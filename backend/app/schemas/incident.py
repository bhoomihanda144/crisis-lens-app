"""
CrisisLens Incident Schemas
Strictly conforms to API Contract v1.0 Section 3 (Incident) and Section 4.4, 4.5.
"""
from typing import List, Optional
from pydantic import BaseModel, Field
from app.schemas.common import LocationSchema, IncidentType, IncidentSeverity, IncidentStatus


class TimelineEntry(BaseModel):
    timestamp: str
    severity: IncidentSeverity
    status: IncidentStatus
    report_count: int = Field(..., ge=0)
    affected_radius_m: int = Field(..., ge=0)
    summary: str


class IncidentResponse(BaseModel):
    id: str = Field(..., description="Semantic incident ID, e.g. inc_001")
    title: str
    type: IncidentType
    location: LocationSchema
    severity: IncidentSeverity
    status: IncidentStatus
    report_ids: List[str] = Field(default_factory=list)
    report_count: int = Field(..., ge=0)
    independent_source_count: int = Field(..., ge=0)
    first_reported_at: str
    last_updated_at: str
    timeline: List[TimelineEntry] = Field(default_factory=list)


class IncidentListResponse(BaseModel):
    items: List[IncidentResponse]
    total: int = Field(..., ge=0)
