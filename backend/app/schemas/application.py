import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ApplicationCreate(BaseModel):
    company: str = Field(..., min_length=1, max_length=200)
    role: str = Field(..., min_length=1, max_length=200)
    job_id: Optional[uuid.UUID] = None
    source: Optional[str] = Field(None, max_length=200)
    status: str = Field("applied", max_length=50)
    recruiter: Optional[str] = Field(None, max_length=200)
    interview_round: Optional[str] = Field(None, max_length=100)
    next_action: Optional[str] = Field(None, max_length=500)
    notes: Optional[str] = Field(None, max_length=10_000)


class ApplicationUpdate(BaseModel):
    company: Optional[str] = Field(None, min_length=1, max_length=200)
    role: Optional[str] = Field(None, min_length=1, max_length=200)
    source: Optional[str] = Field(None, max_length=200)
    status: Optional[str] = Field(None, max_length=50)
    recruiter: Optional[str] = Field(None, max_length=200)
    interview_round: Optional[str] = Field(None, max_length=100)
    next_action: Optional[str] = Field(None, max_length=500)
    notes: Optional[str] = Field(None, max_length=10_000)


class ApplicationResponse(BaseModel):
    id: uuid.UUID
    job_id: Optional[uuid.UUID] = None
    company: Optional[str] = None
    role: Optional[str] = None
    source: Optional[str] = None
    status: Optional[str] = None
    recruiter: Optional[str] = None
    interview_round: Optional[str] = None
    next_action: Optional[str] = None
    notes: Optional[str] = None
    applied_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OutreachDraftRequest(BaseModel):
    company: str = Field(..., min_length=1, max_length=200)
    detail: str = Field(..., min_length=1, max_length=2000)
    # When provided the draft is persisted against this (owned) application.
    application_id: Optional[uuid.UUID] = None
    recipient_name: Optional[str] = Field(None, max_length=200)


class OutreachDraftResponse(BaseModel):
    id: uuid.UUID
    application_id: uuid.UUID
    recipient_name: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OutreachGenerateResponse(BaseModel):
    status: str
    draft: str
    saved_draft_id: Optional[uuid.UUID] = None
