"""
CrisisLens Verification Schemas
Strictly conforms to API Contract v1.0 Section 4.10.
"""
from typing import Optional
from pydantic import BaseModel, Field
from app.schemas.common import VerificationAction


class VerificationRequest(BaseModel):
    action: VerificationAction = Field(..., description="Action: 'confirm', 'reject', or 'request_more_info'")
    note: Optional[str] = Field(None, description="Duty officer review note or rationale")
    verified_by: Optional[str] = Field(None, description="Name or title of reviewing officer")
