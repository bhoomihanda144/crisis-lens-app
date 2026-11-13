"""What-if Simulation schemas for CrisisLens API Contract v1.0.

Single source of truth: docs/api-contract.md (Section 4.9)
Member 3 logic, Member 2 serves.
"""

from typing import List, Literal
from pydantic import BaseModel, ConfigDict, Field


class SimulationRequest(BaseModel):
    """Request payload for POST /simulate."""
    model_config = ConfigDict(extra="forbid")

    scenario_name: str = Field(..., min_length=1, description="Descriptive scenario name")
    affected_population: int = Field(..., ge=0, description="Estimated affected population")
    disaster_severity: int = Field(..., ge=1, le=5, description="Severity integer from 1 to 5")
    rescue_teams: int = Field(..., ge=0, description="Available rescue teams")
    blocked_roads: int = Field(..., ge=0, description="Number of blocked arterial roads")
    available_ambulances: int = Field(..., ge=0, description="Available emergency ambulances")


class ResourceDemand(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rescue_teams: int = Field(..., ge=0, description="Demanded rescue teams")
    ambulances: int = Field(..., ge=0, description="Demanded ambulances")


class ResourceShortage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resource: str = Field(..., min_length=1, description="Resource name, e.g. rescue_teams, ambulances")
    required: int = Field(..., ge=0, description="Required amount")
    available: int = Field(..., ge=0, description="Available amount")
    shortfall: int = Field(..., ge=0, description="Shortfall (required - available)")


class PriorityChange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    incident_id: str = Field(..., description="Incident ID")
    title: str = Field(..., min_length=1, description="Incident title")
    baseline_rank: int = Field(..., ge=1, description="Baseline priority rank")
    scenario_rank: int = Field(..., ge=1, description="Simulated scenario rank")
    reason: str = Field(..., min_length=1, description="Reason for priority change")


class SimulationResults(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resource_demand: ResourceDemand
    shortages: List[ResourceShortage] = Field(default_factory=list)
    estimated_response_delay_minutes: int = Field(..., ge=0)
    priority_changes: List[PriorityChange] = Field(default_factory=list)
    summary: str = Field(..., min_length=1)


class SimulationResponse(BaseModel):
    """Response payload for POST /simulate."""
    model_config = ConfigDict(extra="forbid")

    scenario_id: str = Field(..., description="Unique simulation run identifier")
    is_simulation: Literal[True] = Field(
        True,
        description="Always true. Marks output as simulated to prevent mixing with real operations."
    )
    generated_at: str = Field(..., description="ISO 8601 UTC timestamp")
    inputs: SimulationRequest
    results: SimulationResults
