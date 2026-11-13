"""
CrisisLens What-If Simulation Router
Implements POST /simulate per API Contract v1.0 Section 4.9.
"""
from fastapi import APIRouter, status
from app.schemas.simulation import SimulationRequest, SimulationResponse
from app.services.simulation_service import SimulationService

router = APIRouter(tags=["What-If Emergency Simulation"])


@router.post(
    "/simulate",
    response_model=SimulationResponse,
    status_code=status.HTTP_200_OK,
    summary="Run what-if emergency scenario simulation",
    description="Calculates hypothetical resource demand, shortages, and response delay. Strictly isolated from live disaster records.",
)
def run_simulation(payload: SimulationRequest):
    return SimulationService.run_simulation(payload)
