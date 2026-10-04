import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from praxis_ai_gateway.base import LLMMessage
from praxis_ai_gateway.router import GatewayRouter, RoutingContext

from backend.app.db.models import Application
from backend.app.exceptions import NotFoundError, ServiceUnavailableError
from backend.app.repositories import outreach as repo
from backend.app.repositories import owned
from backend.app.repositories.base import Page

logger = logging.getLogger(__name__)

DRAFT_FAILED_TEXT = "Draft generation failed. Please try again."


async def generate_cold_outreach(
    candidate_id: str, company: str, detail: str, gateway_router: GatewayRouter, routing_ctx: RoutingContext
) -> str:
    """
    Generates cold outreach messages.
    System prompt strictly forbids hallucinating recipient names or unearned candidate skills.
    No auto-send capability exists.
    """
    logger.info("outreach_draft_requested")
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
        result = resp.result
        return getattr(result, "text", result)
    except Exception as e:
        logger.error("outreach_generation_failed", extra={"error_type": type(e).__name__})
        return DRAFT_FAILED_TEXT


async def list_drafts(db: AsyncSession, candidate_id: str, cursor: Optional[str], limit: int) -> Page:
    return await repo.list_drafts(db, candidate_id, cursor=cursor, limit=limit)


async def draft_outreach(
    db: AsyncSession,
    gateway,
    candidate: dict,
    *,
    company: str,
    detail: str,
    application_id=None,
    recipient_name: Optional[str] = None,
):
    if application_id is not None:
        app = await owned.get_owned(db, Application, application_id, candidate["id"], extra=(Application.deleted_at.is_(None),))
        if app is None:
            raise NotFoundError("Application")
    ctx = RoutingContext(user_id=candidate["user_id"])
    draft = await generate_cold_outreach(candidate["id"], company, detail, gateway, ctx)
    if draft == DRAFT_FAILED_TEXT:
        raise ServiceUnavailableError("Draft generation is temporarily unavailable")
    saved_id = None
    if application_id is not None:
        saved = await repo.create_draft(db, application_id, f"Reaching out to {company}", draft, recipient_name)
        await db.commit()
        saved_id = saved.id
    return draft, saved_id
