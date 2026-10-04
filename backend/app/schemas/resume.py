import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ResumeUploadResponse(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    status: str
    processing_status: str
    message: str


class ResumeResponse(BaseModel):
    id: uuid.UUID
    candidate_id: uuid.UUID
    document_id: uuid.UUID
    filename: Optional[str] = None
    mime_type: Optional[str] = None
    size_bytes: Optional[int] = None
    is_primary: bool = False
    processing_status: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime


class ResumeStatusResponse(BaseModel):
    id: uuid.UUID
    processing_status: Optional[str] = None
    error_message: Optional[str] = None


class ResumeFactResponse(BaseModel):
    """A claim extracted from the resume (resume_claims row)."""

    id: uuid.UUID
    fact_type: Optional[str] = None
    content: str
    verified_by_user: bool
    verified_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_claim(cls, claim) -> "ResumeFactResponse":
        return cls(
            id=claim.id,
            fact_type=claim.claim_type,
            content=claim.claim_text,
            verified_by_user=bool(claim.verified_by_user),
            verified_at=claim.verified_at,
        )


class ResumeFactUpdate(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)
