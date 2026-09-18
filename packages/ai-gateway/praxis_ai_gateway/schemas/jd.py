from pydantic import BaseModel, Field
from typing import List, Optional

class JobRequirement(BaseModel):
    skill_text: str = Field(..., description="The specific requirement or skill")
    category: str = Field(..., description="Category of the requirement (e.g., 'technical', 'behavioral', 'domain')")
    priority: str = Field(..., description="'required' or 'preferred'")
    evidence_quote: str = Field(..., description="The literal JD sentence supporting this requirement")

class LikelyTopic(BaseModel):
    topic: str = Field(..., description="Inferred interview topic")
    rationale: str = Field(..., description="Rationale for why this topic is likely to be interviewed based on JD language")

class ExtractedJobBlueprint(BaseModel):
    company: Optional[str] = None
    role: Optional[str] = None
    seniority_signal: Optional[str] = Field(None, description="Inferred seniority level (e.g., 'Junior', 'Senior', 'Staff')")
    job_requirements: List[JobRequirement] = []
    likely_topics: List[LikelyTopic] = []
