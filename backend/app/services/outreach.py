import logging
from praxis_ai_gateway.router import GatewayRouter, RoutingContext
from praxis_ai_gateway.base import LLMMessage

logger = logging.getLogger(__name__)

async def generate_cold_outreach(candidate_id: str, company: str, detail: str, gateway_router: GatewayRouter, routing_ctx: RoutingContext) -> str:
    """
    Generates cold outreach messages.
    System prompt strictly forbids hallucinating recipient names or unearned candidate skills.
    No auto-send capability exists.
    """
    logger.info(f"Drafting outreach for {company}")
    
    prompt = f"""
    Draft a cold outreach message for {company}.
    Context about why I am reaching out: {detail}.
    
    CRITICAL INSTRUCTIONS:
    - DO NOT invent or hallucinate a hiring manager's name. Use a generic greeting like 'Hi Team' if no name is provided.
    - DO NOT invent unearned candidate skills. Base it only on standard professional courtesy.
    - Keep it concise, under 4 sentences.
    """
    
    messages = [LLMMessage(role="user", content=prompt)]
    
    try:
        resp = await gateway_router.route("reasoning", routing_ctx, "generate", messages=messages)
        return resp.result
    except Exception as e:
        logger.error(f"Failed to generate outreach: {e}")
        return "Draft generation failed. Please try again."
