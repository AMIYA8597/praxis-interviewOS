from pydantic import BaseModel, Field
from typing import List, Optional

class CandidateSkill(BaseModel):
    name: str = Field(..., description="The exact name of the skill")
    proficiency: str = Field(..., description="Inferred proficiency level based on text (e.g., 'Beginner', 'Intermediate', 'Expert'). If unclear, default to 'Intermediate'")
    extraction_confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score from 0.0 to 1.0 that this skill is genuinely possessed by the candidate")

class CandidateProject(BaseModel):
    title: str = Field(..., description="Title of the project")
    role: str = Field("Unknown", description="Candidate's role on the project")
    summary: str = Field(..., description="Summary of what the project was and what was accomplished")
    extraction_confidence: float = Field(..., ge=0.0, le=1.0)

class CandidateExperience(BaseModel):
    company: str
    title: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    description: str = Field(..., description="Summary of responsibilities and achievements")
    extraction_confidence: float = Field(..., ge=0.0, le=1.0)

class CandidateEducation(BaseModel):
    institution: str
    degree: Optional[str] = None
    field_of_study: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    extraction_confidence: float = Field(..., ge=0.0, le=1.0)

class ExtractedResumeProfile(BaseModel):
    skills: List[CandidateSkill] = []
    projects: List[CandidateProject] = []
    experiences: List[CandidateExperience] = []
    education: List[CandidateEducation] = []
