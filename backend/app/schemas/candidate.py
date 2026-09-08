from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import datetime
import uuid

class CandidateResponse(BaseModel):
    id: uuid.UUID
    profile_id: uuid.UUID
    full_name: str
    headline: Optional[str]
    target_roles: List[str]
    preferred_language: str
    speaking_style: str
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class CandidateUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    headline: Optional[str] = Field(None, max_length=200)
    target_roles: Optional[List[str]] = None
    preferred_language: Optional[str] = Field(None, max_length=50)
    speaking_style: Optional[str] = Field(None, max_length=50)
