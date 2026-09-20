import logging
import uuid
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from praxis_ai_gateway.prompt_builder import PromptBuilder

logger = logging.getLogger(__name__)

class ClaimProvenance(BaseModel):
    claim_text: str
    supported: bool
    source_chunk_id: Optional[str] = None
    source_project_id: Optional[str] = None
    source_excerpt: Optional[str] = None

class ConsistencyResult(BaseModel):
    is_contradiction: bool
    contradicted_claim_id: Optional[str] = None

class SessionClaim(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    claim_text: str
    supported: bool = False
    source_chunk_id: Optional[str] = None
    source_project_id: Optional[str] = None
    confidence: Optional[float] = None
    contradiction_of_claim_id: Optional[str] = None



async def extract_claims(answer_text: str, question_context: str, gateway_router, routing_ctx) -> List[str]:
    """
    Task 1: Claim extraction from a candidate answer.
    """
    with open("prompts/scoring/claim_extraction_v1.md", "r") as f:
        sys_prompt = f.read()

    builder = PromptBuilder()
    builder.add_system(sys_prompt)
    builder.add_trusted_context("interviewer_question", question_context)
    builder.add_untrusted("candidate_answer", "realtime_stt", answer_text)
    
    from realtime_agent.app.scoring.models import ClaimExtractionResult
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

async def check_consistency(new_claim_text: str, session_id: str, gateway_router, routing_ctx) -> ConsistencyResult:
    """
    Task 3: The Consistency Engine.
    Checks if `new_claim` contradicts any previously stored claim for this session.
    """
    from sqlalchemy import text
    query = text("SELECT id, claim_text FROM session_claims WHERE session_id = :sid")
    res = await gateway_router.db.execute(query, {"sid": session_id})
    session_claims = res.fetchall()
    
    if not session_claims:
        return ConsistencyResult(is_contradiction=False)
        
    builder = PromptBuilder()
    builder.add_system(
        "Compare the new claim against the prior claims from the same interview session. "
        "Does the new claim explicitly contradict the facts of a prior claim about the SAME entity/topic? "
        "Return the ID of the contradicted claim if yes, or None if no contradiction."
    )
    
    prior_claims_str = "\n".join([f"ID: {c.id} | Claim: {c.claim_text}" for c in session_claims])
    builder.add_trusted_context("prior_claims", prior_claims_str)
    builder.add_task(f"New Claim: {new_claim_text}")
    
    class LlmConsistencyResult(BaseModel):
        is_contradiction: bool
        contradicted_claim_id: Optional[str]
        
    builder.add_output_schema(LlmConsistencyResult)
    
    try:
        call_result = await gateway_router.route(
            "fast_classify",
            routing_ctx,
            "generate_structured",
            messages=[m.model_dump(exclude_none=True) for m in builder.build()],
            schema=LlmConsistencyResult
        )
        res = call_result.result
        return ConsistencyResult(is_contradiction=res.is_contradiction, contradicted_claim_id=res.contradicted_claim_id)
    except Exception as e:
        logger.warning(f"Consistency check failed: {e}")
        return ConsistencyResult(is_contradiction=False)

async def check_grounding(claim_text: str, candidate_id: str, gateway_router, routing_ctx) -> SessionClaim:
    """
    Task 2: Grounding check per claim.
    """
    from praxis_ai_gateway.retrieval import hybrid_search
    # gateway_router.db is an AsyncSession, we extract the bind engine
    retrieved_chunks = await hybrid_search(
        query=claim_text, 
        candidate_id=candidate_id, 
        db=gateway_router.db.bind, 
        k=3,
        boost_verified=True
    )
        
    supported = False
    source_chunk_id = None
    source_project_id = None
    confidence = None
    
    # 2. Relevance/Entailment check (fast_classify)
    if retrieved_chunks:
        # We check top chunks
        for chunk in retrieved_chunks:
            builder = PromptBuilder()
            builder.add_system("Does this retrieved context genuinely corroborate the specific claim? Reply YES or NO.")
            builder.add_trusted_context("retrieved_context", chunk.content)
            builder.add_task(f"Claim: {claim_text}")
            
            try:
                call_result = await gateway_router.route(
                    "fast_classify",
                    routing_ctx,
                    "generate",
                    messages=[m.model_dump(exclude_none=True) for m in builder.build()]
                )
                if "YES" in call_result.result.text.upper():
                    supported = True
                    source_chunk_id = chunk.id
                    source_project_id = getattr(chunk, 'project_id', None)
                    confidence = 1.0
                    break
            except Exception as e:
                logger.warning(f"Entailment check failed: {e}")
                
    return SessionClaim(
        session_id="", # Assigned by caller
        claim_text=claim_text,
        supported=supported,
        source_chunk_id=source_chunk_id,
        source_project_id=source_project_id,
        confidence=confidence
    )

async def get_claim_provenance(claim_id: str, gateway_router) -> Optional[ClaimProvenance]:
    """
    Task 6: Provenance Data Assembly for the (Future) UI.
    """
    from sqlalchemy import text
    query = text("SELECT claim_text, supported, source_chunk_id, source_project_id, confidence FROM session_claims WHERE id = :id")
    res = await gateway_router.db.execute(query, {"id": claim_id})
    row = res.fetchone()
    
    if not row:
        return None
        
    return ClaimProvenance(
        claim_text=row.claim_text,
        supported=row.supported,
        source_chunk_id=row.source_chunk_id,
        source_project_id=row.source_project_id,
        confidence=row.confidence
    )

async def process_candidate_answer_claims(answer_text: str, question_context: str, session_id: str, turn_id: str, candidate_id: str, gateway_router, routing_ctx) -> List[SessionClaim]:
    """
    End-to-end processing of claims for an answer.
    """
    claims = await extract_claims(answer_text, question_context, gateway_router, routing_ctx)
    processed_claims = []
    
    from sqlalchemy import text
    for claim_text in claims:
        # 1. Grounding Check
        session_claim = await check_grounding(claim_text, candidate_id, gateway_router, routing_ctx)
        session_claim.session_id = session_id
        
        # 2. Consistency Engine
        consistency = await check_consistency(claim_text, session_id, gateway_router, routing_ctx)
        if consistency.is_contradiction:
            session_claim.contradiction_of_claim_id = consistency.contradicted_claim_id
            
        # 3. Save to DB
        query = text("""
            INSERT INTO session_claims (id, session_id, turn_id, claim_text, supported, source_chunk_id, source_project_id, confidence, contradiction_of_claim_id)
            VALUES (:id, :session_id, :turn_id, :claim_text, :supported, :source_chunk_id, :source_project_id, :confidence, :contradiction_of_claim_id)
        """)
        await gateway_router.db.execute(query, {
            "id": session_claim.id,
            "session_id": session_claim.session_id,
            "turn_id": turn_id,
            "claim_text": session_claim.claim_text,
            "supported": session_claim.supported,
            "source_chunk_id": session_claim.source_chunk_id,
            "source_project_id": session_claim.source_project_id,
            "confidence": session_claim.confidence,
            "contradiction_of_claim_id": session_claim.contradiction_of_claim_id
        })
        await gateway_router.db.commit()
        
        processed_claims.append(session_claim)
        
    return processed_claims
