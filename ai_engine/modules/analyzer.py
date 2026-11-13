"""Report Analyzer Orchestrator.

Integrates freshness, duplicate detection, source independence, conflict detection,
explainable multi-dimensional scoring, and recommendation generation.
Strictly produces Analysis conforming to CrisisLens API Contract v1.0.
"""

from datetime import datetime, timezone
from typing import List, Optional

from ai_engine import __version__
from ai_engine.schemas.enums import (
    ScoreLevelUrgency,
    ScoreLevelThree,
    RecommendationType,
    SourceType,
    CorroborationStatus,
)
from ai_engine.schemas.internal import ReportInput
from ai_engine.schemas.common import (
    Scores,
    UrgencyScore,
    EvidenceConfidenceScore,
    VerificationPriorityScore,
)
from ai_engine.schemas.analysis import (
    Analysis,
    Recommendation,
    ConflictItem,
    ConflictStatement,
)
from ai_engine.modules.freshness import FreshnessAnalyzer
from ai_engine.modules.duplicate import DuplicateDetector
from ai_engine.modules.source import SourceIndependenceAnalyzer


def _detect_conflicts(
    report: ReportInput,
    context_reports: List[ReportInput],
    now_iso: str,
) -> List[ConflictItem]:
    """Detects direct contradictions between reports."""
    conflicts: List[ConflictItem] = []
    text_lower = report.text.lower()

    for other in context_reports:
        if other.id == report.id:
            continue
        other_lower = other.text.lower()

        # Structural damage conflict pattern (e.g. "building collapsed" vs "only compound wall fell")
        is_conflict = (
            ("collapse" in text_lower and "only" in other_lower and "wall" in other_lower) or
            ("collapse" in other_lower and "only" in text_lower and "wall" in text_lower)
        )

        # Casualty / trapped conflict pattern (e.g. "people trapped" vs "nobody trapped / safe")
        if not is_conflict:
            is_conflict = (
                ("trapped" in text_lower and ("nobody trapped" in other_lower or "no one trapped" in other_lower)) or
                ("trapped" in other_lower and ("nobody trapped" in text_lower or "no one trapped" in text_lower))
            )

        if is_conflict:
            conflicts.append(
                ConflictItem(
                    id=f"cfl_{len(conflicts) + 1:03d}",
                    topic="Extent of damage and casualties",
                    report_ids=[report.id, other.id],
                    statements=[
                        ConflictStatement(report_id=report.id, text=report.text),
                        ConflictStatement(report_id=other.id, text=other.text),
                    ],
                    detected_at=now_iso,
                )
            )

    return conflicts


