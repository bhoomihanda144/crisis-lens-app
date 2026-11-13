"""Incident and Priority schemas for CrisisLens API Contract v1.0.

Single source of truth: docs/api-contract.md (Section 3 & 4.7)
"""

from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field

from ai_engine.schemas.enums import (
    IncidentType,
    IncidentSeverity,
    IncidentStatus,
    PrioritySort,
)
from ai_engine.schemas.common import (
    Location,
    UrgencyScore,
    EvidenceConfidenceScore,
    VerificationPriorityScore,
)


class TimelineEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    timestamp: str = Field(..., description="ISO 8601 UTC timestamp")
    severity: IncidentSeverity
    status: IncidentStatus
    report_count: int = Field(..., ge=1)
    affected_radius_m: int = Field(..., ge=0)
    summary: str = Field(..., min_length=1)


class Incident(BaseModel):
    """Complete Incident object representation."""
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="Incident ID, e.g. inc_001")
    title: str = Field(..., min_length=1)
    type: IncidentType
    location: Location
    severity: IncidentSeverity
    status: IncidentStatus
    report_ids: List[str] = Field(default_factory=list)
    report_count: int = Field(..., ge=0)
    independent_source_count: int = Field(..., ge=0)
    first_reported_at: str = Field(..., description="ISO 8601 UTC timestamp")
    last_updated_at: str = Field(..., description="ISO 8601 UTC timestamp")
    timeline: List[TimelineEntry] = Field(default_factory=list)


class HumanDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str = Field(default="not_decided", description="Always not_decided in v1")
    decided_by: Optional[str] = None
    decided_at: Optional[str] = None


class PriorityItem(BaseModel):
    """Individual ranked item in GET /incidents/priority."""
    model_config = ConfigDict(extra="forbid")

    rank: int = Field(..., ge=1, description="1-indexed rank order")
    incident_id: str = Field(..., description="Incident ID")
    title: str = Field(..., min_length=1)
    location: Location
    urgency: UrgencyScore
    evidence_confidence: EvidenceConfidenceScore
    verification_priority: VerificationPriorityScore
    explanation: List[str] = Field(default_factory=list)
    recommended_next_steps: List[str] = Field(default_factory=list)
    requires_human_decision: Literal[True] = Field(
        True,
        description="Always true. Human responders retain full dispatch authority."
    )
    human_decision: HumanDecision = Field(default_factory=HumanDecision)


class PriorityResponse(BaseModel):
    """Response payload for GET /incidents/priority."""
    model_config = ConfigDict(extra="forbid")

    sort: PrioritySort = Field(..., description="urgency or verification")
    items: List[PriorityItem] = Field(default_factory=list)
