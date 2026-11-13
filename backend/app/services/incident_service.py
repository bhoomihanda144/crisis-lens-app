"""
CrisisLens Incident Service
Handles database operations for emergency incidents adhering to API Contract v1.0.
"""
from typing import List, Optional, Tuple, Dict, Any
from app.database.supabase_client import get_supabase_client
from app.schemas.incident import IncidentResponse, TimelineEntry
from app.schemas.common import LocationSchema, IncidentType, IncidentSeverity, IncidentStatus
from app.core.exceptions import NotFoundException


def _build_incident_response(
    row: Dict[str, Any],
    report_ids: Optional[List[str]] = None,
) -> IncidentResponse:
    """Transforms a Supabase row into an API-compliant IncidentResponse."""
    raw_timeline = row.get("timeline") or []
    # Ensure timeline entries are sorted oldest first
    sorted_timeline = sorted(raw_timeline, key=lambda x: x.get("timestamp", ""))

    timeline_entries = [
        TimelineEntry(
            timestamp=item["timestamp"],
            severity=IncidentSeverity(item["severity"]),
            status=IncidentStatus(item["status"]),
            report_count=item.get("report_count", 0),
            affected_radius_m=item.get("affected_radius_m", 0),
            summary=item.get("summary", ""),
        )
        for item in sorted_timeline
    ]

    assigned_reports = report_ids if report_ids is not None else []

    return IncidentResponse(
        id=row["id"],
        title=row["title"],
        type=IncidentType(row["type"]),
        location=LocationSchema(
            lat=row["lat"],
            lng=row["lng"],
            label=row["location_label"],
        ),
        severity=IncidentSeverity(row["severity"]),
        status=IncidentStatus(row["status"]),
        report_ids=assigned_reports,
        report_count=row.get("report_count", len(assigned_reports)),
        independent_source_count=row.get("independent_source_count", 0),
        first_reported_at=row["first_reported_at"],
        last_updated_at=row["last_updated_at"],
        timeline=timeline_entries,
    )


class IncidentService:
    @staticmethod
    def get_incident_by_id(incident_id: str) -> IncidentResponse:
        supabase = get_supabase_client()
        res = supabase.table("incidents").select("*").eq("id", incident_id).limit(1).execute()
        if not res.data:
            raise NotFoundException("Incident", incident_id)

        incident_row = res.data[0]

        # Retrieve associated report IDs
        reports_res = supabase.table("reports").select("id").eq("incident_id", incident_id).execute()
        report_ids = [r["id"] for r in (reports_res.data or [])]

        return _build_incident_response(incident_row, report_ids=report_ids)

    @staticmethod
    def list_incidents(
        status_filter: Optional[str] = None,
        severity_filter: Optional[str] = None,
        type_filter: Optional[str] = None,
    ) -> Tuple[List[IncidentResponse], int]:
        supabase = get_supabase_client()
        query = supabase.table("incidents").select("*")

        if status_filter:
            query = query.eq("status", status_filter)
        if severity_filter:
            query = query.eq("severity", severity_filter)
        if type_filter:
            query = query.eq("type", type_filter)

        res = query.order("first_reported_at", desc=True).execute()
        rows = res.data or []

        if not rows:
            return [], 0

        # Batch fetch all associated report IDs for these incidents
        incident_ids = [r["id"] for r in rows]
        reports_res = supabase.table("reports").select("id, incident_id").in_("incident_id", incident_ids).execute()

        report_map: Dict[str, List[str]] = {inc_id: [] for inc_id in incident_ids}
        for r in reports_res.data or []:
            inc_id = r.get("incident_id")
            if inc_id in report_map:
                report_map[inc_id].append(r["id"])

        items = [
            _build_incident_response(row, report_ids=report_map.get(row["id"], []))
            for row in rows
        ]
        return items, len(items)
