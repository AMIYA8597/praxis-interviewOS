import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class StudyItemCreate(BaseModel):
    topic: str = Field(..., min_length=1, max_length=255)
    prompt: str = Field(..., min_length=1, max_length=10_000)
    reference_answer: Optional[str] = Field(None, max_length=20_000)
    difficulty: Optional[str] = Field(None, max_length=50)


class StudyItemResponse(BaseModel):
    id: uuid.UUID
    topic: str
    source: Optional[str] = None
    prompt: str
    reference_answer: Optional[str] = None
    difficulty: Optional[str] = None
    ease_factor: Optional[float] = None
    interval_days: Optional[int] = None
    repetitions: Optional[int] = None
    next_review_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReviewItemRequest(BaseModel):
    quality: int = Field(..., ge=0, le=5, description="SM-2 recall quality 0..5")


class ReviewItemResponse(BaseModel):
    status: str
    id: uuid.UUID
    interval_days: int
    repetitions: int
    ease_factor: float
    next_review_at: datetime


class GenerateMaterialRequest(BaseModel):
    topic: str = Field(..., min_length=1, max_length=255)
    difficulty: str = Field("standard", max_length=50)


class SolveScreenshotRequest(BaseModel):
    image_base64: str = Field(..., min_length=1)
    screenshot_task_id: str = Field(..., min_length=1, max_length=100)


class QueuedTaskResponse(BaseModel):
    status: str
    task_id: str
