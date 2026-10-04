from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.dependencies import get_ai_gateway, get_current_candidate, get_db_session
from backend.app.schemas.application import (
    OutreachDraftRequest,
    OutreachDraftResponse,
    OutreachGenerateResponse,
)
from backend.app.schemas.common import COMMON_ERROR_RESPONSES, PaginatedResponse
from backend.app.services import outreach as service

router = APIRouter(tags=["outreach"], responses=COMMON_ERROR_RESPONSES)


class CampaignsPage(PaginatedResponse[OutreachDraftResponse]):
    # Legacy key kept alongside `items`.
    campaigns: list[OutreachDraftResponse] = []


@router.get("/outreach/campaigns", response_model=CampaignsPage)
async def list_campaigns(
    cursor: Optional[str] = Query(None, description="Opaque cursor from a previous page"),
    limit: int = Query(20, ge=1, le=100),
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session),
):
    page = await service.list_drafts(db, candidate["id"], cursor, limit)
    return {"items": page.items, "campaigns": page.items, "next_cursor": page.next_cursor}


@router.post("/outreach/draft", response_model=OutreachGenerateResponse)
async def draft_outreach(
    req: OutreachDraftRequest,
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session),
    gateway=Depends(get_ai_gateway),
):
    draft, saved_id = await service.draft_outreach(
        db,
        gateway,
        candidate,
        company=req.company,
        detail=req.detail,
        application_id=req.application_id,
        recipient_name=req.recipient_name,
    )
    return {"status": "success", "draft": draft, "saved_draft_id": saved_id}
