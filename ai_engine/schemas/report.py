"""Report schemas for CrisisLens API Contract v1.0.

Single source of truth: docs/api-contract.md (Section 3 & 4.1)
"""

from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field

from ai_engine.schemas.enums import SourceType, ReportStatus, VerifyAction
from ai_engine.schemas.common import Location
from ai_engine.schemas.analysis import Analysis


class ReportSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: SourceType = Field(..., description="citizen, social_media, news, official, sensor, responder")
    name: str = Field(..., min_length=1, description="Name or identifier of source")


class VerificationRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: VerifyAction = Field(..., description="confirm, reject, request_more_info")
    note: Optional[str] = Field(None, description="Human notes regarding action")
    verified_by: Optional[str] = Field(None, description="Identity of verifier / duty officer")
    verified_at: str = Field(..., description="ISO 8601 UTC timestamp")


class Report(BaseModel):
    """Complete Report object representation."""
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="Report ID, e.g. rpt_001")
    text: str = Field(..., min_length=1, description="Content of the emergency report")
    source: ReportSource
    location: Location
    reported_at: str = Field(..., description="ISO 8601 UTC timestamp")
    received_at: str = Field(..., description="ISO 8601 UTC timestamp")
    status: ReportStatus
    incident_id: Optional[str] = Field(None, description="Associated incident ID")
    forwarded_from: Optional[str] = Field(None, description="Parent report ID if forwarded")
    analysis: Optional[Analysis] = Field(None, description="Analysis object if analyzed, otherwise null")
    verification: Optional[VerificationRecord] = Field(None, description="Human verification record if acted upon")


class ReportCreate(BaseModel):
    """Request payload for POST /reports."""
    model_config = ConfigDict(extra="forbid")

    text: str = Field(..., min_length=1)
    source: ReportSource
    location: Location
    reported_at: Optional[str] = None
    forwarded_from: Optional[str] = None


class ReportListResponse(BaseModel):
    """Response payload for GET /reports."""
    model_config = ConfigDict(extra="forbid")

    items: List[Report]
    total: int
    limit: int
    offset: int
