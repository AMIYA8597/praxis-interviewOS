import asyncio
import logging
from pydantic import BaseModel
from praxis_ai_gateway.router import GatewayRouter, RoutingContext

logger = logging.getLogger(__name__)

class CompletenessResult(BaseModel):
    is_complete: bool

class TurnEndDecision(BaseModel):
    is_turn_end: bool
    reason: str

class TurnEndDetector:
    def __init__(self, router: GatewayRouter, silence_threshold_ms: int = 550):
        self.router = router
        self.silence_threshold_ms = silence_threshold_ms
        with open("prompts/classification/completeness_v1.md", "r", encoding="utf-8") as f:
            self.prompt_template = f.read()

    async def evaluate(self, vad_silence_ms: int, partial_transcript: str) -> TurnEndDecision:
        if vad_silence_ms < self.silence_threshold_ms:
            return TurnEndDecision(is_turn_end=False, reason="silence_under_threshold")
            
        # VAD silence has exceeded threshold.
        # But is it just a long mid-sentence pause?
        clean_text = partial_transcript.strip()
        
        # If there's barely any text, it's definitely a turn end or noise
        if len(clean_text.split()) < 2:
            return TurnEndDecision(is_turn_end=True, reason="silence_over_threshold_short_text")

        from praxis_ai_gateway.prompt_builder import PromptBuilder
        builder = PromptBuilder()
        builder.add_system(self.prompt_template)
        builder.add_untrusted("partial_transcript", "realtime_stt", clean_text)
        builder.add_output_schema(CompletenessResult)
        
        context = RoutingContext(user_id="system", zero_spend_mode=False, local_only=False)
        
        async def _do_route():
            call_result = await self.router.route(
                "fast_classify", 
                context, 
                "generate_structured",
                messages=[m.model_dump(exclude_none=True) for m in builder.build()],
                schema=CompletenessResult
            )
            return call_result.result

        try:
            # Budget strictly under 150ms
            result = await asyncio.wait_for(_do_route(), timeout=0.120)
            if not result.is_complete:
                logger.info(f"Semantic completeness check blocked turn end for fragment: '{clean_text}'")
                return TurnEndDecision(is_turn_end=False, reason="mid_sentence_pause")
            return TurnEndDecision(is_turn_end=True, reason="silence_and_semantically_complete")
        except asyncio.TimeoutError:
            logger.warning("Completeness check timed out. Falling back to VAD silence decision.")
            return TurnEndDecision(is_turn_end=True, reason="silence_timeout_fallback")
        except Exception as e:
            logger.error(f"Completeness check failed ({e}). Falling back to VAD.")
            return TurnEndDecision(is_turn_end=True, reason="silence_error_fallback")
