"""
CrisisLens Incidents Router
Implements GET /incidents, GET /incidents/{id} per API Contract v1.0.
"""
from typing import Optional
from fastapi import APIRouter, Query, status
from app.schemas.incident import IncidentResponse, IncidentListResponse
from app.services.incident_service import IncidentService

router = APIRouter(prefix="/incidents", tags=["Incidents"])


@router.get(
    "",
    response_model=IncidentListResponse,
    status_code=status.HTTP_200_OK,
    summary="List emergency incidents",
    description="Retrieve all aggregated incidents with optional status, severity, and type filters.",
)
def list_incidents(
    status: Optional[str] = Query(None, description="Filter by status: active, monitoring, resolved"),
    severity: Optional[str] = Query(None, description="Filter by severity: low, medium, high, critical"),
    type: Optional[str] = Query(None, description="Filter by type: flood, fire, earthquake, etc."),
):
    items, total = IncidentService.list_incidents(
        status_filter=status,
        severity_filter=severity,
        type_filter=type,
    )
    return IncidentListResponse(items=items, total=total)


@router.get(
    "/{id}",
    response_model=IncidentResponse,
    status_code=status.HTTP_200_OK,
    summary="Get single incident",
    description="Returns detailed incident record including associated report IDs and chronological timeline.",
)
def get_incident(id: str):
    return IncidentService.get_incident_by_id(id)
