from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum

class ClaimClassification(str, Enum):
    SUPPORTED = "SUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    UNCERTAIN = "UNCERTAIN"

class ClaimGroundingResult(BaseModel):
    classification: ClaimClassification
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    source_chunk_id: Optional[str] = None
    source_excerpt: Optional[str] = None
    reasoning: Optional[str] = None

class StarCompleteness(BaseModel):
    situation: bool
    task: bool
    action: bool
    result: bool

class DimensionScores(BaseModel):
    relevance: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    correctness: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    structure: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    specificity: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    conciseness: Optional[float] = Field(default=None, ge=0.0, le=1.0)

class ExtractedClaim(BaseModel):
    claim_text: str
    is_verifiable: bool

class ClaimExtractionResult(BaseModel):
    claims: List[ExtractedClaim]

class AnswerScore(BaseModel):
    relevance: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    correctness: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    structure: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    grounding: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    specificity: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    conciseness: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    star_completeness: Optional[StarCompleteness] = None
    overall: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    rationale: str
    measurement_status: str = "MEASURED"  # MEASURED | ESTIMATED | UNAVAILABLE | DEGRADED
    rubric_version: str = "v1"


# Phase 16 — System design rubric
class SystemDesignScore(BaseModel):
    """Dedicated rubric for system design interview answers."""
    requirements_clarification: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Did candidate ask clarifying questions and establish scope?")
    high_level_design: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Quality of top-level components and data flow")
    scalability: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Addresses load, horizontal scaling, sharding, replication")
    data_modeling: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Schema design, normalization, index choices")
    api_design: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="REST/gRPC/WebSocket choices and contract quality")
    bottleneck_identification: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Identifies hot spots, SPoFs, latency sources")
    trade_off_reasoning: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Explicitly articulates and justifies trade-offs")
    communication: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Clarity, structure, collaboration with interviewer")
    overall: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    rationale: str
    measurement_status: str = "MEASURED"  # MEASURED | ESTIMATED | UNAVAILABLE | DEGRADED
    rubric_version: str = "system_design_v1"
