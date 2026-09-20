import asyncio
import json
import logging
import hashlib
from typing import Literal, Optional
from pydantic import BaseModel
from praxis_ai_gateway.router import GatewayRouter

logger = logging.getLogger(__name__)

class QuestionClassification(BaseModel):
    is_question: bool
    confidence: float
    question_type: Literal[
        "behavioral", "resume", "project", "technical", "coding", 
        "debugging", "sql", "dsa", "ml", "deep_learning", "genai", 
        "rag", "system_design", "architecture", "database", "cloud", 
        "devops", "statistics", "probability", "case_study", "follow_up", 
        "clarification", "other"
    ]
    domain: Literal[
        "Python", "SQL", "ML", "System Design", "Cloud", "General", "Other"
    ]
    is_follow_up: bool

# Simple heuristic fallback
def _heuristic_fallback(transcript: str) -> QuestionClassification:
    text = transcript.strip().lower()
    
    # Affirmation filter
    affirmations = {"okay", "great", "mm-hmm", "i see", "yes", "no", "sure", "got it", "makes sense", "right"}
    if len(text.split()) <= 3 and any(a in text for a in affirmations):
        return QuestionClassification(
            is_question=False,
            confidence=0.9,
            question_type="other",
            domain="Other",
            is_follow_up=False
        )
        
    return QuestionClassification(
        is_question=True,
        confidence=0.5, # low confidence for fallback
        question_type="other",
        domain="Other",
        is_follow_up=False
    )

class FastClassifier:
    """
    ### ORCHESTRATOR INTERFACE CONTRACT:
    - **Invocation Phase**: Call `classify(transcript, prior_context)` during the `TURN_END` phase, immediately after the candidate finishes speaking.
    - **Output Shape**: Returns a `QuestionClassification` Pydantic model (contains `is_question`, `question_type`, `domain`, `is_follow_up`, etc.).
    - **Latency Guarantee**: Enforces a strict 120ms timeout. Will NOT block state transitions for more than 120ms. If the LLM exceeds this, it gracefully returns a deterministic heuristic fallback.
    """
    def __init__(self, router: GatewayRouter, redis_pool=None):
        self.router = router
        self.redis_pool = redis_pool
        with open("prompts/classification/domain_v1.md", "r", encoding="utf-8") as f:
            self.prompt_template = f.read()

    async def classify(self, transcript: str, prior_context: str = "") -> QuestionClassification:
        # Fast-path false-question filter
        fallback = _heuristic_fallback(transcript)
        if not fallback.is_question:
            logger.debug("Fast-path heuristic matched false-question. Bypassing LLM.")
            return fallback

        # Cache Key Strategy: hash of transcript + prior_context
        cache_key = None
        if self.redis_pool:
            key_content = f"{transcript.strip()}|{prior_context.strip()}"
            hash_id = hashlib.md5(key_content.encode('utf-8')).hexdigest()
            cache_key = f"cache:classify:{hash_id}"
            
            try:
                cached = await self.redis_pool.get(cache_key)
                if cached:
                    logger.debug("Classification loaded from cache")
                    return QuestionClassification.model_validate_json(cached)
            except Exception as e:
                logger.warning(f"Redis cache read failed: {e}")

        from praxis_ai_gateway.prompt_builder import PromptBuilder
        builder = PromptBuilder()
        builder.add_system(self.prompt_template)
        if prior_context:
            builder.add_trusted_context("prior_context", prior_context)
        builder.add_untrusted("transcript", "realtime_stt", transcript)
        builder.add_output_schema(QuestionClassification)
        
        from praxis_ai_gateway.router import RoutingContext
        context = RoutingContext(user_id="system", zero_spend_mode=False, local_only=False)
        
        async def _do_route():
            call_result = await self.router.route(
                "fast_classify", 
                context, 
                "generate_structured",
                messages=[m.model_dump(exclude_none=True) for m in builder.build()],
                schema=QuestionClassification
            )
            # The result is stored in call_result.result, which will be the validated Pydantic model
            return call_result.result
            
        try:
            # 120ms timeout as budgeted in spec
            # Note: local dummy calls are instant, real LLMs will hit this limit if slow.
            result = await asyncio.wait_for(_do_route(), timeout=0.120)
            
            if self.redis_pool and cache_key:
                try:
                    # Cache with 60s TTL since transcripts are ephemeral to the turn
                    await self.redis_pool.setex(
                        cache_key, 
                        60, 
                        result.model_dump_json()
                    )
                except Exception as e:
                    logger.warning(f"Redis cache write failed: {e}")
                    
            return result
        except asyncio.TimeoutError:
            logger.warning("fast_classify timed out (>120ms). Applying graceful heuristic fallback.")
            return _heuristic_fallback(transcript)
        except Exception as e:
            logger.error(f"fast_classify failed: {e}. Applying fallback.")
            return _heuristic_fallback(transcript)
