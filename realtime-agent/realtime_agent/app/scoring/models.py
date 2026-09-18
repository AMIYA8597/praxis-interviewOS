from pydantic import BaseModel, Field
from typing import Optional, List

class StarCompleteness(BaseModel):
    situation: bool
    task: bool
    action: bool
    result: bool

class DimensionScores(BaseModel):
    relevance: float = Field(ge=0.0, le=1.0)
    correctness: float = Field(ge=0.0, le=1.0)
    structure: float = Field(ge=0.0, le=1.0)
    specificity: float = Field(ge=0.0, le=1.0)
    conciseness: float = Field(ge=0.0, le=1.0)

class ExtractedClaim(BaseModel):
    claim_text: str
    is_verifiable: bool

class ClaimExtractionResult(BaseModel):
    claims: List[ExtractedClaim]

class AnswerScore(BaseModel):
    relevance: float = Field(ge=0.0, le=1.0)
    correctness: float = Field(ge=0.0, le=1.0)
    structure: float = Field(ge=0.0, le=1.0)
    grounding: float = Field(ge=0.0, le=1.0)
    specificity: float = Field(ge=0.0, le=1.0)
    conciseness: float = Field(ge=0.0, le=1.0)
    star_completeness: Optional[StarCompleteness] = None
    overall: float = Field(ge=0.0, le=1.0)
    rationale: str
    rubric_version: str = "v1"
