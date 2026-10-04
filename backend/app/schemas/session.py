import uuid
from datetime import datetime
from typing import Any, List, Literal, Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator

SessionMode = Literal["mock_interview", "drill", "freeform", "debrief"]
InterviewType = Literal["behavioral", "technical", "system_design", "mixed", "screening"]
Difficulty = Literal["warmup", "standard", "senior", "stress"]


class SessionCreate(BaseModel):
    # Desktop client sends `target_job_id`.
    job_id: Optional[uuid.UUID] = Field(None, validation_alias=AliasChoices("job_id", "target_job_id"))
    focus_area: Optional[str] = Field(None, max_length=200)
    mode: SessionMode = "mock_interview"
    interview_type: InterviewType = "technical"
    difficulty: Difficulty = "standard"
    language: Optional[str] = Field(None, max_length=20)

    model_config = ConfigDict(extra="ignore", populate_by_name=True)


class SessionResponse(BaseModel):
    id: uuid.UUID
    # Same value as `id`; the desktop client reads `session_id`.
    session_id: uuid.UUID
    candidate_id: uuid.UUID
    job_id: Optional[uuid.UUID] = None
    status: str
    focus_area: Optional[str] = None
    mode: Optional[str] = None
    interview_type: Optional[str] = None
    difficulty: Optional[str] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    duration_s: Optional[int] = None
    turn_count: Optional[int] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def _fill_session_id(cls, data: Any) -> Any:
        if not isinstance(data, dict) and hasattr(data, "__table__"):
            data = {c.key: getattr(data, c.key) for c in data.__mapper__.column_attrs}
        if isinstance(data, dict):
            data = dict(data)
            data.setdefault("session_id", data.get("id"))
            data["status"] = data.get("status") or "pending"
        return data


class SessionTurnResponse(BaseModel):
    id: uuid.UUID
    turn_index: int
    speaker: Optional[str] = None
    text: Optional[str] = None
    parent_turn_id: Optional[uuid.UUID] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class SessionDebriefResponse(BaseModel):
    """`status` is "pending" until the debrief job has produced a row."""

    status: Literal["ready", "pending"]
    id: Optional[uuid.UUID] = None
    session_id: uuid.UUID
    headline_metrics: Optional[Any] = None
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    flagged_claims: Optional[Any] = None
    jd_coverage: Optional[Any] = None
    generated_at: Optional[datetime] = None


class SessionEndResponse(BaseModel):
    id: uuid.UUID
    status: str
    debrief_status: str
