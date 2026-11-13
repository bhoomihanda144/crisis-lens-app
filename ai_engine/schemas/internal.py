"""Internal request and service schemas for CrisisLens AI Engine.

These schemas define the payload exchanged between Member 2 (Backend) and Member 3 (AI Engine).
"""

from typing import List, Optional, Any, Dict
from pydantic import BaseModel, ConfigDict, Field, model_validator

from ai_engine.schemas.enums import PrioritySort
from ai_engine.schemas.analysis import ConflictItem, Analysis
from ai_engine.schemas.incident import TimelineEntry
from ai_engine.schemas.simulation import SimulationRequest


class ReportInput(BaseModel):
    """Normalized report input schema.

    Accepts both flat format (Supabase database row sent by Member 2)
    and nested format (API Contract Report object).
    """
    model_config = ConfigDict(extra="ignore")

    id: str = Field(..., description="Report identifier, e.g. rpt_001")
    text: str = Field(..., min_length=1, description="Emergency report text")
    source_type: str = Field(default="citizen", description="citizen, social_media, news, official, sensor, responder")
    source_name: str = Field(default="Anonymous", description="Reporter name or handle")
    location_label: str = Field(default="Unknown", description="Human-readable location")
    lat: Optional[float] = Field(None, description="Latitude coordinate")
    lng: Optional[float] = Field(None, description="Longitude coordinate")
    reported_at: str = Field(..., description="ISO 8601 UTC timestamp")
    received_at: Optional[str] = Field(None, description="ISO 8601 UTC timestamp")
    forwarded_from: Optional[str] = Field(None, description="Parent report ID if forwarded")
    incident_id: Optional[str] = Field(None, description="Associated incident ID if linked")
    status: Optional[str] = Field(None, description="Report status")
    provenance: Optional[str] = Field(None, description="Verifiable source provenance or credentials if established")

    @model_validator(mode="before")
    @classmethod
    def normalize_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        normalized = dict(data)

        # Handle nested source: {"type": ..., "name": ...}
        if "source" in normalized and isinstance(normalized["source"], dict):
            src = normalized["source"]
            if "type" in src and "source_type" not in normalized:
                normalized["source_type"] = src["type"]
            if "name" in src and "source_name" not in normalized:
                normalized["source_name"] = src["name"]

        # Handle nested location: {"lat": ..., "lng": ..., "label": ...}
        if "location" in normalized and isinstance(normalized["location"], dict):
            loc = normalized["location"]
            if "label" in loc and "location_label" not in normalized:
                normalized["location_label"] = loc["label"]
            if "lat" in loc and "lat" not in normalized:
                normalized["lat"] = loc["lat"]
            if "lng" in loc and "lng" not in normalized:
                normalized["lng"] = loc["lng"]

        # Handle location_lat / location_lng aliases if present
        if "location_lat" in normalized and "lat" not in normalized:
            normalized["lat"] = normalized["location_lat"]
        if "location_lng" in normalized and "lng" not in normalized:
            normalized["lng"] = normalized["location_lng"]

        return normalized


class AnalyzeRequest(BaseModel):
    """Payload sent by Member 2 to POST /analyze."""
    model_config = ConfigDict(extra="ignore")

    report: ReportInput = Field(..., description="Target report to analyze")
    context_reports: List[ReportInput] = Field(
        default_factory=list,
        description="List of existing candidate reports to compare against"
    )


class GenerateGraphRequest(BaseModel):
    """Payload sent by Member 2 to generate an incident evidence relationship graph."""
    model_config = ConfigDict(extra="ignore")

    incident_id: str = Field(..., description="Incident ID, e.g. inc_001")
    reports: List[ReportInput] = Field(
        default_factory=list,
        description="List of reports associated with the incident",
    )
    conflicts: Optional[List[ConflictItem]] = Field(
        default_factory=list,
        description="Explicitly identified conflicts for relationship generation",
    )


