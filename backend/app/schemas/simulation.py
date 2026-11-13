"""
CrisisLens Simulation Schemas
Strictly conforms to API Contract v1.0 Section 4.9.
Simulations are isolated from live disaster records (is_simulation: true).
"""
from typing import List, Dict, Any
from pydantic import BaseModel, Field


class SimulationRequest(BaseModel):
    scenario_name: str = Field(..., min_length=1, description="Descriptive name of the hypothetical scenario")
    affected_population: int = Field(..., ge=0, description="Estimated number of affected citizens")
    disaster_severity: int = Field(..., ge=1, le=5, description="Severity rating on 1-5 scale")
    rescue_teams: int = Field(..., ge=0, description="Number of currently available rescue teams")
    blocked_roads: int = Field(..., ge=0, description="Number of impassable or blocked arterial routes")
    available_ambulances: int = Field(..., ge=0, description="Number of currently operational ambulances")


class ResourceDemand(BaseModel):
    rescue_teams: int = Field(..., ge=0)
    ambulances: int = Field(..., ge=0)


class ResourceShortage(BaseModel):
    resource: str
    required: int = Field(..., ge=0)
    available: int = Field(..., ge=0)
    shortfall: int = Field(..., ge=0)


class PriorityChange(BaseModel):
    incident_id: str
    title: str
    baseline_rank: int = Field(..., ge=1)
    scenario_rank: int = Field(..., ge=1)
    reason: str


class SimulationResults(BaseModel):
    resource_demand: ResourceDemand
    shortages: List[ResourceShortage] = Field(default_factory=list)
    estimated_response_delay_minutes: int = Field(..., ge=0)
    priority_changes: List[PriorityChange] = Field(default_factory=list)
    summary: str


class SimulationResponse(BaseModel):
    scenario_id: str = Field(..., description="Semantic simulation ID, e.g. sim_001")
    is_simulation: bool = True
    generated_at: str
    inputs: SimulationRequest
    results: SimulationResults
