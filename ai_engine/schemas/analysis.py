"""Analysis object schemas for CrisisLens API Contract v1.0.

Single source of truth: docs/api-contract.md (Section 3)
Produced by Member 3 (AI/ML), stored and served by Member 2 (Backend).
"""

from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field

from ai_engine.schemas.enums import (
    FreshnessStatus,
    Independence,
    CorroborationStatus,
    RelationshipType,
    RecommendationType,
)
from ai_engine.schemas.common import Scores


class DuplicateMatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    report_id: str = Field(..., description="ID of matching report, e.g. rpt_001")
    similarity: float = Field(..., ge=0.0, le=1.0, description="Similarity score between 0.0 and 1.0")
    reasons: List[str] = Field(default_factory=list, description="Reasons for match detection")


class DuplicateInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_duplicate: bool = Field(..., description="Whether report is identified as duplicate")
    matches: List[DuplicateMatch] = Field(default_factory=list, description="List of matched reports, empty if none")


class RelatedReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    report_id: str = Field(..., description="Referenced report ID")
    relation: RelationshipType = Field(..., description="Relationship type")


class SourceVerification(BaseModel):
    model_config = ConfigDict(extra="forbid")

    independence: Independence = Field(..., description="independent, forwarded, or unknown")
    original_report_id: Optional[str] = Field(None, description="Original report ID if derived/forwarded")
    related: List[RelatedReport] = Field(default_factory=list, description="Related reports and their relationship types")
    corroboration_status: CorroborationStatus = Field(..., description="corroborated, single_source, or disputed")


class FreshnessInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: FreshnessStatus = Field(..., description="recent (<=60m), aging (61-240m), stale (>240m)")
    age_minutes: int = Field(..., ge=0, description="Age of report in minutes")
    last_updated: str = Field(..., description="ISO 8601 UTC timestamp")


class ConflictStatement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    report_id: str = Field(..., description="Report providing this statement")
    text: str = Field(..., description="Extracted statement or report text")


class ConflictItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="Conflict ID, e.g. cfl_001")
    topic: str = Field(..., description="Topic of contradiction, e.g. Extent of damage")
    report_ids: List[str] = Field(..., min_length=2, description="IDs of reports in conflict")
    statements: List[ConflictStatement] = Field(..., min_length=2, description="Conflicting statements")
    detected_at: str = Field(..., description="ISO 8601 UTC timestamp")


class Recommendation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: RecommendationType = Field(..., description="verify_first, monitor, escalate_for_human_review")
    summary: str = Field(..., description="Recommendation explanation for human responders")
    next_steps: List[str] = Field(default_factory=list, description="Actionable next steps")
    requires_human_decision: Literal[True] = Field(
        True,
        description="Must always be true. Human responders retain full decision control."
    )


class Analysis(BaseModel):
    """The complete Analysis object produced by Member 3."""
    model_config = ConfigDict(extra="forbid")

    analyzed_at: str = Field(..., description="ISO 8601 UTC timestamp")
    engine_version: str = Field(..., description="Version of the AI engine, e.g. 0.1.0")
    duplicate: DuplicateInfo
    source_verification: SourceVerification
    freshness: FreshnessInfo
    conflicts: List[ConflictItem] = Field(default_factory=list)
    scores: Scores
    recommendation: Recommendation
