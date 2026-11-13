"""
CrisisLens Analysis Schemas
Strictly conforms to API Contract v1.0 Section 3 (Analysis) and Section 4.6.
"""
from typing import List, Optional
from pydantic import BaseModel, Field
from app.schemas.common import (
    FreshnessSchema,
    ScoreDetail,
    IndependenceType,
    CorroborationStatus,
    RecommendationType,
    RelationshipType,
)


class DuplicateMatch(BaseModel):
    report_id: str
    similarity: float = Field(..., ge=0.0, le=1.0)
    reasons: List[str] = Field(default_factory=list)


class DuplicateInfo(BaseModel):
    is_duplicate: bool = False
    matches: List[DuplicateMatch] = Field(default_factory=list)


class RelatedReport(BaseModel):
    report_id: str
    relation: RelationshipType


class SourceVerificationInfo(BaseModel):
    independence: IndependenceType = IndependenceType.INDEPENDENT
    original_report_id: Optional[str] = None
    related: List[RelatedReport] = Field(default_factory=list)
    corroboration_status: CorroborationStatus = CorroborationStatus.SINGLE_SOURCE


class ConflictingStatement(BaseModel):
    report_id: str
    text: str


class ConflictItem(BaseModel):
    id: str
    topic: str
    report_ids: List[str] = Field(default_factory=list)
    statements: List[ConflictingStatement] = Field(default_factory=list)
    detected_at: str


class RecommendationInfo(BaseModel):
    type: RecommendationType
    summary: str
    next_steps: List[str] = Field(default_factory=list)
    requires_human_decision: bool = True


class AnalysisScores(BaseModel):
    urgency: ScoreDetail
    evidence_confidence: ScoreDetail
    verification_priority: ScoreDetail


class AnalysisObject(BaseModel):
    analyzed_at: str
    engine_version: str = "0.1.0"
    duplicate: DuplicateInfo
    source_verification: SourceVerificationInfo
    freshness: FreshnessSchema
    conflicts: List[ConflictItem] = Field(default_factory=list)
    scores: AnalysisScores
    recommendation: RecommendationInfo
