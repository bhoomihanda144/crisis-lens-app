"""
CrisisLens Analysis Router
Implements POST /analyze/{report_id} per API Contract v1.0 Section 4.6.
"""
from fastapi import APIRouter, status
from app.schemas.report import ReportResponse
from app.services.analysis_service import AnalysisService

router = APIRouter(tags=["AI Analysis"])


@router.post(
    "/analyze/{report_id}",
    response_model=ReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze report with AI Engine",
    description="Runs AI intelligence on the report, stores duplicate/conflict/score results, and updates report status to 'analyzed'.",
)
async def analyze_report(report_id: str):
    return await AnalysisService.analyze_report(report_id)
