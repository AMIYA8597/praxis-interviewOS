from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime
import uuid

class JobCreate(BaseModel):
    company: str = Field(..., min_length=1, max_length=100)
    role_title: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=10)

class JobResponse(BaseModel):
    id: uuid.UUID
    candidate_id: uuid.UUID
    company: str
    role_title: str
    processing_status: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
