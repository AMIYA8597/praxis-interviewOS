from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime
import uuid

class SessionCreate(BaseModel):
    job_id: Optional[uuid.UUID] = None
    focus_area: Optional[str] = None

class SessionResponse(BaseModel):
    id: uuid.UUID
    candidate_id: uuid.UUID
    job_id: Optional[uuid.UUID]
    status: str
    focus_area: Optional[str]
    started_at: Optional[datetime]
    ended_at: Optional[datetime]
    
    model_config = ConfigDict(from_attributes=True)
