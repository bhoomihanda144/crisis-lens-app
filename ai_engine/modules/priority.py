"""Incident Priority Ranking Engine Module (Stage 5).

Implements CrisisLens API Contract v1.0 Section 4.7.
Computes explainable, deterministic multi-dimensional priority scores:
- Urgency: Threat to life, vulnerable populations, hazard progression.
- Evidence Confidence: Independent corroboration, official/sensor telemetry, penalty for forwarding/conflicts.
- Verification Priority: Urgent need for human ground-truth verification (elevated by urgency/confidence gap and conflicts).

Strictly preserves:
- Separation of scores: Urgency, Confidence, and Verification Priority remain independent (no combined score).
- Human Decision Authority: `requires_human_decision=True` invariant, human_decision status always `not_decided`.
- Deterministic tie-breaking and rank numbering.
"""

from typing import List, Dict, Set, Tuple, Optional

from ai_engine.schemas.enums import (
    PrioritySort,
    ScoreLevelUrgency,
    ScoreLevelThree,
    IncidentSeverity,
    IncidentStatus,
    SourceType,
)
from ai_engine.schemas.common import (
    Location,
    UrgencyScore,
    EvidenceConfidenceScore,
    VerificationPriorityScore,
)
from ai_engine.schemas.incident import (
    PriorityItem,
    PriorityResponse,
    HumanDecision,
)
from ai_engine.schemas.internal import IncidentInput, ReportInput
from ai_engine.modules.source import SourceIndependenceAnalyzer
from ai_engine.modules.duplicate import DuplicateDetector


# --- NAMED SCORING CONSTANTS ---

# Baseline Urgency by Incident Severity
SEVERITY_URGENCY_BASE: Dict[str, int] = {
    "critical": 85,
    "high": 70,
    "medium": 50,
    "low": 25,
}

# Threat Keywords for Report Urgency Analysis
LIFE_THREAT_KEYWORDS: Set[str] = {
    "trapped", "collapse", "collapsed", "drowning", "casualty", "casualties",
    "injured", "injury", "buried", "fatal", "suffocation", "unconscious",
}
VULNERABLE_KEYWORDS: Set[str] = {
    "elderly", "children", "child", "infant", "infants", "patients", "patient",
    "hospital", "clinic", "school", "disabled", "wheelchair",
}
PROGRESSING_HAZARD_KEYWORDS: Set[str] = {
    "flood", "flooding", "water level", "rising", "fire", "spreading", "gas leak",
    "overflowing", "explosion", "landslide",
}

# Confidence Scoring Constants
BASE_CONFIDENCE = 40
CONFIDENCE_INDEPENDENT_3_PLUS = 35
CONFIDENCE_INDEPENDENT_2 = 25
CONFIDENCE_INDEPENDENT_1 = 5
CONFIDENCE_ZERO_INDEPENDENT = -10
CONFIDENCE_OFFICIAL_OR_SENSOR = 20
CONFIDENCE_FORWARDED_PENALTY = -15
CONFIDENCE_CONFLICT_PENALTY = -20

# Verification Priority Scoring Constants
BASE_VERIFICATION = 30
VERIFICATION_HIGH_URGENCY_LOW_CONF = 35
VERIFICATION_CRITICAL_GAP = 15
VERIFICATION_CONFLICT_BOOST = 30
VERIFICATION_SINGLE_SOURCE_BOOST = 15
VERIFICATION_CORROBORATION_RELIEF = -25
VERIFICATION_RESOLVED_RELIEF = -30


