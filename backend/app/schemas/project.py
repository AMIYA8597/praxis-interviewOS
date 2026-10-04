import uuid
from datetime import datetime
from typing import Any, List, Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator

class _ProjectFields(BaseModel):
    problem: Optional[str] = None
    motivation: Optional[str] = None
    users_served: Optional[str] = None
    architecture: Optional[str] = None
    datasets: Optional[str] = None
    data_pipeline: Optional[str] = None
    models_used: Optional[List[str]] = None
    training_approach: Optional[str] = None
    evaluation_method: Optional[str] = None
    metrics: Optional[Any] = None
    deployment: Optional[str] = None
    infra: Optional[str] = None
    challenges: Optional[str] = None
    failure_cases: Optional[str] = None
    tradeoffs: Optional[str] = None
    improvements: Optional[str] = None
    personal_contribution: Optional[str] = None
    team_size: Optional[int] = Field(None, ge=1, le=10000)
    duration_months: Optional[int] = Field(None, ge=0, le=600)
    github_url: Optional[str] = Field(None, max_length=500)
    demo_url: Optional[str] = Field(None, max_length=500)


class ProjectCreate(_ProjectFields):
    name: str = Field(..., min_length=1, max_length=100)
    summary: str = Field(..., min_length=1)
    # Stored in candidate_projects.business_impact; `business_value` kept for API compatibility.
    business_value: Optional[str] = Field(None, validation_alias=AliasChoices("business_value", "business_impact"))
    tech_stack: List[str] = Field(default_factory=list)


class ProjectUpdate(_ProjectFields):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    summary: Optional[str] = Field(None, min_length=1)
    business_value: Optional[str] = Field(None, validation_alias=AliasChoices("business_value", "business_impact"))
    tech_stack: Optional[List[str]] = None
    verified_by_user: Optional[bool] = None


class ProjectResponse(_ProjectFields):
    id: uuid.UUID
    candidate_id: uuid.UUID
    name: str
    summary: Optional[str] = None
    business_value: Optional[str] = None
    tech_stack: List[str] = Field(default_factory=list)
    verified_by_user: bool
    confidence: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def _map_columns(cls, data: Any) -> Any:
        if not isinstance(data, dict) and hasattr(data, "__mapper__"):
            data = {attr.key: getattr(data, attr.key) for attr in data.__mapper__.column_attrs}
        if isinstance(data, dict):
            data = dict(data)
            if "business_value" not in data:
                data["business_value"] = data.get("business_impact")
            if data.get("tech_stack") is None:
                data["tech_stack"] = []
        return data
