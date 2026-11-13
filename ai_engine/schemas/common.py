"""Common shared schemas for CrisisLens API Contract v1.0.

Single source of truth: docs/api-contract.md
"""

from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

from ai_engine.schemas.enums import (
    ScoreLevelUrgency,
    ScoreLevelThree,
)


class Location(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lat: float = Field(..., description="Latitude coordinate", ge=-90.0, le=90.0)
    lng: float = Field(..., description="Longitude coordinate", ge=-180.0, le=180.0)
    label: str = Field(..., min_length=1, description="Human readable location name")


class UrgencyScore(BaseModel):
    model_config = ConfigDict(extra="forbid")

    score: int = Field(..., ge=0, le=100, description="Score integer from 0 to 100")
    level: ScoreLevelUrgency = Field(..., description="Urgency level: low, medium, high, or critical")
    reasons: List[str] = Field(default_factory=list, description="List of reasons for this score")


class EvidenceConfidenceScore(BaseModel):
    model_config = ConfigDict(extra="forbid")

    score: int = Field(..., ge=0, le=100, description="Score integer from 0 to 100")
    level: ScoreLevelThree = Field(..., description="Confidence level: low, medium, or high")
    reasons: List[str] = Field(default_factory=list, description="List of reasons for this score")


class VerificationPriorityScore(BaseModel):
    model_config = ConfigDict(extra="forbid")

    score: int = Field(..., ge=0, le=100, description="Score integer from 0 to 100")
    level: ScoreLevelThree = Field(..., description="Priority level: low, medium, or high")
    reasons: List[str] = Field(default_factory=list, description="List of reasons for this score")


class Scores(BaseModel):
    """The three separate scores produced by Member 3.

    Rule: The three scores are separate on purpose. There is no combined score anywhere in this API.
    """
    model_config = ConfigDict(extra="forbid")

    urgency: UrgencyScore
    evidence_confidence: EvidenceConfidenceScore
    verification_priority: VerificationPriorityScore


class APIErrorDetails(BaseModel):
    code: str
    message: str
    details: Optional[dict] = None


class APIErrorResponse(BaseModel):
    error: APIErrorDetails
