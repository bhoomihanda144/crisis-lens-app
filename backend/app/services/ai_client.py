"""
CrisisLens AI Client
Interfaces with Member 3's AI Engine service over HTTP.
Includes contract-compliant fallback analysis so the system remains fully operational
even when Member 3's service is offline or in development.
"""
import httpx
import logging
from typing import Dict, Any, List, Optional
from app.core.config import settings
from app.utils.datetime_utils import now_utc_iso, calculate_freshness
from app.schemas.analysis import AnalysisObject
from app.schemas.evidence import EvidenceGraphResponse
from app.schemas.priority import PriorityResponse
from app.schemas.simulation import SimulationRequest, SimulationResponse

logger = logging.getLogger(__name__)

# Version tag for deterministic fallback — distinguishable from real AI output.
# Member 3: coordinate this prefix string with your engine_version field.
FALLBACK_ENGINE_VERSION = "deterministic-fallback-0.1.0"


class AIClient:
    @staticmethod
    async def analyze_report(
        report_data: Dict[str, Any],
        existing_reports: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Calls Member 3's AI Engine endpoint.
        If unavailable, runs the deterministic contract-compliant intelligence engine.
        Real AI output has engine_version set by Member 3's engine.
        Deterministic fallback always has engine_version starting with 'deterministic-fallback'.
        """
        # Try to call Member 3's AI Engine service
        if settings.AI_ENGINE_URL:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(
                        f"{settings.AI_ENGINE_URL.rstrip('/')}/analyze",
                        json={
                            "report": report_data,
                            "context_reports": existing_reports,
                        },
                    )
                    if resp.status_code == 200:
                        raw_data = resp.json()
                        # Validate structure against AnalysisObject schema
                        validated = AnalysisObject.model_validate(raw_data)
                        return validated.model_dump(mode="json")
                    else:
                        logger.warning(
                            "AI Engine at %s returned non-200 status %s. Using deterministic fallback.",
                            settings.AI_ENGINE_URL,
                            resp.status_code,
                        )
            except httpx.TimeoutException as exc:
                logger.warning(
                    "AI Engine request timed out (%s). Using deterministic fallback.",
                    type(exc).__name__,
                )
            except httpx.ConnectError as exc:
                logger.warning(
                    "AI Engine connection failed (%s). Using deterministic fallback.",
                    type(exc).__name__,
                )
            except Exception as exc:
                logger.warning(
                    "AI Engine unavailable (%s). Using deterministic fallback.",
                    type(exc).__name__,
                )

        # Deterministic contract-compliant analysis engine
        logger.info("Running deterministic fallback analysis (engine_version=%s).", FALLBACK_ENGINE_VERSION)
        return AIClient._compute_deterministic_analysis(report_data, existing_reports)

    @staticmethod
    def generate_evidence_graph(
        incident_id: str,
        reports: List[Dict[str, Any]],
        conflicts: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[EvidenceGraphResponse]:
        """
        Calls Member 3's AI Engine endpoint:
        POST /incidents/{incident_id}/evidence-graph
        Sends incident reports and explicitly identified conflicts.
        Returns validated EvidenceGraphResponse if successful, or None on failure/timeout.
        """
        if not settings.AI_ENGINE_URL:
            return None

        url = f"{settings.AI_ENGINE_URL.rstrip('/')}/incidents/{incident_id}/evidence-graph"
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(
                    url,
                    json={
                        "incident_id": incident_id,
                        "reports": reports,
                        "conflicts": conflicts or [],
                    },
                )
                if resp.status_code == 200:
                    raw_data = resp.json()
                    validated = EvidenceGraphResponse.model_validate(raw_data)
                    return validated
                else:
                    logger.warning(
                        "AI Engine evidence-graph at %s returned non-200 status %s for incident %s.",
                        url,
                        resp.status_code,
                        incident_id,
                    )
        except httpx.TimeoutException as exc:
            logger.warning(
                "AI Engine evidence-graph request timed out for incident %s (%s).",
                incident_id,
                type(exc).__name__,
            )
        except httpx.ConnectError as exc:
            logger.warning(
                "AI Engine connection failed for evidence-graph at %s (%s).",
                url,
                type(exc).__name__,
            )
        except Exception as exc:
            logger.warning(
                "AI Engine evidence-graph failed or returned invalid response (%s: %s).",
                type(exc).__name__,
                exc,
            )
        return None

    @staticmethod
    def get_priority_ranking(
        incidents: List[Dict[str, Any]],
        sort: str = "urgency",
    ) -> Optional[PriorityResponse]:
        """
        Calls Member 3's AI Engine endpoint:
        POST /incidents/priority?sort={sort}
        Sends batch of incidents with reports and existing analysis.
        Returns validated PriorityResponse if successful, or None on failure/timeout.
        """
        if not settings.AI_ENGINE_URL:
            return None

        url = f"{settings.AI_ENGINE_URL.rstrip('/')}/incidents/priority"
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(
                    url,
                    params={"sort": sort},
                    json={
                        "sort": sort,
                        "incidents": incidents,
                    },
                )
                if resp.status_code == 200:
                    raw_data = resp.json()
                    validated = PriorityResponse.model_validate(raw_data)
                    return validated
                else:
                    logger.warning(
                        "AI Engine priority ranking at %s returned non-200 status %s.",
                        url,
                        resp.status_code,
                    )
        except httpx.TimeoutException as exc:
            logger.warning(
                "AI Engine priority ranking timed out (%s).",
                type(exc).__name__,
            )
        except httpx.ConnectError as exc:
            logger.warning(
                "AI Engine connection failed for priority ranking at %s (%s).",
                url,
                type(exc).__name__,
            )
        except Exception as exc:
            logger.warning(
                "AI Engine priority ranking failed or returned invalid response (%s: %s).",
                type(exc).__name__,
                exc,
            )
        return None

    @staticmethod
    def run_simulation(
        payload: SimulationRequest,
        incidents: Optional[List[Dict[str, Any]]] = None,
        blocked_access_incident_ids: Optional[List[str]] = None,
    ) -> Optional[SimulationResponse]:
        """
        Calls Member 3's AI Engine endpoint:
        POST /simulation/run
        Sends scenario inputs along with active incident context and road-access impact data.
        Returns validated SimulationResponse if successful, or None on failure/timeout.
        """
        if not settings.AI_ENGINE_URL:
            return None

        url = f"{settings.AI_ENGINE_URL.rstrip('/')}/simulation/run"
        request_body = {
            "scenario_name": payload.scenario_name,
            "affected_population": payload.affected_population,
            "disaster_severity": payload.disaster_severity,
            "rescue_teams": payload.rescue_teams,
            "blocked_roads": payload.blocked_roads,
            "available_ambulances": payload.available_ambulances,
            "incidents": incidents or [],
            "blocked_access_incident_ids": blocked_access_incident_ids or [],
        }
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(url, json=request_body)
                if resp.status_code == 200:
                    raw_data = resp.json()
                    validated = SimulationResponse.model_validate(raw_data)
                    return validated
                else:
                    logger.warning(
                        "AI Engine simulation at %s returned non-200 status %s.",
                        url,
                        resp.status_code,
                    )
        except httpx.TimeoutException as exc:
            logger.warning(
                "AI Engine simulation request timed out (%s).",
                type(exc).__name__,
            )
        except httpx.ConnectError as exc:
            logger.warning(
                "AI Engine connection failed for simulation at %s (%s).",
                url,
                type(exc).__name__,
            )
        except Exception as exc:
            logger.warning(
                "AI Engine simulation failed or returned invalid response (%s: %s).",
                type(exc).__name__,
                exc,
            )
        return None

    @staticmethod
    def _compute_deterministic_analysis(
        report: Dict[str, Any],
        existing_reports: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        report_text = report["text"].lower()
        source_type = report["source_type"]
        forwarded_from = report.get("forwarded_from")
        reported_at = report["reported_at"]

        # 1. Freshness analysis
        freshness_info = calculate_freshness(reported_at)

        # 2. Duplicate detection
        matches = []
        is_duplicate = False
        words = set(report_text.split())

        for other in existing_reports:
            if other["id"] == report["id"]:
                continue
            other_text = other["text"].lower()
            other_words = set(other_text.split())
            intersection = words.intersection(other_words)
            similarity = len(intersection) / max(1, len(words.union(other_words)))

            # If similarity is noticeable
            if similarity >= 0.35 or forwarded_from == other["id"]:
                is_duplicate = True
                reasons = []
                if similarity >= 0.5:
                    reasons.append("Similar phrasing and vocabulary")
                if other.get("location_label") == report.get("location_label"):
                    reasons.append("Same reported location")
                if forwarded_from == other["id"]:
                    reasons.append('Direct forwarded marker or reference')
                    similarity = 0.95
                if not reasons:
                    reasons.append("Overlapping disaster context")

                matches.append({
                    "report_id": other["id"],
                    "similarity": round(min(1.0, similarity), 2),
                    "reasons": reasons,
                })

        # 3. Source independence & corroboration
        is_forwarded = bool(forwarded_from or "fwd:" in report_text or "forwarded" in report_text)
        independence = "forwarded" if is_forwarded else "independent"
        original_id = forwarded_from or (matches[0]["report_id"] if matches else None)

        related_list = []
        for m in matches:
            rel_type = "forwarded" if is_forwarded else "duplicate"
            related_list.append({"report_id": m["report_id"], "relation": rel_type})

        corroboration = "corroborated" if (len(matches) > 0 and not is_forwarded) else "single_source"

        # 4. Conflict detection
        conflicts = []
        if "wall" in report_text and "collapsed" in report_text:
            pass  # regular
        for other in existing_reports:
            otext = other["text"].lower()
            if ("collapse" in report_text and "only" in otext and "wall" in otext) or \
               ("collapse" in otext and "only" in report_text and "wall" in report_text):
                conflicts.append({
                    "id": f"cfl_{len(conflicts)+1:03d}",
                    "topic": "Extent of structural damage",
                    "report_ids": [report["id"], other["id"]],
                    "statements": [
                        {"report_id": report["id"], "text": report["text"]},
                        {"report_id": other["id"], "text": other["text"]},
                    ],
                    "detected_at": now_utc_iso(),
                })

        # 5. Score calculation (Urgency, Evidence Confidence, Verification Priority)
        # Urgency
        urgency_score = 50
        urgency_reasons = []
        if any(w in report_text for w in ["trapped", "collapse", "drowning", "casualty", "injured"]):
            urgency_score += 40
            urgency_reasons.append("Potential threat to human life or reported trapped individuals")
        if any(w in report_text for w in ["elderly", "children", "patients", "hospital"]):
            urgency_score += 15
            urgency_reasons.append("Vulnerable population mentioned")
        if any(w in report_text for w in ["flood", "water level", "rising", "fire"]):
            urgency_score += 10
            urgency_reasons.append("Active progressing environmental hazard")
        urgency_score = min(100, max(0, urgency_score))
        urgency_level = "critical" if urgency_score >= 85 else "high" if urgency_score >= 70 else "medium" if urgency_score >= 40 else "low"

        # Evidence Confidence
        confidence_score = 40
        confidence_reasons = []
        if source_type in ["official", "responder"]:
            confidence_score += 50
            confidence_reasons.append("Submitted by verified emergency official or first responder")
        elif source_type == "sensor":
            confidence_score += 40
            confidence_reasons.append("Automated sensor telemetry confirmation")
        elif source_type == "news":
            confidence_score += 25
            confidence_reasons.append("Reputable news wire verification")
        else:
            confidence_reasons.append("Citizen field report")

        if corroboration == "corroborated":
            confidence_score += 25
            confidence_reasons.append("Corroborated by independent sources")
        if is_forwarded:
            confidence_score -= 30
            confidence_reasons.append("Forwarded message copy; does not add independent confirmation weight")

        confidence_score = min(100, max(0, confidence_score))
        confidence_level = "high" if confidence_score >= 75 else "medium" if confidence_score >= 45 else "low"

        # Verification Priority (Needs review first if high urgency but low confidence, or conflicts)
        verification_score = 30
        verification_reasons = []
        if conflicts:
            verification_score += 45
            verification_reasons.append("Direct contradiction detected between witness accounts")
        if urgency_score >= 75 and confidence_score < 60:
            verification_score += 35
            verification_reasons.append("High urgency report lacking official confirmation")
        if corroboration == "single_source" and source_type == "citizen":
            verification_score += 15
            verification_reasons.append("Single unconfirmed citizen witness")
        if corroboration == "corroborated":
            verification_score -= 20
            verification_reasons.append("Already corroborated by multiple independent reports")

        verification_score = min(100, max(0, verification_score))
        verification_level = "high" if verification_score >= 70 else "medium" if verification_score >= 40 else "low"

        # 6. Recommendation
        if conflicts or verification_score >= 70:
            rec_type = "verify_first"
            rec_summary = "Conflicting or high-urgency single-source information. Verify on-site before deploying resources."
            rec_steps = ["Dispatch reconnaissance or call local contact", "Re-assess upon verification"]
        elif urgency_score >= 75 and confidence_score >= 70:
            rec_type = "escalate_for_human_review"
            rec_summary = "Strong corroborating evidence and high urgency. Refer immediately to duty officer for action."
            rec_steps = ["Alert incident coordinator", "Prepare rescue deployment standby"]
        else:
            rec_type = "monitor"
            rec_summary = "Report logged and correlated. Monitor situation for further updates."
            rec_steps = ["Maintain surveillance", "Re-check in 30 minutes"]

        analysis_payload = {
            "analyzed_at": now_utc_iso(),
            "engine_version": FALLBACK_ENGINE_VERSION,
            "duplicate": {
                "is_duplicate": is_duplicate,
                "matches": matches,
            },
            "source_verification": {
                "independence": independence,
                "original_report_id": original_id,
                "related": related_list,
                "corroboration_status": corroboration,
            },
            "freshness": freshness_info,
            "conflicts": conflicts,
            "scores": {
                "urgency": {
                    "score": urgency_score,
                    "level": urgency_level,
                    "reasons": urgency_reasons,
                },
                "evidence_confidence": {
                    "score": confidence_score,
                    "level": confidence_level,
                    "reasons": confidence_reasons,
                },
                "verification_priority": {
                    "score": verification_score,
                    "level": verification_level,
                    "reasons": verification_reasons,
                },
            },
            "recommendation": {
                "type": rec_type,
                "summary": rec_summary,
                "next_steps": rec_steps,
                "requires_human_decision": True,
            },
        }

        # Validate with Pydantic
        validated = AnalysisObject.model_validate(analysis_payload)
        return validated.model_dump(mode="json")
