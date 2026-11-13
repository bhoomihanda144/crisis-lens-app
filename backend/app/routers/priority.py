"""
CrisisLens Incident Priority Router
Implements GET /incidents/priority per API Contract v1.0 Section 4.7.
"""
from fastapi import APIRouter, Query, status
from app.schemas.priority import PriorityResponse
from app.services.priority_service import PriorityService

router = APIRouter(prefix="/incidents", tags=["Smart Rescue Priority"])


@router.get(
    "/priority",
    response_model=PriorityResponse,
    status_code=status.HTTP_200_OK,
    summary="Get rescue priority queue",
    description="Returns ranked priority recommendations sorted by urgency (default) or verification need. All three scores are kept separate.",
)
def get_priority_ranking(
    sort: str = Query("urgency", pattern="^(urgency|verification)$", description="Sort criteria: 'urgency' or 'verification'"),
):
    return PriorityService.get_priority_ranking(sort=sort)
