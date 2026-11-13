"""
CrisisLens Evidence Relationship Graph Schemas
Strictly conforms to API Contract v1.0 Section 4.8.
Node ID equals the Report ID.
Edges point from the later/derived report (source) to the earlier/reference report (target).
"""
from typing import List
from pydantic import BaseModel, Field
from app.schemas.common import SourceType, FreshnessStatus, RelationshipType


class GraphNode(BaseModel):
    id: str = Field(..., description="Node ID equals the report ID")
    report_id: str
    label: str
    role: RelationshipType
    source_type: SourceType
    source_name: str
    timestamp: str
    excerpt: str
    freshness_status: FreshnessStatus


class GraphEdge(BaseModel):
    id: str
    source: str = Field(..., description="Source report ID (later / derived report)")
    target: str = Field(..., description="Target report ID (earlier / reference report)")
    type: RelationshipType
    label: str
    confidence: float = Field(..., ge=0.0, le=1.0)


class EvidenceGraphResponse(BaseModel):
    incident_id: str
    nodes: List[GraphNode]
    edges: List[GraphEdge]
