"""FastAPI route definitions for CrisisLens AI Engine."""

from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict

from ai_engine.schemas.enums import PrioritySort
from ai_engine.schemas.internal import (
    AnalyzeRequest,
    GenerateGraphRequest,
    PriorityRankRequest,
    SimulationScenarioRequest,
)
from ai_engine.schemas.analysis import Analysis
from ai_engine.schemas.incident import PriorityResponse
from ai_engine.schemas.graph import EvidenceGraphResponse
from ai_engine.schemas.simulation import SimulationRequest, SimulationResponse
from ai_engine.modules.analyzer import ReportAnalyzer
from ai_engine.modules.graph import EvidenceGraphBuilder, GraphValidationError
from ai_engine.modules.priority import IncidentPriorityRanker
from ai_engine.modules.simulation import DisasterSimulationEngine

router = APIRouter()


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    service: str
    version: str
    port: int
    stage: str


@router.get("/health", response_model=HealthResponse, tags=["Health"])
def get_health() -> HealthResponse:
    """Health check endpoint to verify AI engine status and connectivity."""
    return HealthResponse(
        status="healthy",
        service="crisis-lens-ai-engine",
        version="0.1.0",
        port=8001,
        stage="Stage 6 - Simulation Engine Active",
    )


@router.post("/analyze", response_model=Analysis, tags=["Analysis"])
def analyze_report_endpoint(request: AnalyzeRequest) -> Analysis:
    """Analyzes an emergency report in context of existing reports.

    Produces full contract-compliant Analysis object including duplicate detection,
    source independence, freshness calculation, conflicts, and 3-dimensional scores.
    """
    return ReportAnalyzer.analyze(
        report=request.report,
        context_reports=request.context_reports,
    )


@router.post(
    "/incidents/{incident_id}/evidence-graph",
    response_model=EvidenceGraphResponse,
    status_code=status.HTTP_200_OK,
    tags=["Evidence Graph"],
    summary="Generate incident evidence relationship graph",
)
def generate_incident_evidence_graph(
    incident_id: str,
    request: GenerateGraphRequest,
) -> EvidenceGraphResponse:
    """Generates an Evidence Relationship Graph for a specific incident.

    Adheres strictly to API Contract v1.0 Section 4.8:
    - Node id equals report id
    - Edge directed from later/derived report (source) to earlier/reference report (target)
    - Validates DAG, self-loops, and edge directions using NetworkX
    """
    target_incident_id = incident_id or request.incident_id
    try:
        return EvidenceGraphBuilder.build_graph(
            incident_id=target_incident_id,
            reports=request.reports,
            conflicts=request.conflicts or [],
        )
    except GraphValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": {"code": "validation_error", "message": str(e), "details": None}},
        )


@router.post(
    "/graph/generate",
    response_model=EvidenceGraphResponse,
    status_code=status.HTTP_200_OK,
    tags=["Evidence Graph"],
    summary="Generate evidence relationship graph (RPC style)",
)
def generate_graph_rpc(request: GenerateGraphRequest) -> EvidenceGraphResponse:
    """Generates an Evidence Relationship Graph from a GenerateGraphRequest payload."""
    try:
        return EvidenceGraphBuilder.build_graph(
            incident_id=request.incident_id,
            reports=request.reports,
            conflicts=request.conflicts or [],
        )
    except GraphValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": {"code": "validation_error", "message": str(e), "details": None}},
        )


@router.post(
    "/incidents/priority",
    response_model=PriorityResponse,
    status_code=status.HTTP_200_OK,
    tags=["Priority Ranking"],
    summary="Compute incident rescue priority ranking",
)
def compute_priority_ranking(
    request: PriorityRankRequest,
    sort: Optional[str] = Query(None, description="Optional query sort override: 'urgency' or 'verification'"),
) -> PriorityResponse:
    """Computes deterministic incident priority ranking according to API Contract v1.0 Section 4.7.

    Precedence Rule:
    - If query parameter 'sort' is provided, it must be 'urgency' or 'verification', and overrides request.sort.
    - If query parameter 'sort' is not provided, request.sort from the request body is used.
    - Invalid sort values raise HTTP 422 validation_error.
    """
    effective_sort = request.sort
    if sort is not None:
        if sort.lower() in ["urgency", "verification"]:
            effective_sort = PrioritySort(sort.lower())
        else:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"error": {"code": "validation_error", "message": f"Invalid sort parameter '{sort}'. Must be 'urgency' or 'verification'.", "details": None}},
            )

    return IncidentPriorityRanker.rank_incidents(
        incidents=request.incidents,
        sort=effective_sort,
    )


@router.post(
    "/priority/rank",
    response_model=PriorityResponse,
    status_code=status.HTTP_200_OK,
    tags=["Priority Ranking"],
    summary="Compute incident rescue priority ranking (RPC alias)",
)
def compute_priority_ranking_rpc(
    request: PriorityRankRequest,
    sort: Optional[str] = Query(None, description="Optional query sort override: 'urgency' or 'verification'"),
) -> PriorityResponse:
    """RPC alias for computing incident priority ranking."""
    return compute_priority_ranking(request=request, sort=sort)


@router.post(
    "/simulate",
    response_model=SimulationResponse,
    status_code=status.HTTP_200_OK,
    tags=["What-If Simulation"],
    summary="Run what-if emergency disaster simulation",
)
def run_simulation(request: SimulationRequest) -> SimulationResponse:
    """Computes deterministic what-if emergency scenario simulation per API Contract v1.0 Section 4.9.

    Calculates:
    - Resource demand (rescue teams and ambulances)
    - Resource shortages (positive shortfalls)
    - Estimated compound response delay
    - Hypothetical priority ranking changes
    """
    return DisasterSimulationEngine.run_simulation(request)


@router.post(
    "/simulation/run",
    response_model=SimulationResponse,
    status_code=status.HTTP_200_OK,
    tags=["What-If Simulation"],
    summary="Run what-if emergency disaster simulation (RPC alias)",
)
def run_simulation_rpc(request: SimulationScenarioRequest) -> SimulationResponse:
    """RPC alias supporting optional active incident context for hypothetical priority re-ranking."""
    return DisasterSimulationEngine.run_simulation(request)


@router.get("/", tags=["Root"])
def get_root() -> Dict[str, Any]:
    """Root metadata endpoint."""
    return {
        "service": "CrisisLens AI Engine Microservice",
        "version": "0.1.0",
        "docs_url": "/docs",
        "health_url": "/health",
        "analyze_url": "/analyze",
        "graph_url": "/graph/generate",
        "incident_graph_url": "/incidents/{id}/evidence-graph",
        "priority_url": "/incidents/priority",
        "priority_rpc_url": "/priority/rank",
        "simulate_url": "/simulate",
        "simulation_rpc_url": "/simulation/run",
        "port": 8001,
    }
