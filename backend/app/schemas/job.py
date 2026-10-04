import uuid
from datetime import datetime
from typing import Any, List, Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator


class JobCreate(BaseModel):
    company: str = Field(..., min_length=1, max_length=200, validation_alias=AliasChoices("company", "company_name"))
    role_title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(
        ..., min_length=10, max_length=50_000, validation_alias=AliasChoices("description", "raw_jd_text")
    )


class JobResponse(BaseModel):
    id: uuid.UUID
    candidate_id: uuid.UUID
    company: str
    role_title: str
    processing_status: str
    error_message: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def _map_columns(cls, data: Any) -> Any:
        if not isinstance(data, dict) and hasattr(data, "company_name"):
            return {
                "id": data.id,
                "candidate_id": data.candidate_id,
                "company": data.company_name,
                "role_title": data.role_title,
                "processing_status": data.processing_status or "pending",
                "error_message": data.error_message,
                "created_at": data.created_at,
            }
        return data


class JobRequirementResponse(BaseModel):
    id: uuid.UUID
    skill_text: str
    category: Optional[str] = None
    priority: Optional[str] = None
    evidence_quote: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class JobBlueprintResponse(BaseModel):
    id: uuid.UUID
    summary: Optional[str] = None
    top_skills: Optional[Any] = None
    likely_topics: List[str] = Field(default_factory=list)
    prep_pack: Optional[Any] = None
    requirements: List[JobRequirementResponse] = Field(default_factory=list)


class JobMatchResponse(BaseModel):
    id: uuid.UUID
    overall_score: Optional[float] = None
    methodology_version: Optional[str] = None
    breakdown: Optional[Any] = None


class JobDetailResponse(JobResponse):
    raw_jd_text: Optional[str] = None
    blueprints: List[JobBlueprintResponse] = Field(default_factory=list)
    matches: List[JobMatchResponse] = Field(default_factory=list)


class JobAcceptedResponse(BaseModel):
    id: uuid.UUID
    status: str
    message: str
