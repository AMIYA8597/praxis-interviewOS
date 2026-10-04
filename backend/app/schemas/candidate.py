import uuid
from datetime import datetime
from typing import Any, List, Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class CandidateResponse(BaseModel):
    id: uuid.UUID
    profile_id: uuid.UUID
    full_name: str
    headline: Optional[str] = None
    location: Optional[str] = None
    years_experience: Optional[float] = None
    target_roles: List[str] = Field(default_factory=list)
    preferred_language: Optional[str] = None
    # jsonb in the DB: may be a string label or a structured object.
    speaking_style: Optional[Any] = None
    onboarding_step: Optional[str] = None
    onboarding_completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CandidateUpdate(BaseModel):
    """PATCH / PUT body. `name` is accepted as an alias of `full_name` (web onboarding sends it)."""

    full_name: Optional[str] = Field(
        None, min_length=2, max_length=100, validation_alias=AliasChoices("full_name", "name")
    )
    headline: Optional[str] = Field(None, max_length=200)
    location: Optional[str] = Field(None, max_length=200)
    years_experience: Optional[float] = Field(None, ge=0, le=80)
    target_roles: Optional[List[str]] = Field(None, max_length=20)
    preferred_language: Optional[str] = Field(None, max_length=50)
    speaking_style: Optional[Any] = None
    onboarding_step: Optional[str] = Field(None, max_length=50)

    # Unknown keys (e.g. onboarding's `summary`) are ignored rather than 422.
    model_config = ConfigDict(extra="ignore", populate_by_name=True)
