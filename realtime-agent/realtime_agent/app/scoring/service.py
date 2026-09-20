import asyncio
import logging
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from realtime_agent.app.scoring.models import AnswerScore, DimensionScores, StarCompleteness, ClaimExtractionResult
from praxis_ai_gateway.prompt_builder import PromptBuilder

logger = logging.getLogger(__name__)

async def extract_claims(text: str, gateway_router, routing_ctx) -> List[str]:
    """
    Extracts key factual claims from the candidate's answer.
    This overlaps with Phase 3.13's claim extraction.
    """
    builder = PromptBuilder()
    builder.add_system("Extract key verifiable factual claims from the following text. Ignore opinions or subjective statements.")
    builder.add_untrusted("candidate_answer", "realtime_stt", text)
    builder.add_output_schema(ClaimExtractionResult)
    
    try:
        call_result = await gateway_router.route(
            "fast_classify",
            routing_ctx,
            "generate_structured",
            messages=[m.model_dump(exclude_none=True) for m in builder.build()],
            schema=ClaimExtractionResult
        )
        return [c.claim_text for c in call_result.result.claims if c.is_verifiable]
    except Exception as e:
        logger.warning(f"Claim extraction failed: {e}")
        return []

async def verify_claim(claim: str, context: str, gateway_router, routing_ctx) -> bool:
    """
    Checks if a claim is supported by the verified context.
    """
    if not context:
        return False
        
    builder = PromptBuilder()
    builder.add_system("Is the following claim supported by the verified context? Reply YES or NO.")
    builder.add_trusted_context("verified_facts", context)
    builder.add_task(f"Claim to verify: {claim}")
    
    try:
        call_result = await gateway_router.route(
            "fast_classify",
            routing_ctx,
            "generate",
            messages=[m.model_dump(exclude_none=True) for m in builder.build()]
        )
        return "YES" in call_result.result.text.upper()
    except Exception as e:
        logger.warning(f"Claim verification failed: {e}")
        return False

async def calculate_grounding_score(candidate_answer: str, verified_context: str, gateway_router, routing_ctx) -> float:
    """
    Task 3: Cross-reference against retrieval.
    Extract claims and verify against provided context.
    """
    claims = await extract_claims(candidate_answer, gateway_router, routing_ctx)
    if not claims:
        # If there are no claims made, grounding is perfectly 1.0 (they didn't make anything up)
        return 1.0
        
    supported_count = 0
    for claim in claims:
        is_supported = await verify_claim(claim, verified_context, gateway_router, routing_ctx)
        if is_supported:
            supported_count += 1
            
    return supported_count / len(claims)

async def score_answer_async(
    question: str, 
    candidate_answer: str, 
    is_behavioral: bool, 
    verified_context: str, 
    gateway_router, 
    routing_ctx
) -> AnswerScore:
    """
    Scores the candidate's answer using the rubric.
    """
    logger.info("Background scoring started...")
    
    # 1. Calculate grounding separately
    grounding = await calculate_grounding_score(candidate_answer, verified_context, gateway_router, routing_ctx)
    
    # 2. Score other dimensions via LLM
    with open("prompts/scoring/rubric_v1.md", "r") as f:
        rubric_prompt = f.read()
        
    builder = PromptBuilder()
    builder.add_system(rubric_prompt)
    builder.add_trusted_context("interviewer_question", question)
    if is_behavioral:
        builder.add_task("This is a behavioral question. You MUST populate star_completeness.")
        
    builder.add_untrusted("candidate_answer", "realtime_stt", candidate_answer)
    builder.add_output_schema(DimensionScores) # Wait, we need a combined schema if we want the LLM to output everything except grounding
    
    class LlmScoringResult(BaseModel):
        relevance: float = Field(ge=0.0, le=1.0)
        correctness: float = Field(ge=0.0, le=1.0)
        structure: float = Field(ge=0.0, le=1.0)
        specificity: float = Field(ge=0.0, le=1.0)
        conciseness: float = Field(ge=0.0, le=1.0)
        star_completeness: Optional[StarCompleteness] = None
        rationale: str
        
    builder.add_output_schema(LlmScoringResult)
    
    try:
        call_result = await gateway_router.route(
            "deep_reasoning",
            routing_ctx,
            "generate_structured",
            messages=[m.model_dump(exclude_none=True) for m in builder.build()],
            schema=LlmScoringResult
        )
        llm_score = call_result.result
    except Exception as e:
        logger.error(f"LLM Scoring failed: {e}")
        llm_score = LlmScoringResult(
            relevance=0.5, correctness=0.5, structure=0.5, specificity=0.5, conciseness=0.5,
            rationale="Scoring failed fallback."
        )
        
    # Calculate overall score deterministically
    weights = {
        'correctness': 0.3,
        'relevance': 0.2,
        'specificity': 0.2,
        'structure': 0.1,
        'grounding': 0.1,
        'conciseness': 0.1
    }
    
    overall = (
        llm_score.correctness * weights['correctness'] +
        llm_score.relevance * weights['relevance'] +
        llm_score.specificity * weights['specificity'] +
        llm_score.structure * weights['structure'] +
        grounding * weights['grounding'] +
        llm_score.conciseness * weights['conciseness']
    )
    
    final_score = AnswerScore(
        relevance=llm_score.relevance,
        correctness=llm_score.correctness,
        structure=llm_score.structure,
        grounding=grounding,
        specificity=llm_score.specificity,
        conciseness=llm_score.conciseness,
        star_completeness=llm_score.star_completeness,
        overall=overall,
        rationale=llm_score.rationale,
        rubric_version="v1"
    )
    
    logger.info(f"Background scoring finished. Overall: {overall:.2f}")
    return final_score

def trigger_background_scoring(question: str, candidate_answer: str, is_behavioral: bool, verified_context: str, gateway_router, routing_ctx, state_machine=None):
    """
    Task 2: Asynchronous, Non-Blocking Scoring.
    Fires off the scoring task without awaiting it.
    """
    async def _run_score():
        try:
            score = await score_answer_async(question, candidate_answer, is_behavioral, verified_context, gateway_router, routing_ctx)
            # In a real system, we'd save this to the DB.
            if state_machine:
                state_machine.last_score = score
        except Exception as e:
            logger.error(f"Background scoring task crashed: {e}")
            
    task = asyncio.create_task(_run_score())
    return task
