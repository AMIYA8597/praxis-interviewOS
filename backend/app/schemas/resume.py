from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime
import uuid

class ResumeResponse(BaseModel):
    id: uuid.UUID
    candidate_id: uuid.UUID
    document_id: uuid.UUID
    filename: str
    is_active: bool
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class ResumeFactResponse(BaseModel):
    id: uuid.UUID
    fact_type: str
    content: str
    verified_by_user: bool
    
    model_config = ConfigDict(from_attributes=True)

class ResumeFactUpdate(BaseModel):
    content: str = Field(..., min_length=1)
