"""
CrisisLens Analysis Service
Orchestrates AI analysis, persists intelligence to Supabase, updates graph edges,
and manages report status transitions.
"""
from typing import Dict, Any, List
from app.database.supabase_client import get_supabase_client
from app.services.ai_client import AIClient
from app.services.report_service import ReportService
from app.schemas.report import ReportResponse
from app.schemas.common import ReportStatus
from app.utils.id_generator import generate_semantic_id, generate_edge_id
from app.core.exceptions import NotFoundException


class AnalysisService:
    @staticmethod
    async def analyze_report(report_id: str) -> ReportResponse:
        supabase = get_supabase_client()

        # 1. Fetch target report
        res = supabase.table("reports").select("*").eq("id", report_id).limit(1).execute()
        if not res.data:
            raise NotFoundException("Report", report_id)

        target_report = res.data[0]

        # 2. Fetch context reports (all other existing reports)
        other_reports_res = supabase.table("reports").select("*").neq("id", report_id).limit(50).execute()
        existing_reports = other_reports_res.data or []

        # 3. Call AI Client (Member 3 or fallback)
        analysis_data = await AIClient.analyze_report(target_report, existing_reports)

        # 4. Upsert into analysis_results
        scores = analysis_data["scores"]
        analysis_id = generate_semantic_id("anl", "analysis_results")

        analysis_row = {
            "id": analysis_id,
            "report_id": report_id,
            "incident_id": target_report.get("incident_id"),
            "analyzed_at": analysis_data["analyzed_at"],
            "engine_version": analysis_data["engine_version"],
            "urgency_score": scores["urgency"]["score"],
            "evidence_confidence_score": scores["evidence_confidence"]["score"],
            "verification_priority_score": scores["verification_priority"]["score"],
            "raw_analysis": analysis_data,
        }

        # Remove existing analysis record if any, then insert
        supabase.table("analysis_results").delete().eq("report_id", report_id).execute()
        supabase.table("analysis_results").insert(analysis_row).execute()

        # 4b. Persist scores into priority_scores (upsert by incident_id)
        # This keeps the priority dashboard consistent with analysis results
        incident_id = target_report.get("incident_id")
        if incident_id:
            pri_id = generate_semantic_id("pri", "priority_scores")
            recommendation = analysis_data.get("recommendation", {})
            priority_row = {
                "id": pri_id,
                "incident_id": incident_id,
                "urgency_score": scores["urgency"]["score"],
                "urgency_level": scores["urgency"]["level"],
                "urgency_reasons": scores["urgency"]["reasons"],
                "evidence_confidence_score": scores["evidence_confidence"]["score"],
                "evidence_confidence_level": scores["evidence_confidence"]["level"],
                "evidence_confidence_reasons": scores["evidence_confidence"]["reasons"],
                "verification_priority_score": scores["verification_priority"]["score"],
                "verification_priority_level": scores["verification_priority"]["level"],
                "verification_priority_reasons": scores["verification_priority"]["reasons"],
                "explanation": recommendation.get("next_steps", []),
                "recommended_next_steps": recommendation.get("next_steps", []),
                "requires_human_decision": True,
                "human_decision_status": "not_decided",
                "updated_at": analysis_data["analyzed_at"],
            }
            try:
                supabase.table("priority_scores").upsert(priority_row, on_conflict="incident_id").execute()
            except Exception:
                # Upsert failed (e.g. no unique constraint); fall back to delete+insert
                try:
                    supabase.table("priority_scores").delete().eq("incident_id", incident_id).execute()
                    supabase.table("priority_scores").insert(priority_row).execute()
                except Exception:
                    pass

        # 5. Update report status to 'analyzed'
        supabase.table("reports").update({"status": ReportStatus.ANALYZED.value}).eq("id", report_id).execute()

        # 6. Record graph edges in report_relationships
        duplicate_info = analysis_data.get("duplicate", {})
        matches = duplicate_info.get("matches", [])
        for match in matches:
            matched_id = match.get("report_id")
            if matched_id and matched_id != report_id:
                similarity = match.get("similarity", 0.9)
                edge_row = {
                    "id": generate_edge_id(),
                    "source_report_id": report_id,       # later/derived report
                    "target_report_id": matched_id,      # earlier/reference report
                    "type": "duplicate",
                    "confidence": similarity,
                    "label": f"Duplicate ({similarity:.2f})",
                }
                try:
                    # Ignore duplicate edges if already present
                    supabase.table("report_relationships").insert(edge_row).execute()
                except Exception:
                    pass

        # Also record forwarded relationship if applicable
        if target_report.get("forwarded_from"):
            fwd_target = target_report["forwarded_from"]
            if fwd_target != report_id:
                edge_row = {
                    "id": generate_edge_id(),
                    "source_report_id": report_id,
                    "target_report_id": fwd_target,
                    "type": "forwarded",
                    "confidence": 0.95,
                    "label": "Forwarded copy",
                }
                try:
                    supabase.table("report_relationships").insert(edge_row).execute()
                except Exception:
                    pass

        # 7. Return refreshed report object with analysis populated
        return ReportService.get_report_by_id(report_id)