class IncidentInput(BaseModel):
    """Normalized incident input schema for priority ranking.

    Accepts both flat format (Supabase database row sent by Member 2)
    and nested format (API Contract Incident object).
    """
    model_config = ConfigDict(extra="ignore")

    id: str = Field(..., description="Incident ID, e.g. inc_001")
    title: str = Field(..., min_length=1, description="Incident title")
    type: str = Field(default="other", description="flood, fire, earthquake, landslide, structural, medical, other")
    severity: str = Field(default="medium", description="low, medium, high, critical")
    status: str = Field(default="active", description="active, monitoring, resolved")
    location_label: str = Field(default="Unknown", description="Human-readable location")
    lat: float = Field(default=0.0, description="Latitude coordinate")
    lng: float = Field(default=0.0, description="Longitude coordinate")
    report_count: Optional[int] = Field(None, description="Total reports associated")
    independent_source_count: Optional[int] = Field(None, description="Independent sources count")
    first_reported_at: Optional[str] = Field(None, description="ISO 8601 UTC timestamp")
    last_updated_at: Optional[str] = Field(None, description="ISO 8601 UTC timestamp")
    timeline: List[TimelineEntry] = Field(default_factory=list, description="Incident evolution timeline")
    reports: Optional[List[ReportInput]] = Field(default_factory=list, description="Associated reports if provided")
    report_analyses: Optional[List[Analysis]] = Field(default_factory=list, description="Pre-computed analyses if provided")
    conflicts: Optional[List[ConflictItem]] = Field(default_factory=list, description="Explicit conflicts if provided")

    @model_validator(mode="before")
    @classmethod
    def normalize_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        normalized = dict(data)

        # Handle nested location: {"lat": ..., "lng": ..., "label": ...}
        if "location" in normalized:
            loc = normalized["location"]
            if isinstance(loc, dict):
                if "label" in loc and "location_label" not in normalized:
                    normalized["location_label"] = loc["label"]
                if "lat" in loc and "lat" not in normalized:
                    normalized["lat"] = loc["lat"]
                if "lng" in loc and "lng" not in normalized:
                    normalized["lng"] = loc["lng"]
            elif isinstance(loc, str) and "location_label" not in normalized:
                normalized["location_label"] = loc

        if "location_lat" in normalized and "lat" not in normalized:
            normalized["lat"] = normalized["location_lat"]
        if "location_lng" in normalized and "lng" not in normalized:
            normalized["lng"] = normalized["location_lng"]

        if "report_count" not in normalized or normalized["report_count"] is None:
            reps = normalized.get("reports") or []
            normalized["report_count"] = len(reps)

        if "independent_source_count" not in normalized or normalized["independent_source_count"] is None:
            normalized["independent_source_count"] = 0

        return normalized


class PriorityRankRequest(BaseModel):
    """Payload sent by Member 2 to rank an incident batch."""
    model_config = ConfigDict(extra="ignore")

    sort: PrioritySort = Field(
        default=PrioritySort.URGENCY,
        description="Ranking sort mode: 'urgency' (default) or 'verification'"
    )
    incidents: List[IncidentInput] = Field(
        default_factory=list,
        description="List of incidents to prioritize",
    )


class SimulationScenarioRequest(BaseModel):
    """Internal simulation request payload supporting optional incident context and access impact."""
    model_config = ConfigDict(extra="ignore")

    scenario_name: str = Field(..., min_length=1, description="Descriptive scenario name")
    affected_population: int = Field(..., ge=0, description="Estimated affected population")
    disaster_severity: int = Field(..., ge=1, le=5, description="Severity integer from 1 to 5")
    rescue_teams: int = Field(..., ge=0, description="Available rescue teams")
    blocked_roads: int = Field(..., ge=0, description="Number of blocked arterial roads")
    available_ambulances: int = Field(..., ge=0, description="Available emergency ambulances")

    # Optional internal integration fields
    incidents: Optional[List[IncidentInput]] = Field(
        default_factory=list,
        description="Optional active incident context for hypothetical priority re-ranking",
    )
    blocked_access_incident_ids: Optional[List[str]] = Field(
        default_factory=list,
        description="Explicit incident IDs where arterial access routes are blocked",
    )

    def to_public_request(self) -> SimulationRequest:
        """Converts to the strict public SimulationRequest schema."""
        return SimulationRequest(
            scenario_name=self.scenario_name,
            affected_population=self.affected_population,
            disaster_severity=self.disaster_severity,
            rescue_teams=self.rescue_teams,
            blocked_roads=self.blocked_roads,
            available_ambulances=self.available_ambulances,
        )
