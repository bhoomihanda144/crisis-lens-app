"""
CrisisLens Common Schemas & Enums
Strictly aligns with CrisisLens API Contract v1.0 Section 2 & 3.
"""
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class SourceType(str, Enum):
    CITIZEN = "citizen"
    SOCIAL_MEDIA = "social_media"
    NEWS = "news"
    OFFICIAL = "official"
    SENSOR = "sensor"
    RESPONDER = "responder"


class ReportStatus(str, Enum):
    PENDING_ANALYSIS = "pending_analysis"
    ANALYZED = "analyzed"
    VERIFIED = "verified"
    REJECTED = "rejected"
    NEEDS_MORE_INFO = "needs_more_info"


class FreshnessStatus(str, Enum):
    RECENT = "recent"
    AGING = "aging"
    STALE = "stale"


class IncidentType(str, Enum):
    FLOOD = "flood"
    FIRE = "fire"
    EARTHQUAKE = "earthquake"
    LANDSLIDE = "landslide"
    STRUCTURAL = "structural"
    MEDICAL = "medical"
    OTHER = "other"


class IncidentSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IncidentStatus(str, Enum):
    ACTIVE = "active"
    MONITORING = "monitoring"
    RESOLVED = "resolved"


class RelationshipType(str, Enum):
    ORIGINAL = "original"
    DUPLICATE = "duplicate"
    FORWARDED = "forwarded"
    CORROBORATING = "corroborating"
    CONFLICTING = "conflicting"


class IndependenceType(str, Enum):
    INDEPENDENT = "independent"
    FORWARDED = "forwarded"
    UNKNOWN = "unknown"


class CorroborationStatus(str, Enum):
    CORROBORATED = "corroborated"
    SINGLE_SOURCE = "single_source"
    DISPUTED = "disputed"


class RecommendationType(str, Enum):
    VERIFY_FIRST = "verify_first"
    MONITOR = "monitor"
    ESCALATE_FOR_HUMAN_REVIEW = "escalate_for_human_review"


class VerificationAction(str, Enum):
    CONFIRM = "confirm"
    REJECT = "reject"
    REQUEST_MORE_INFO = "request_more_info"


class LocationSchema(BaseModel):
    lat: float = Field(..., description="Latitude coordinate", ge=-90.0, le=90.0)
    lng: float = Field(..., description="Longitude coordinate", ge=-180.0, le=180.0)
    label: str = Field(..., min_length=1, description="Human-readable location label")


class SourceSchema(BaseModel):
    type: SourceType = Field(..., description="Source category")
    name: str = Field(..., min_length=1, description="Name or handle of reporter")


class FreshnessSchema(BaseModel):
    status: FreshnessStatus
    age_minutes: int = Field(..., ge=0)
    last_updated: str


class ScoreDetail(BaseModel):
    score: int = Field(..., ge=0, le=100)
    level: str
    reasons: List[str] = Field(default_factory=list)
