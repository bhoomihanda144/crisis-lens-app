"""
CrisisLens Human Verification Service
Implements PATCH /reports/{id}/verify per API Contract v1.0 Section 4.10.
Manages status mapping:
- confirm          -> verified
- reject           -> rejected
- request_more_info -> needs_more_info
Appends an audit trail record to the verifications table.
"""
from app.database.supabase_client import get_supabase_client
from app.schemas.verification import VerificationRequest
from app.schemas.report import ReportResponse
from app.schemas.common import ReportStatus, VerificationAction
from app.services.report_service import ReportService
from app.utils.id_generator import generate_semantic_id
from app.utils.datetime_utils import now_utc_iso
from app.core.exceptions import NotFoundException


class VerificationService:
    @staticmethod
    def verify_report(report_id: str, payload: VerificationRequest) -> ReportResponse:
        supabase = get_supabase_client()

        # 1. Verify report exists
        rep_res = supabase.table("reports").select("*").eq("id", report_id).limit(1).execute()
        if not rep_res.data:
            raise NotFoundException("Report", report_id)

        # 2. Map verification action to contract status
        status_map = {
            VerificationAction.CONFIRM: ReportStatus.VERIFIED,
            VerificationAction.REJECT: ReportStatus.REJECTED,
            VerificationAction.REQUEST_MORE_INFO: ReportStatus.NEEDS_MORE_INFO,
        }
        new_status = status_map[payload.action]

        ver_id = generate_semantic_id("ver", "verifications")
        verified_at = now_utc_iso()

        # 3. Create verification audit record
        ver_row = {
            "id": ver_id,
            "report_id": report_id,
            "action": payload.action.value,
            "note": payload.note,
            "verified_by": payload.verified_by,
            "verified_at": verified_at,
        }
        supabase.table("verifications").insert(ver_row).execute()

        # 4. Update report status in database
        supabase.table("reports").update({"status": new_status.value}).eq("id", report_id).execute()

        # 5. Return updated report
        return ReportService.get_report_by_id(report_id)
