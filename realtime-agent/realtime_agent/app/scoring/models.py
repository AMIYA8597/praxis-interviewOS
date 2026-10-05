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


# Phase 16 — System design rubric
class SystemDesignScore(BaseModel):
    """Dedicated rubric for system design interview answers."""
    requirements_clarification: float = Field(ge=0.0, le=1.0, description="Did candidate ask clarifying questions and establish scope?")
    high_level_design: float = Field(ge=0.0, le=1.0, description="Quality of top-level components and data flow")
    scalability: float = Field(ge=0.0, le=1.0, description="Addresses load, horizontal scaling, sharding, replication")
    data_modeling: float = Field(ge=0.0, le=1.0, description="Schema design, normalization, index choices")
    api_design: float = Field(ge=0.0, le=1.0, description="REST/gRPC/WebSocket choices and contract quality")
    bottleneck_identification: float = Field(ge=0.0, le=1.0, description="Identifies hot spots, SPoFs, latency sources")
    trade_off_reasoning: float = Field(ge=0.0, le=1.0, description="Explicitly articulates and justifies trade-offs")
    communication: float = Field(ge=0.0, le=1.0, description="Clarity, structure, collaboration with interviewer")
    overall: float = Field(ge=0.0, le=1.0)
    rationale: str
    rubric_version: str = "system_design_v1"
