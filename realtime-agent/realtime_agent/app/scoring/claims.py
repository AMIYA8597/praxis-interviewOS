from packages.config.settings import PROJECT_ROOT
import logging
import uuid
from typing import List, Optional
from pydantic import BaseModel, Field

from praxis_ai_gateway.prompt_builder import PromptBuilder

logger = logging.getLogger(__name__)

class ClaimProvenance(BaseModel):
    claim_text: str
    supported: bool
    classification: str = "UNSUPPORTED"
    source_chunk_id: Optional[str] = None
    source_project_id: Optional[str] = None
    source_excerpt: Optional[str] = None
    confidence: Optional[float] = None

class ConsistencyResult(BaseModel):
    is_contradiction: bool
    contradicted_claim_id: Optional[str] = None

class SessionClaim(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    claim_text: str
    supported: bool = False
    classification: str = "UNSUPPORTED"
    source_chunk_id: Optional[str] = None
    source_project_id: Optional[str] = None
    source_excerpt: Optional[str] = None
    confidence: Optional[float] = None
    contradiction_of_claim_id: Optional[str] = None



async def extract_claims(answer_text: str, question_context: str, gateway_router, routing_ctx) -> List[str]:
    """
    Task 1: Claim extraction from a candidate answer.
    """
    with open(str(PROJECT_ROOT / "prompts/scoring/claim_extraction_v1.md"), "r") as f:
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
    classification = "UNSUPPORTED"
    source_chunk_id = None
    source_project_id = None
    source_excerpt = None
    confidence = None
    
    # 2. Relevance/Entailment check (5-tier classification)
    if retrieved_chunks:
        from realtime_agent.app.scoring.models import ClaimGroundingResult
        for chunk in retrieved_chunks:
            builder = PromptBuilder()
            builder.add_system(
                "You are an evidence verification engine. Compare the candidate's claim against the retrieved context from their verified background documents.\n"
                "Classify the claim into exactly one tier:\n"
                "- SUPPORTED: Direct factual evidence proves the claim.\n"
                "- PARTIALLY_SUPPORTED: The claim is mostly consistent with the evidence but slightly overstated.\n"
                "- UNSUPPORTED: The retrieved context mentions related concepts but cannot verify this specific claim.\n"
                "- CONTRADICTED: The retrieved context directly contradicts the candidate's claim.\n"
                "- UNCERTAIN: Ambiguous context or insufficient detail to determine truth.\n"
                "Extract the exact source excerpt when available."
            )
            builder.add_trusted_context("retrieved_context", chunk.content)
            builder.add_task(f"Claim: {claim_text}")
            builder.add_output_schema(ClaimGroundingResult)
            
            try:
                call_result = await gateway_router.route(
                    "claim_grounding",
                    routing_ctx,
                    "generate_structured",
                    messages=[m.model_dump(exclude_none=True) for m in builder.build()],
                    schema=ClaimGroundingResult
                )
                res = call_result.result
                classification = res.classification.value if hasattr(res.classification, "value") else str(res.classification)
                confidence = res.confidence
                source_excerpt = res.source_excerpt
                raw_pid = getattr(chunk, 'project_id', None)
                pid_str = str(raw_pid) if (raw_pid is not None and not hasattr(raw_pid, "_mock_name")) else None
                if classification in ("SUPPORTED", "PARTIALLY_SUPPORTED"):
                    supported = True
                    source_chunk_id = str(chunk.id) if chunk.id else None
                    source_project_id = pid_str
                    break
                elif classification == "CONTRADICTED":
                    supported = False
                    source_chunk_id = str(chunk.id) if chunk.id else None
                    source_project_id = pid_str
                    break
            except Exception as e:
                logger.warning(f"Structured entailment check failed: {e}")
                try:
                    call_result = await gateway_router.route(
                        "fast_classify",
                        routing_ctx,
                        "generate",
                        messages=[m.model_dump(exclude_none=True) for m in builder.build()]
                    )
                    txt = getattr(call_result.result, "text", "") or ""
                    if "YES" in txt.upper() or "SUPPORTED" in txt.upper():
                        supported = True
                        classification = "SUPPORTED"
                        source_chunk_id = chunk.id
                        source_project_id = getattr(chunk, 'project_id', None)
                        confidence = 0.9
                        break
                    elif "CONTRADICT" in txt.upper():
                        supported = False
                        classification = "CONTRADICTED"
                        source_chunk_id = chunk.id
                        confidence = 0.9
                        break
                    else:
                        classification = "UNCERTAIN"
                        confidence = 0.5
                except Exception as ex2:
                    logger.warning(f"Entailment fallback failed: {ex2}")
                    classification = "UNCERTAIN"
                    confidence = 0.3
                
    return SessionClaim(
        session_id="", # Assigned by caller
        claim_text=claim_text,
        supported=supported,
        classification=classification,
        source_chunk_id=source_chunk_id,
        source_project_id=source_project_id,
        source_excerpt=source_excerpt,
        confidence=confidence
    )

async def get_claim_provenance(claim_id: str, gateway_router) -> Optional[ClaimProvenance]:
    """
    Task 6: Provenance Data Assembly for the UI.
    """
    from sqlalchemy import text
    query = text("SELECT claim_text, supported, source_chunk_id, source_project_id, confidence FROM session_claims WHERE id = :id")
    res = await gateway_router.db.execute(query, {"id": claim_id})
    row = res.fetchone()
    
    if not row:
        return None
        
    classification = "SUPPORTED" if row.supported else "UNSUPPORTED"
    return ClaimProvenance(
        claim_text=row.claim_text,
        supported=row.supported,
        classification=classification,
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
