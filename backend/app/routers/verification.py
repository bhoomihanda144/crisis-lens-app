"""
CrisisLens Human Verification Router
Implements PATCH /reports/{id}/verify per API Contract v1.0 Section 4.10.
"""
from fastapi import APIRouter, status
from app.schemas.verification import VerificationRequest
from app.schemas.report import ReportResponse
from app.services.verification_service import VerificationService

router = APIRouter(prefix="/reports", tags=["Human Verification"])


@router.patch(
    "/{id}/verify",
    response_model=ReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Human verification of emergency report",
    description="Action can be 'confirm' (status -> verified), 'reject' (status -> rejected), or 'request_more_info' (status -> needs_more_info).",
)
def verify_report(id: str, payload: VerificationRequest):
    return VerificationService.verify_report(id, payload)
