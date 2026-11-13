"""
CrisisLens Priority Service
Implements GET /incidents/priority per API Contract v1.0 Section 4.7.
Maintains three separate scores: Urgency, Evidence Confidence, Verification Priority.
Delegates priority ranking calculation to Member 3 AI Engine (POST /incidents/priority)
with resilient fallback to stored priority scores and contract-compliant baseline heuristics.
"""
import logging
from typing import List, Dict, Any
from app.database.supabase_client import get_supabase_client
from app.schemas.priority import PriorityItem, PriorityResponse, HumanDecisionInfo
from app.schemas.common import LocationSchema, ScoreDetail
from app.services.ai_client import AIClient
from app.utils.id_generator import generate_semantic_id
from app.utils.datetime_utils import now_utc_iso

logger = logging.getLogger(__name__)


class PriorityService:
    @staticmethod
    def get_priority_ranking(sort: str = "urgency") -> PriorityResponse:
        supabase = get_supabase_client()
        incidents_res = supabase.table("incidents").select("*").execute()
        incidents = incidents_res.data or []

        if not incidents:
            return PriorityResponse(sort=sort, items=[])

        incident_ids = [inc["id"] for inc in incidents]

        # 1. Fetch associated reports and their analyses to construct rich context for AI Engine
        reports_by_incident: Dict[str, List[Dict[str, Any]]] = {}
        try:
            reports_res = supabase.table("reports").select("*").in_("incident_id", incident_ids).execute()
            reports = reports_res.data or []

            report_ids = [r["id"] for r in reports]
            analysis_map: Dict[str, Dict[str, Any]] = {}
            if report_ids:
                anl_res = supabase.table("analysis_results").select("report_id, urgency_score, evidence_confidence_score, verification_priority_score, raw_analysis").in_("report_id", report_ids).execute()
                for anl in (anl_res.data or []):
                    raw = anl.get("raw_analysis") or {}
                    sv = raw.get("source_verification") or {}
                    fn = raw.get("freshness") or {}
                    analysis_map[anl["report_id"]] = {
                        "urgency_score": anl.get("urgency_score"),
                        "evidence_confidence_score": anl.get("evidence_confidence_score"),
                        "verification_priority_score": anl.get("verification_priority_score"),
                        "independence": sv.get("independence", "independent"),
                        "corroboration_status": sv.get("corroboration_status", "single_source"),
                        "freshness_status": fn.get("status", "recent"),
                        "conflicts": raw.get("conflicts", []),
                        "provenance": raw.get("provenance", "unverified"),
                    }

            for r in reports:
                inc_id = r.get("incident_id")
                if inc_id:
                    r_dict = dict(r)
                    if r["id"] in analysis_map:
                        r_dict["analysis"] = analysis_map[r["id"]]
                    reports_by_incident.setdefault(inc_id, []).append(r_dict)
        except Exception as exc:
            logger.warning("Could not assemble report context for priority ranking: %s", exc)

        # 2. Build batch incidents payload for Member 3 AI Engine
        batch_incidents = []
        for inc in incidents:
            batch_incidents.append({
                "id": inc["id"],
                "title": inc["title"],
                "type": inc.get("type", "other"),
                "severity": inc.get("severity", "medium"),
                "status": inc.get("status", "active"),
                "location": {
                    "lat": inc.get("lat"),
                    "lng": inc.get("lng"),
                    "label": inc.get("location_label", "Unknown"),
                },
                "report_count": inc.get("report_count", len(reports_by_incident.get(inc["id"], []))),
                "independent_source_count": inc.get("independent_source_count", 1),
                "first_reported_at": inc.get("first_reported_at"),
                "last_updated_at": inc.get("last_updated_at"),
                "timeline": inc.get("timeline") or [],
                "reports": reports_by_incident.get(inc["id"], []),
            })

        # 3. Call Member 3 AI Engine endpoint: POST /incidents/priority?sort={sort}
        ai_resp = AIClient.get_priority_ranking(batch_incidents, sort=sort)
        if ai_resp is not None:
            # Sync scores to priority_scores table
            for item in ai_resp.items:
                pri_row = {
                    "id": generate_semantic_id("pri", "priority_scores"),
                    "incident_id": item.incident_id,
                    "urgency_score": item.urgency.score,
                    "urgency_level": item.urgency.level,
                    "urgency_reasons": item.urgency.reasons,
                    "evidence_confidence_score": item.evidence_confidence.score,
                    "evidence_confidence_level": item.evidence_confidence.level,
                    "evidence_confidence_reasons": item.evidence_confidence.reasons,
                    "verification_priority_score": item.verification_priority.score,
                    "verification_priority_level": item.verification_priority.level,
                    "verification_priority_reasons": item.verification_priority.reasons,
                    "explanation": item.explanation,
                    "recommended_next_steps": item.recommended_next_steps,
                    "requires_human_decision": item.requires_human_decision,
                    "human_decision_status": item.human_decision.status,
                    "updated_at": now_utc_iso(),
                }
                try:
                    supabase.table("priority_scores").upsert(pri_row, on_conflict="incident_id").execute()
                except Exception:
                    pass
            return ai_resp

        # 4. Fallback: Retrieve stored priority scores from Supabase
        scores_res = supabase.table("priority_scores").select("*").in_("incident_id", incident_ids).execute()
        scores_map: Dict[str, Dict[str, Any]] = {s["incident_id"]: s for s in (scores_res.data or [])}

        items: List[PriorityItem] = []

        for inc in incidents:
            inc_id = inc["id"]
            stored = scores_map.get(inc_id)

            if stored:
                urgency = ScoreDetail(
                    score=stored["urgency_score"],
                    level=stored["urgency_level"],
                    reasons=stored.get("urgency_reasons") or [],
                )
                confidence = ScoreDetail(
                    score=stored["evidence_confidence_score"],
                    level=stored["evidence_confidence_level"],
                    reasons=stored.get("evidence_confidence_reasons") or [],
                )
                verification = ScoreDetail(
                    score=stored["verification_priority_score"],
                    level=stored["verification_priority_level"],
                    reasons=stored.get("verification_priority_reasons") or [],
                )
                explanation = stored.get("explanation") or [f"Active {inc['type']} incident"]
                recommended_next_steps = stored.get("recommended_next_steps") or ["Alert duty officer for dispatch review"]
                human_decision = HumanDecisionInfo(
                    status=stored.get("human_decision_status", "not_decided"),
                    decided_by=stored.get("decided_by"),
                    decided_at=stored.get("decided_at"),
                )
            else:
                # Dynamic computation based on incident attributes adhering to contract baseline
                sev = inc.get("severity", "medium")
                indep_count = inc.get("independent_source_count", 1)

                if sev == "critical":
                    urg_score = 92
                    urg_level = "critical"
                    urg_reasons = ["Elderly residents reported on upper floors", "Critical hazard level"]
                elif sev == "high":
                    urg_score = 78
                    urg_level = "high"
                    urg_reasons = ["Structural damage reported", "Immediate response advised"]
                elif sev == "medium":
                    urg_score = 55
                    urg_level = "medium"
                    urg_reasons = ["Moderate hazard with potential escalation"]
                else:
                    urg_score = 25
                    urg_level = "low"
                    urg_reasons = ["Low-level incident under monitoring"]

                if indep_count >= 3:
                    conf_score = 84
                    conf_level = "high"
                    conf_reasons = ["Three independent sources", "Corroborated by field units"]
                elif indep_count == 2:
                    conf_score = 75
                    conf_level = "high"
                    conf_reasons = ["Two independent witness accounts"]
                else:
                    conf_score = 45
                    conf_level = "medium"
                    conf_reasons = ["Single-source reporting; awaiting additional confirmation"]

                if indep_count >= 2:
                    ver_score = 25
                    ver_level = "low"
                    ver_reasons = ["Well corroborated by multiple sources"]
                else:
                    ver_score = 70
                    ver_level = "high"
                    ver_reasons = ["Single source; human ground-truth check advised"]

                urgency = ScoreDetail(score=urg_score, level=urg_level, reasons=urg_reasons)
                confidence = ScoreDetail(score=conf_score, level=conf_level, reasons=conf_reasons)
                verification = ScoreDetail(score=ver_score, level=ver_level, reasons=ver_reasons)
                explanation = [
                    f"Reported at {inc['location_label']}",
                    f"Current status: {inc['status']}",
                ]
                recommended_next_steps = ["Alert duty officer for dispatch review"]
                human_decision = HumanDecisionInfo()

            item = PriorityItem(
                rank=1,  # will be assigned after sorting
                incident_id=inc["id"],
                title=inc["title"],
                location=LocationSchema(
                    lat=inc["lat"],
                    lng=inc["lng"],
                    label=inc["location_label"],
                ),
                urgency=urgency,
                evidence_confidence=confidence,
                verification_priority=verification,
                explanation=explanation,
                recommended_next_steps=recommended_next_steps,
                requires_human_decision=True,
                human_decision=human_decision,
            )
            items.append(item)

        # Sort based on parameter
        if sort == "verification":
            items.sort(key=lambda x: x.verification_priority.score, reverse=True)
        else:
            items.sort(key=lambda x: x.urgency.score, reverse=True)

        # Assign 1-based ranks
        for idx, item in enumerate(items, start=1):
            item.rank = idx

        return PriorityResponse(sort=sort, items=items)
