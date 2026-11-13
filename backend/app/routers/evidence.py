"""
CrisisLens Evidence Relationship Graph Router
Implements GET /incidents/{id}/evidence-graph per API Contract v1.0 Section 4.8.
"""
from fastapi import APIRouter, status
from app.schemas.evidence import EvidenceGraphResponse
from app.services.evidence_service import EvidenceService

router = APIRouter(prefix="/incidents", tags=["Evidence Relationship Graph"])


@router.get(
    "/{id}/evidence-graph",
    response_model=EvidenceGraphResponse,
    status_code=status.HTTP_200_OK,
    summary="Get incident evidence relationship graph",
    description="Returns nodes (reports) and directed edges (later/derived -> earlier/reference) for graph visualization.",
)
def get_evidence_graph(id: str):
    return EvidenceService.get_evidence_graph(id)
