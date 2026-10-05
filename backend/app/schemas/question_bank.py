import uuid
from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

DomainCategory = Literal["TECHNICAL", "BEHAVIORAL", "SPECIALIZED"]
QuestionDifficulty = Literal["easy", "medium", "hard", "expert"]
QuestionSource = Literal["human", "ai_generated"]
QualityStatus = Literal["draft", "approved", "deprecated"]


class InterviewDomainResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    parent_code: Optional[str] = None
    category: DomainCategory
    label: str
    description: Optional[str] = None
    sort_order: int


class QuestionBankResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    domain_code: str
    subcategory: Optional[str] = None
    difficulty: QuestionDifficulty
    title: str
    body: str
    expected_concepts: Optional[List[str]] = None
    rubric: Optional[str] = None
    role_tags: Optional[List[str]] = None
    source: QuestionSource
    quality_status: QualityStatus
    created_at: datetime


class QuestionBankCreate(BaseModel):
    domain_code: str = Field(..., max_length=50)
    subcategory: Optional[str] = Field(None, max_length=100)
    difficulty: QuestionDifficulty
    title: str = Field(..., min_length=5, max_length=300)
    body: str = Field(..., min_length=10)
    expected_concepts: Optional[List[str]] = None
    rubric: Optional[str] = None
    role_tags: Optional[List[str]] = None
    source: QuestionSource = "human"


class ReadinessResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    candidate_id: uuid.UUID
    job_id: Optional[uuid.UUID] = None
    computed_at: datetime
    overall_score: Optional[float] = None
    confidence: Optional[Literal["low", "medium", "high"]] = None
    technical_score: Optional[float] = None
    system_design_score: Optional[float] = None
    behavioral_score: Optional[float] = None
    communication_score: Optional[float] = None
    grounding_score: Optional[float] = None
    jd_coverage_score: Optional[float] = None
    weakest_domain: Optional[str] = None
    recommended_action: Optional[str] = None
    component_detail: Optional[dict] = None


class PreparationPlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    candidate_id: uuid.UUID
    job_id: Optional[uuid.UUID] = None
    generated_at: datetime
    plan_sessions: List[dict]
    is_active: bool
    completed_count: int
