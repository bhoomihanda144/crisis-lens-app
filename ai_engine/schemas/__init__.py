"""Schemas module exporting all contract-compliant Pydantic models."""

from ai_engine.schemas.enums import (
    SourceType,
    ReportStatus,
    FreshnessStatus,
    IncidentType,
    IncidentSeverity,
    IncidentStatus,
    RelationshipType,
    Independence,
    CorroborationStatus,
    ScoreLevelUrgency,
    ScoreLevelThree,
    RecommendationType,
    VerifyAction,
    PrioritySort,
)
from ai_engine.schemas.common import (
    Location,
    UrgencyScore,
    EvidenceConfidenceScore,
    VerificationPriorityScore,
    Scores,
    APIErrorDetails,
    APIErrorResponse,
)
from ai_engine.schemas.analysis import (
    DuplicateMatch,
    DuplicateInfo,
    RelatedReport,
    SourceVerification,
    FreshnessInfo,
    ConflictStatement,
    ConflictItem,
    Recommendation,
    Analysis,
)
from ai_engine.schemas.report import (
    ReportSource,
    VerificationRecord,
    Report,
    ReportCreate,
    ReportListResponse,
)
from ai_engine.schemas.incident import (
    TimelineEntry,
    Incident,
    HumanDecision,
    PriorityItem,
    PriorityResponse,
)
from ai_engine.schemas.graph import (
    EvidenceNode,
    EvidenceEdge,
    EvidenceGraphResponse,
)
from ai_engine.schemas.simulation import (
    SimulationRequest,
    ResourceDemand,
    ResourceShortage,
    PriorityChange,
    SimulationResults,
    SimulationResponse,
)
from ai_engine.schemas.internal import (
    ReportInput,
    AnalyzeRequest,
    GenerateGraphRequest,
    IncidentInput,
    PriorityRankRequest,
    SimulationScenarioRequest,
)

__all__ = [
    # Enums
    "SourceType",
    "ReportStatus",
    "FreshnessStatus",
    "IncidentType",
    "IncidentSeverity",
    "IncidentStatus",
    "RelationshipType",
    "Independence",
    "CorroborationStatus",
    "ScoreLevelUrgency",
    "ScoreLevelThree",
    "RecommendationType",
    "VerifyAction",
    "PrioritySort",
    # Common
    "Location",
    "UrgencyScore",
    "EvidenceConfidenceScore",
    "VerificationPriorityScore",
    "Scores",
    "APIErrorDetails",
    "APIErrorResponse",
    # Analysis
    "DuplicateMatch",
    "DuplicateInfo",
    "RelatedReport",
    "SourceVerification",
    "FreshnessInfo",
    "ConflictStatement",
    "ConflictItem",
    "Recommendation",
    "Analysis",
    # Report
    "ReportSource",
    "VerificationRecord",
    "Report",
    "ReportCreate",
    "ReportListResponse",
    # Incident
    "TimelineEntry",
    "Incident",
    "HumanDecision",
    "PriorityItem",
    "PriorityResponse",
    # Graph
    "EvidenceNode",
    "EvidenceEdge",
    "EvidenceGraphResponse",
    # Simulation
    "SimulationRequest",
    "ResourceDemand",
    "ResourceShortage",
    "PriorityChange",
    "SimulationResults",
    "SimulationResponse",
    # Internal
    "ReportInput",
    "AnalyzeRequest",
    "GenerateGraphRequest",
    "IncidentInput",
    "PriorityRankRequest",
    "SimulationScenarioRequest",
]
