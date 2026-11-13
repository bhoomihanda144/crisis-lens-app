"""Allowed enumerations from CrisisLens API Contract v1.0.

Single source of truth: docs/api-contract.md
"""

from enum import Enum


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
    RECENT = "recent"  # age <= 60 min
    AGING = "aging"    # 61–240 min
    STALE = "stale"    # > 240 min


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


class Independence(str, Enum):
    INDEPENDENT = "independent"
    FORWARDED = "forwarded"
    UNKNOWN = "unknown"


class CorroborationStatus(str, Enum):
    CORROBORATED = "corroborated"
    SINGLE_SOURCE = "single_source"
    DISPUTED = "disputed"


class ScoreLevelUrgency(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ScoreLevelThree(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RecommendationType(str, Enum):
    VERIFY_FIRST = "verify_first"
    MONITOR = "monitor"
    ESCALATE_FOR_HUMAN_REVIEW = "escalate_for_human_review"


class VerifyAction(str, Enum):
    CONFIRM = "confirm"
    REJECT = "reject"
    REQUEST_MORE_INFO = "request_more_info"


class PrioritySort(str, Enum):
    URGENCY = "urgency"
    VERIFICATION = "verification"