class IncidentPriorityRanker:
    """Deterministic, explainable priority ranking engine for emergency incidents."""

    @classmethod
    def rank_incidents(
        cls,
        incidents: List[IncidentInput],
        sort: PrioritySort = PrioritySort.URGENCY,
    ) -> PriorityResponse:
        """Ranks a batch of incidents by urgency or verification need.

        Args:
            incidents: List of incident input objects.
            sort: Sorting criterion (PrioritySort.URGENCY or PrioritySort.VERIFICATION).

        Returns:
            PriorityResponse containing ranked PriorityItem objects.
        """
        if not incidents:
            return PriorityResponse(sort=sort, items=[])

        unranked_items: List[PriorityItem] = []

        for inc in incidents:
            urgency, confidence, verification, explanation, next_steps = cls.compute_incident_scores(inc)

            loc = Location(
                lat=inc.lat,
                lng=inc.lng,
                label=inc.location_label,
            )

            item = PriorityItem(
                rank=1,  # will be assigned after deterministic sorting
                incident_id=inc.id,
                title=inc.title,
                location=loc,
                urgency=urgency,
                evidence_confidence=confidence,
                verification_priority=verification,
                explanation=explanation,
                recommended_next_steps=next_steps,
                requires_human_decision=True,
                human_decision=HumanDecision(
                    status="not_decided",
                    decided_by=None,
                    decided_at=None,
                ),
            )
            unranked_items.append(item)

        # Deterministic sorting based on criteria
        if sort == PrioritySort.VERIFICATION or sort == "verification":
            # Primary: verification_priority descending
            # Secondary tie-breaker: urgency descending
            # Tertiary tie-breaker: incident_id ascending
            unranked_items.sort(
                key=lambda item: (-item.verification_priority.score, -item.urgency.score, item.incident_id)
            )
        else:
            # Primary: urgency descending
            # Secondary tie-breaker: verification_priority descending
            # Tertiary tie-breaker: incident_id ascending
            unranked_items.sort(
                key=lambda item: (-item.urgency.score, -item.verification_priority.score, item.incident_id)
            )

        # Assign 1-indexed ranks
        for idx, item in enumerate(unranked_items, start=1):
            item.rank = idx

        effective_sort = PrioritySort.VERIFICATION if (sort == PrioritySort.VERIFICATION or sort == "verification") else PrioritySort.URGENCY
        return PriorityResponse(sort=effective_sort, items=unranked_items)

    @classmethod
    def compute_incident_scores(
        cls,
        incident: IncidentInput,
    ) -> Tuple[UrgencyScore, EvidenceConfidenceScore, VerificationPriorityScore, List[str], List[str]]:
        """Calculates three independent scores, explanations, and next steps for an incident."""
        urgency = cls._calculate_urgency(incident)
        confidence, effective_indep = cls._calculate_evidence_confidence(incident)
        verification = cls._calculate_verification_priority(incident, urgency.score, confidence.score, effective_indep)

        explanation = cls._generate_explanation(incident, urgency, confidence, verification)
        next_steps = cls._generate_next_steps(urgency, confidence, verification, incident)

        return urgency, confidence, verification, explanation, next_steps

    @classmethod
    def _calculate_urgency(cls, incident: IncidentInput) -> UrgencyScore:
        """Computes urgency reflecting life safety, vulnerable groups, and hazard progression."""
        sev_key = incident.severity.lower() if incident.severity else "medium"
        base_urgency = SEVERITY_URGENCY_BASE.get(sev_key, 50)
        urg_val = base_urgency
        reasons: List[str] = [f"Incident severity evaluated as {sev_key.capitalize()}"]

        # 1. Report-level analysis & threat signal detection
        # Rule: Do not dilute severe active threats through simple averaging
        max_report_urgency: Optional[int] = None
        report_reasons: List[str] = []

        if incident.report_analyses:
            report_urgencies = [a.scores.urgency.score for a in incident.report_analyses]
            if report_urgencies:
                max_report_urgency = max(report_urgencies)
                # Find matching analysis reasons
                for a in incident.report_analyses:
                    if a.scores.urgency.score == max_report_urgency:
                        report_reasons.extend(a.scores.urgency.reasons)
                        break

        elif incident.reports:
            # Text scan across associated reports
            has_life_threat = False
            has_vulnerable = False
            has_prog_hazard = False

            for rep in incident.reports:
                txt_lower = rep.text.lower()
                if any(w in txt_lower for w in LIFE_THREAT_KEYWORDS):
                    has_life_threat = True
                if any(w in txt_lower for w in VULNERABLE_KEYWORDS):
                    has_vulnerable = True
                if any(w in txt_lower for w in PROGRESSING_HAZARD_KEYWORDS):
                    has_prog_hazard = True

            scanned_urgency = base_urgency
            if has_life_threat:
                scanned_urgency = max(scanned_urgency, 85)
                report_reasons.append("Potential threat to human life or reported trapped individuals")
            if has_vulnerable:
                scanned_urgency = min(100, scanned_urgency + 10)
                report_reasons.append("Vulnerable population mentioned in field reports")
            if has_prog_hazard:
                scanned_urgency = min(100, scanned_urgency + 5)
                report_reasons.append("Active progressing environmental hazard reported")

            if report_reasons:
                max_report_urgency = scanned_urgency

        if max_report_urgency is not None:
            # Take the severe threat without dilution
            if max_report_urgency > urg_val:
                urg_val = max_report_urgency
                reasons.extend(report_reasons)

        # 2. Timeline progression signals
        if incident.timeline:
            severities = [t.severity for t in incident.timeline]
            # Check for escalation
            if len(severities) >= 2 and severities[-1] in [IncidentSeverity.HIGH, IncidentSeverity.CRITICAL]:
                urg_val = min(100, urg_val + 5)
                reasons.append("Escalating severity trend observed in incident timeline")
            # Check affected radius
            if any(t.affected_radius_m >= 500 for t in incident.timeline):
                urg_val = min(100, urg_val + 5)
                reasons.append("Significant geographical hazard radius reported (>= 500m)")

        # 3. Status handling
        # Rule: Do not assume an incident is resolved merely because its latest report is old
        # Rule: Preserve historical threat reasons and append resolution status
        if incident.status and incident.status.lower() == "resolved":
            urg_val = min(urg_val, 20)
            reasons.append("Incident has been officially marked as resolved; priority lowered accordingly")

        urg_score = min(100, max(0, urg_val))

        # Map to ScoreLevelUrgency enum
        if urg_score >= 85:
            level = ScoreLevelUrgency.CRITICAL
        elif urg_score >= 70:
            level = ScoreLevelUrgency.HIGH
        elif urg_score >= 40:
            level = ScoreLevelUrgency.MEDIUM
        else:
            level = ScoreLevelUrgency.LOW

        return UrgencyScore(
            score=urg_score,
            level=level,
            reasons=reasons,
        )

    @classmethod
    def _reconcile_independent_sources(
        cls,
        incident: IncidentInput,
    ) -> Tuple[int, List[str], bool]:
        """Reconciles metadata independent_source_count with report-level evidence.

        Strict Guardrails:
        - Excludes forwarded reports.
        - Excludes duplicate reports when established by available evidence.
        - Does not count multiple reports from the same known source as independent.
        - Does not infer independence solely from source_type or source_name.
        - Handles missing report data conservatively.
        - If metadata conflicts with report evidence, uses the conservative defensible count.

        Returns:
            Tuple of (effective_independent_count, reconciliation_reasons, has_official_confirmation).
        """
        reconciliation_reasons: List[str] = []
        has_official_confirmation = False

        if not incident.reports:
            # Conservative fallback to metadata count when reports are omitted
            effective_count = incident.independent_source_count or 0
            return effective_count, reconciliation_reasons, has_official_confirmation

        # Inspect report-level evidence
        non_forwarded_reports: List[ReportInput] = []
        forwarded_count = 0
        known_sources: Set[str] = set()
        anonymous_count = 0

        for r in incident.reports:
            # Check official / sensor confirmation with verifiable provenance
            st = r.source_type.lower() if r.source_type else ""
            prov = r.provenance.lower() if r.provenance else ""
            if st in [SourceType.OFFICIAL.value, SourceType.RESPONDER.value] and prov in [
                "verified", "authenticated", "firsthand", "verified_original"
            ]:
                has_official_confirmation = True
            elif st == SourceType.SENSOR.value:
                has_official_confirmation = True

            # 1. Forwarded check
            is_fwd = bool(r.forwarded_from) or SourceIndependenceAnalyzer.is_forwarded_text(r.text)
            if is_fwd:
                forwarded_count += 1
                continue

            # 2. Duplicate check against previously processed non-forwarded reports
            if non_forwarded_reports:
                dup_info = DuplicateDetector.detect_duplicates(
                    report=r,
                    context_reports=non_forwarded_reports,
                    duplicate_threshold=0.55,
                )
                if dup_info.is_duplicate:
                    # Exclude duplicate reports from independent evidence
                    continue

            non_forwarded_reports.append(r)

            # 3. Source identity tracking
            src_name = r.source_name.strip().lower() if r.source_name else "anonymous"
            if src_name in ["anonymous", "unknown", "witness", "resident", "citizen"]:
                anonymous_count += 1
            else:
                known_sources.add(src_name)

        # Defensible independent source count:
        # Known distinct sources + at most 1 distinct non-duplicate anonymous source (to prevent anonymous multiplier)
        defensible_count = len(known_sources) + min(1, anonymous_count)

        # If majority are forwarded
        if forwarded_count > 0 and forwarded_count >= len(incident.reports) / 2:
            reconciliation_reasons.append("High proportion of forwarded copies; does not add independent confirmation weight")

        # Reconcile with metadata count
        metadata_count = incident.independent_source_count or 0
        if metadata_count > 0 and defensible_count == 0:
            effective_count = 0
            reconciliation_reasons.append(
                f"Metadata claimed {metadata_count} independent sources, but all attached reports were unconfirmed, forwarded, or duplicates"
            )
        elif metadata_count > defensible_count:
            # Conflict detected: metadata claimed more independent sources than verified in reports
            effective_count = defensible_count
            reconciliation_reasons.append(
                f"Metadata claimed {metadata_count} independent sources, but report evidence confirms only {defensible_count} independent source(s)"
            )
        else:
            effective_count = max(metadata_count, defensible_count)

        return effective_count, reconciliation_reasons, has_official_confirmation

    @classmethod
    def _calculate_evidence_confidence(
        cls,
        incident: IncidentInput,
    ) -> Tuple[EvidenceConfidenceScore, int]:
        """Computes confidence reflecting independent sources, official telemetry, and penalties."""
        conf_val = BASE_CONFIDENCE
        reasons: List[str] = []

        # 1. Independent source count evaluation with reconciliation
        effective_count, recon_reasons, has_official_confirmation = cls._reconcile_independent_sources(incident)
        reasons.extend(recon_reasons)

        if effective_count >= 3:
            conf_val += CONFIDENCE_INDEPENDENT_3_PLUS
            reasons.append(f"{effective_count} independent sources corroborate incident")
        elif effective_count == 2:
            conf_val += CONFIDENCE_INDEPENDENT_2
            reasons.append("Two independent sources corroborate incident")
        elif effective_count == 1:
            conf_val += CONFIDENCE_INDEPENDENT_1
            reasons.append("Single-source report; awaiting independent field corroboration")
        else:
            conf_val += CONFIDENCE_ZERO_INDEPENDENT
            reasons.append("Unconfirmed; zero verified independent sources established")

        # 2. Official responder or sensor confirmation
        if has_official_confirmation:
            conf_val += CONFIDENCE_OFFICIAL_OR_SENSOR
            reasons.append("Confirmed by verified emergency responder or automated sensor telemetry")
        elif incident.reports:
            reasons.append("Field witness reports pending official on-site confirmation")

        # 3. Conflict / contradiction penalty
        if incident.conflicts:
            conf_val += CONFIDENCE_CONFLICT_PENALTY
            reasons.append(f"Direct contradictory accounts detected ({len(incident.conflicts)} conflict item(s))")

        conf_score = min(100, max(0, conf_val))

        # Map to ScoreLevelThree enum
        if conf_score >= 75:
            level = ScoreLevelThree.HIGH
        elif conf_score >= 45:
            level = ScoreLevelThree.MEDIUM
        else:
            level = ScoreLevelThree.LOW

        return EvidenceConfidenceScore(
            score=conf_score,
            level=level,
            reasons=reasons,
        ), effective_count

    @classmethod
    def _calculate_verification_priority(
        cls,
        incident: IncidentInput,
        urgency_score: int,
        confidence_score: int,
        effective_independent_count: int,
    ) -> VerificationPriorityScore:
        """Computes verification priority reflecting need for human ground-truth checking."""
        ver_val = BASE_VERIFICATION
        reasons: List[str] = []

        # 1. High Urgency with Low Evidence Confidence
        # Rule: High urgency combined with low evidence confidence increases verification priority
        if urgency_score >= 70 and confidence_score < 60:
            ver_val += VERIFICATION_HIGH_URGENCY_LOW_CONF
            reasons.append("High urgency situation lacking robust verification; human ground-truth check required")

        if urgency_score >= 85 and confidence_score < 45:
            ver_val += VERIFICATION_CRITICAL_GAP
            reasons.append("Critical life hazard reported from unverified single source")

        # 2. Explicit Conflicts
        # Rule: Explicit conflicts should increase verification priority
        if incident.conflicts:
            ver_val += VERIFICATION_CONFLICT_BOOST
            reasons.append(f"Contradictory witness statements present ({len(incident.conflicts)} conflict(s))")

        # 3. Single Source Witness
        if effective_independent_count <= 1 and confidence_score < 75:
            ver_val += VERIFICATION_SINGLE_SOURCE_BOOST
            reasons.append("Single witness account; field verification advised before heavy deployment")

        # 4. Well-corroborated evidence relief
        # Rule: Already well-corroborated evidence should generally reduce unnecessary verification priority
        if confidence_score >= 75 and not incident.conflicts:
            ver_val += VERIFICATION_CORROBORATION_RELIEF
            reasons.append("Well corroborated by multiple reliable sources; lower verification urgency")

        # 5. Resolved incident relief
        # Rule: Preserve historical context while appending resolution status
        if incident.status and incident.status.lower() == "resolved":
            ver_val += VERIFICATION_RESOLVED_RELIEF
            reasons.append("Incident marked as resolved; routine closeout verification only")

        ver_score = min(100, max(0, ver_val))

        # Map to ScoreLevelThree enum
        if ver_score >= 70:
            level = ScoreLevelThree.HIGH
        elif ver_score >= 40:
            level = ScoreLevelThree.MEDIUM
        else:
            level = ScoreLevelThree.LOW

        return VerificationPriorityScore(
            score=ver_score,
            level=level,
            reasons=reasons,
        )

    @staticmethod
    def _generate_explanation(
        incident: IncidentInput,
        urgency: UrgencyScore,
        confidence: EvidenceConfidenceScore,
        verification: VerificationPriorityScore,
    ) -> List[str]:
        """Produces concise bullet-point summary explaining ranking positioning."""
        bullets: List[str] = [
            f"Active {incident.type.capitalize()} incident at {incident.location_label}",
            f"Status: {incident.status.capitalize()} (Severity: {incident.severity.capitalize()})",
        ]

        if urgency.level in [ScoreLevelUrgency.CRITICAL, ScoreLevelUrgency.HIGH]:
            # Add top urgency driver
            if urgency.reasons:
                bullets.append(f"Urgency driver: {urgency.reasons[0]}")
        else:
            bullets.append(f"Urgency rated {urgency.level.value} ({urgency.score}/100)")

        if confidence.level == ScoreLevelThree.HIGH:
            bullets.append("Evidence is well-corroborated by independent field accounts")
        elif confidence.level == ScoreLevelThree.LOW:
            bullets.append("Evidence confidence is low; unconfirmed field claims")

        if verification.level == ScoreLevelThree.HIGH:
            bullets.append("Flagged for verify-first queue due to verification priority")

        return bullets

    @staticmethod
    def _generate_next_steps(
        urgency: UrgencyScore,
        confidence: EvidenceConfidenceScore,
        verification: VerificationPriorityScore,
        incident: IncidentInput,
    ) -> List[str]:
        """Produces actionable recommended next steps for human dispatchers."""
        if incident.status and incident.status.lower() == "resolved":
            return [
                "Recommend logging final responder debrief",
                "Suggest archiving incident documentation",
            ]

        if verification.level == ScoreLevelThree.HIGH or incident.conflicts:
            return [
                "Advise dispatching reconnaissance or calling local contact for on-site verification",
                "Recommend confirming hazard extent with ward officer before committing heavy rescue resources",
            ]

        if urgency.level in [ScoreLevelUrgency.CRITICAL, ScoreLevelUrgency.HIGH] and confidence.level == ScoreLevelThree.HIGH:
            return [
                "Recommend alerting duty officer for immediate tactical dispatch review",
                "Advise staging emergency rescue and medical standby units for responder review",
            ]

        return [
            "Recommend maintaining monitoring and logging incoming field updates",
            "Suggest re-assessing incident priority upon arrival of new corroborating evidence",
        ]
