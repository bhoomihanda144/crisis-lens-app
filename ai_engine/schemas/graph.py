"""Evidence Graph schemas for CrisisLens API Contract v1.0.

Single source of truth: docs/api-contract.md (Section 4.8)
Produced by Member 3 (AI/ML), served by Member 2 (Backend).
"""

from typing import List
from pydantic import BaseModel, ConfigDict, Field

from ai_engine.schemas.enums import (
    RelationshipType,
    SourceType,
    FreshnessStatus,
)


class EvidenceNode(BaseModel):
    """Node in the incident evidence graph."""
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="Unique node id, equals report_id")
    report_id: str = Field(..., description="Underlying report ID")
    label: str = Field(..., min_length=1, description="Brief display label, e.g. Citizen: Lake Road flooding")
    role: RelationshipType = Field(..., description="original, duplicate, forwarded, corroborating, conflicting")
    source_type: SourceType = Field(..., description="citizen, social_media, news, official, sensor, responder")
    source_name: str = Field(..., min_length=1, description="Source display name")
    timestamp: str = Field(..., description="ISO 8601 UTC timestamp")
    excerpt: str = Field(..., description="Short text preview of report")
    freshness_status: FreshnessStatus = Field(..., description="recent, aging, or stale")


class EvidenceEdge(BaseModel):
    """Directed edge in the evidence graph.

    Rule: Edge goes from later or derived report (source) to earlier or reference report (target).
    """
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="Edge identifier, e.g. edge_001")
    source: str = Field(..., description="Later or derived report ID")
    target: str = Field(..., description="Earlier or reference report ID")
    type: RelationshipType = Field(..., description="duplicate, forwarded, corroborating, conflicting")
    label: str = Field(..., description="Edge label, e.g. Duplicate (0.91)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence / similarity value")


class EvidenceGraphResponse(BaseModel):
    """Response payload for GET /incidents/{id}/evidence-graph."""
    model_config = ConfigDict(extra="forbid")

    incident_id: str = Field(..., description="Incident ID")
    nodes: List[EvidenceNode] = Field(default_factory=list)
    edges: List[EvidenceEdge] = Field(default_factory=list)
