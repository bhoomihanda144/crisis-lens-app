"""
CrisisLens Reports Router
Implements POST /reports, GET /reports, GET /reports/{id} per API Contract v1.0.
"""
from typing import Optional
from fastapi import APIRouter, Query, status
from app.schemas.report import ReportCreate, ReportResponse, ReportListResponse
from app.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.post(
    "",
    response_model=ReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a new emergency report",
    description="Submits a report. Initial status is 'pending_analysis' and analysis is null.",
)
def create_report(payload: ReportCreate):
    return ReportService.create_report(payload)


@router.get(
    "",
    response_model=ReportListResponse,
    status_code=status.HTTP_200_OK,
    summary="List emergency reports",
    description="Retrieve reports with filtering and sorting (e.g. Verify-First queue).",
)
def list_reports(
    q: Optional[str] = Query(None, description="Search report text"),
    status: Optional[str] = Query(None, description="Filter by report status"),
    freshness: Optional[str] = Query(None, description="Filter by freshness status: recent, aging, stale"),
    incident_id: Optional[str] = Query(None, description="Filter by associated incident ID"),
    sort: str = Query("newest", description="Sort order: 'newest' or 'verification_priority'"),
    limit: int = Query(50, ge=1, le=100, description="Page limit"),
    offset: int = Query(0, ge=0, description="Page offset"),
):
    items, total = ReportService.list_reports(
        q=q,
        status_filter=status,
        freshness_filter=freshness,
        incident_id=incident_id,
        sort=sort,
        limit=limit,
        offset=offset,
    )
    return ReportListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{id}",
    response_model=ReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Get single report",
    description="Returns an individual report with analysis and verification if available.",
)
def get_report(id: str):
    return ReportService.get_report_by_id(id)
