"""
CrisisLens Report Schemas
Strictly conforms to API Contract v1.0 Section 3 (Report) and Section 4.1, 4.2, 4.3.
"""
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field
from app.schemas.common import LocationSchema, SourceSchema, ReportStatus, VerificationAction


class ReportCreate(BaseModel):
    text: str = Field(..., min_length=1, description="Content of the emergency report")
    source: SourceSchema = Field(..., description="Report source metadata")
    location: LocationSchema = Field(..., description="Geographical location of report")
    reported_at: Optional[str] = Field(None, description="ISO 8601 UTC timestamp of original occurrence")
    forwarded_from: Optional[str] = Field(None, description="Report ID this report was forwarded from")


class VerificationInfo(BaseModel):
    action: VerificationAction
    note: Optional[str] = None
    verified_by: Optional[str] = None
    verified_at: str


class ReportResponse(BaseModel):
    id: str = Field(..., description="Semantic report ID, e.g. rpt_001")
    text: str
    source: SourceSchema
    location: LocationSchema
    reported_at: str
    received_at: str
    status: ReportStatus
    incident_id: Optional[str] = None
    forwarded_from: Optional[str] = None
    analysis: Optional[Dict[str, Any]] = None
    verification: Optional[VerificationInfo] = None


class ReportListResponse(BaseModel):
    items: List[ReportResponse]
    total: int = Field(..., ge=0)
    limit: int = Field(..., ge=1)
    offset: int = Field(..., ge=0)
