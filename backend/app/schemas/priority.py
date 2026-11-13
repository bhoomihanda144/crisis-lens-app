"""
CrisisLens Priority Schemas
Strictly conforms to API Contract v1.0 Section 4.7.
Three separate scores: Urgency, Evidence Confidence, Verification Priority.
"""
from typing import List, Optional
from pydantic import BaseModel, Field
from app.schemas.common import LocationSchema, ScoreDetail


class HumanDecisionInfo(BaseModel):
    status: str = "not_decided"
    decided_by: Optional[str] = None
    decided_at: Optional[str] = None


class PriorityItem(BaseModel):
    rank: int = Field(..., ge=1, description="Ranking position (1-based)")
    incident_id: str
    title: str
    location: LocationSchema
    urgency: ScoreDetail
    evidence_confidence: ScoreDetail
    verification_priority: ScoreDetail
    explanation: List[str] = Field(default_factory=list)
    recommended_next_steps: List[str] = Field(default_factory=list)
    requires_human_decision: bool = True
    human_decision: HumanDecisionInfo = Field(default_factory=HumanDecisionInfo)


class PriorityResponse(BaseModel):
    sort: str = Field(..., description="Sorting criterion: 'urgency' or 'verification'")
    items: List[PriorityItem]
