"""
CrisisLens Report Service
Handles database operations for reports adhering to API Contract v1.0.
"""
from typing import List, Optional, Tuple, Dict, Any
from app.database.supabase_client import get_supabase_client
from app.schemas.report import ReportCreate, ReportResponse, VerificationInfo
from app.schemas.common import SourceSchema, LocationSchema, ReportStatus
from app.utils.id_generator import generate_report_id
from app.utils.datetime_utils import now_utc_iso, calculate_freshness
from app.core.exceptions import NotFoundException, ValidationException


def _build_report_response(
    row: Dict[str, Any],
    analysis: Optional[Dict[str, Any]] = None,
    verification: Optional[Dict[str, Any]] = None,
) -> ReportResponse:
    """Transforms a Supabase row into an API-compliant ReportResponse."""
    ver_obj = None
    if verification:
        ver_obj = VerificationInfo(
            action=verification["action"],
            note=verification.get("note"),
            verified_by=verification.get("verified_by"),
            verified_at=verification["verified_at"],
        )

    return ReportResponse(
        id=row["id"],
        text=row["text"],
        source=SourceSchema(
            type=row["source_type"],
            name=row["source_name"],
        ),
        location=LocationSchema(
            lat=row["lat"],
            lng=row["lng"],
            label=row["location_label"],
        ),
        reported_at=row["reported_at"],
        received_at=row["received_at"],
        status=ReportStatus(row["status"]),
        incident_id=row.get("incident_id"),
        forwarded_from=row.get("forwarded_from"),
        analysis=analysis,
        verification=ver_obj,
    )


class ReportService:
    @staticmethod
    def create_report(payload: ReportCreate) -> ReportResponse:
        supabase = get_supabase_client()
        report_id = generate_report_id()
        current_time = now_utc_iso()
        reported_at = payload.reported_at or current_time

        # Validate forwarded_from reference if provided
        if payload.forwarded_from:
            parent = supabase.table("reports").select("id").eq("id", payload.forwarded_from).limit(1).execute()
            if not parent.data:
                raise ValidationException(f"Forwarded-from report {payload.forwarded_from} does not exist")

        row = {
            "id": report_id,
            "text": payload.text,
            "source_type": payload.source.type.value,
            "source_name": payload.source.name,
            "lat": payload.location.lat,
            "lng": payload.location.lng,
            "location_label": payload.location.label,
            "reported_at": reported_at,
            "received_at": current_time,
            "status": ReportStatus.PENDING_ANALYSIS.value,
            "incident_id": None,
            "forwarded_from": payload.forwarded_from,
        }

        res = supabase.table("reports").insert(row).execute()
        if not res.data:
            raise Exception("Failed to insert report into database")

        created_row = res.data[0]
        return _build_report_response(created_row, analysis=None, verification=None)

    @staticmethod
    def get_report_by_id(report_id: str) -> ReportResponse:
        supabase = get_supabase_client()
        res = supabase.table("reports").select("*").eq("id", report_id).limit(1).execute()
        if not res.data:
            raise NotFoundException("Report", report_id)

        report_row = res.data[0]

        # Fetch associated analysis if present
        analysis_res = supabase.table("analysis_results").select("raw_analysis").eq("report_id", report_id).limit(1).execute()
        analysis = analysis_res.data[0]["raw_analysis"] if analysis_res.data else None

        # Fetch latest verification if present
        ver_res = supabase.table("verifications").select("*").eq("report_id", report_id).order("verified_at", desc=True).limit(1).execute()
        verification = ver_res.data[0] if ver_res.data else None

        return _build_report_response(report_row, analysis=analysis, verification=verification)

    @staticmethod
    def list_reports(
        q: Optional[str] = None,
        status_filter: Optional[str] = None,
        freshness_filter: Optional[str] = None,
        incident_id: Optional[str] = None,
        sort: str = "newest",
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[ReportResponse], int]:
        supabase = get_supabase_client()

        # Build query
        query = supabase.table("reports").select("*", count="exact")

        if q:
            query = query.ilike("text", f"%{q}%")
        if status_filter:
            query = query.eq("status", status_filter)
        if incident_id:
            query = query.eq("incident_id", incident_id)

        # Apply sorting
        if sort == "verification_priority":
            # For verification priority, fetch reports and order by priority score
            # We will query and sort appropriately
            query = query.order("reported_at", desc=True)
        else:
            query = query.order("reported_at", desc=True)

        res = query.execute()
        all_rows = res.data or []

        # Filter by freshness if specified
        if freshness_filter:
            filtered_rows = []
            for r in all_rows:
                freshness = calculate_freshness(r["reported_at"])
                if freshness["status"] == freshness_filter:
                    filtered_rows.append(r)
            all_rows = filtered_rows

        total = len(all_rows)

        # Batch fetch analysis and verifications for these reports
        report_ids = [r["id"] for r in all_rows]
        analysis_map: Dict[str, Any] = {}
        verification_map: Dict[str, Any] = {}

        if report_ids:
            anl_res = supabase.table("analysis_results").select("report_id, raw_analysis, verification_priority_score").in_("report_id", report_ids).execute()
            for a in anl_res.data or []:
                analysis_map[a["report_id"]] = a["raw_analysis"]

            ver_res = supabase.table("verifications").select("*").in_("report_id", report_ids).order("verified_at", desc=True).execute()
            for v in ver_res.data or []:
                if v["report_id"] not in verification_map:
                    verification_map[v["report_id"]] = v

        # Sort by verification_priority if requested (highest score first)
        if sort == "verification_priority":
            def get_ver_score(row):
                anl = analysis_map.get(row["id"])
                if anl and "scores" in anl and "verification_priority" in anl["scores"]:
                    return anl["scores"]["verification_priority"].get("score", 0)
                return -1

            all_rows.sort(key=get_ver_score, reverse=True)

        # Apply limit & offset
        paged_rows = all_rows[offset : offset + limit]

        items = [
            _build_report_response(
                r,
                analysis=analysis_map.get(r["id"]),
                verification=verification_map.get(r["id"]),
            )
            for r in paged_rows
        ]

        return items, total