class ReportAnalyzer:
    """End-to-end report intelligence analyzer."""

    @classmethod
    def analyze(
        cls,
        report: ReportInput,
        context_reports: List[ReportInput],
        reference_time: Optional[datetime] = None,
    ) -> Analysis:
        """Executes full intelligence pipeline for a report."""
        if not reference_time:
            reference_time = datetime.now(timezone.utc)
        elif reference_time.tzinfo is None:
            reference_time = reference_time.replace(tzinfo=timezone.utc)

        now_iso = reference_time.strftime("%Y-%m-%dT%H:%M:%SZ")

        # 1. Freshness analysis
        freshness = FreshnessAnalyzer.calculate_freshness(
            report.reported_at,
            reference_time=reference_time,
        )

        # 2. Duplicate detection
        duplicate = DuplicateDetector.detect_duplicates(
            report=report,
            context_reports=context_reports,
        )

        # 3. Conflict detection
        conflicts = _detect_conflicts(report, context_reports, now_iso)
        has_conflicts = len(conflicts) > 0

        # 4. Source verification & independence
        source_verification = SourceIndependenceAnalyzer.analyze_source(
            report=report,
            duplicate_info=duplicate,
            context_reports=context_reports,
            has_conflicts=has_conflicts,
        )

        is_forwarded = source_verification.independence.value == "forwarded"
        corroboration = source_verification.corroboration_status.value

        # 5. Explainable Score Calculations
        text_lower = report.text.lower()

        # --- Urgency Score (0 to 100, 4 levels) ---
        urgency_val = 50
        urgency_reasons: List[str] = []
        if any(w in text_lower for w in ["trapped", "collapse", "drowning", "casualty", "injured"]):
            urgency_val += 40
            urgency_reasons.append("Potential threat to human life or reported trapped individuals")
        if any(w in text_lower for w in ["elderly", "children", "patients", "hospital"]):
            urgency_val += 15
            urgency_reasons.append("Vulnerable population mentioned")
        if any(w in text_lower for w in ["flood", "water level", "rising", "fire"]):
            urgency_val += 10
            urgency_reasons.append("Active progressing environmental hazard")
        if not urgency_reasons:
            urgency_reasons.append("Baseline incident urgency")

        urgency_val = min(100, max(0, urgency_val))
        if urgency_val >= 85:
            urgency_lvl = ScoreLevelUrgency.CRITICAL
        elif urgency_val >= 70:
            urgency_lvl = ScoreLevelUrgency.HIGH
        elif urgency_val >= 40:
            urgency_lvl = ScoreLevelUrgency.MEDIUM
        else:
            urgency_lvl = ScoreLevelUrgency.LOW

        # --- Evidence Confidence Score (0 to 100, 3 levels) ---
        conf_val = 40
        conf_reasons: List[str] = []
        src_type = report.source_type.lower()
        if src_type in [SourceType.OFFICIAL.value, SourceType.RESPONDER.value]:
            conf_val += 50
            conf_reasons.append("Submitted by verified emergency official or first responder")
        elif src_type == SourceType.SENSOR.value:
            conf_val += 40
            conf_reasons.append("Automated sensor telemetry confirmation")
        elif src_type == SourceType.NEWS.value:
            conf_val += 25
            conf_reasons.append("Reputable news wire report")
        else:
            conf_reasons.append("Citizen field witness account")

        if corroboration == CorroborationStatus.CORROBORATED.value:
            conf_val += 25
            conf_reasons.append("Corroborated by independent sources")
        if is_forwarded:
            conf_val -= 30
            conf_reasons.append("Forwarded message copy; does not add independent confirmation weight")
        if has_conflicts:
            conf_val -= 20
            conf_reasons.append("Disputed by another account")

        conf_val = min(100, max(0, conf_val))
        if conf_val >= 75:
            conf_lvl = ScoreLevelThree.HIGH
        elif conf_val >= 45:
            conf_lvl = ScoreLevelThree.MEDIUM
        else:
            conf_lvl = ScoreLevelThree.LOW

        # --- Verification Priority Score (0 to 100, 3 levels) ---
        ver_val = 30
        ver_reasons: List[str] = []
        if has_conflicts:
            ver_val += 45
            ver_reasons.append("Direct contradiction detected between witness accounts")
        if urgency_val >= 75 and conf_val < 60:
            ver_val += 35
            ver_reasons.append("High urgency report lacking official confirmation")
        if corroboration == CorroborationStatus.SINGLE_SOURCE.value and src_type == SourceType.CITIZEN.value:
            ver_val += 15
            ver_reasons.append("Single unconfirmed citizen witness")
        if corroboration == CorroborationStatus.CORROBORATED.value:
            ver_val -= 20
            ver_reasons.append("Already corroborated by multiple independent reports")
        if src_type in [SourceType.OFFICIAL.value, SourceType.RESPONDER.value]:
            ver_val -= 20
            ver_reasons.append("Directly submitted by emergency responder")

        ver_val = min(100, max(0, ver_val))
        if ver_val >= 70:
            ver_lvl = ScoreLevelThree.HIGH
        elif ver_val >= 40:
            ver_lvl = ScoreLevelThree.MEDIUM
        else:
            ver_lvl = ScoreLevelThree.LOW

        scores = Scores(
            urgency=UrgencyScore(score=urgency_val, level=urgency_lvl, reasons=urgency_reasons),
            evidence_confidence=EvidenceConfidenceScore(score=conf_val, level=conf_lvl, reasons=conf_reasons),
            verification_priority=VerificationPriorityScore(score=ver_val, level=ver_lvl, reasons=ver_reasons),
        )

        # 6. Recommendation
        if has_conflicts or ver_val >= 70:
            rec_type = RecommendationType.VERIFY_FIRST
            rec_summary = "Conflicting or high-urgency uncorroborated information. Verify on-site before deploying resources."
            rec_steps = ["Dispatch reconnaissance unit or call local contact", "Re-assess upon verification"]
        elif urgency_val >= 75 and conf_val >= 70:
            rec_type = RecommendationType.ESCALATE_FOR_HUMAN_REVIEW
            rec_summary = "Strong corroborating evidence and high urgency. Refer immediately to duty officer for action."
            rec_steps = ["Alert incident coordinator", "Prepare rescue deployment standby"]
        else:
            rec_type = RecommendationType.MONITOR
            rec_summary = "Report logged and correlated. Monitor situation for further updates."
            rec_steps = ["Maintain surveillance", "Re-check in 30 minutes"]

        recommendation = Recommendation(
            type=rec_type,
            summary=rec_summary,
            next_steps=rec_steps,
            requires_human_decision=True,
        )

        return Analysis(
            analyzed_at=now_iso,
            engine_version=__version__,
            duplicate=duplicate,
            source_verification=source_verification,
            freshness=freshness,
            conflicts=conflicts,
            scores=scores,
            recommendation=recommendation,
        )
