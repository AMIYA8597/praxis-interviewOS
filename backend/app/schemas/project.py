from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import datetime
import uuid

class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    summary: str = Field(..., min_length=1)
    business_value: Optional[str] = None
    tech_stack: List[str] = Field(default_factory=list)

class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    summary: Optional[str] = Field(None, min_length=1)
    business_value: Optional[str] = None
    tech_stack: Optional[List[str]] = None

class ProjectResponse(BaseModel):
    id: uuid.UUID
    candidate_id: uuid.UUID
    name: str
    summary: str
    business_value: Optional[str]
    tech_stack: List[str]
    verified_by_user: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
