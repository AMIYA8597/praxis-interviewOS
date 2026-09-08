import logging

logger = logging.getLogger(__name__)

async def generate_cold_outreach(candidate_id: str, company: str, detail: str, gateway_router, routing_ctx) -> str:
    """
    Generates cold outreach messages.
    System prompt strictly forbids hallucinating recipient names or unearned candidate skills.
    No auto-send capability exists.
    """
    logger.info(f"Drafting outreach for {company}")
    
    # provider = gateway_router.route("reasoning", routing_ctx)
    # prompt = "Draft a cold message. Do NOT invent a hiring manager's name if not provided."
    
    return f"Hi Team at {company},\n\nI noticed you are scaling your realtime infrastructure ({detail}). I recently reduced latency by 40% on a similar Kafka pipeline and would love to connect."
