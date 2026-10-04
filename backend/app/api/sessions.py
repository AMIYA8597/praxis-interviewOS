import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from opentelemetry import trace
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.dependencies import get_arq_pool, get_current_candidate, get_db_session
from backend.app.schemas.common import COMMON_ERROR_RESPONSES, PaginatedResponse
from backend.app.schemas.session import (
    SessionCreate,
    SessionDebriefResponse,
    SessionEndResponse,
    SessionResponse,
    SessionTurnResponse,
)
from backend.app.services import sessions as service

router = APIRouter(tags=["sessions"], responses=COMMON_ERROR_RESPONSES)


@router.post("/sessions", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    session_data: SessionCreate,
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session),
):
    session = await service.create_session(db, candidate["id"], session_data)
    span = trace.get_current_span()
    if span.is_recording():
        span.set_attribute("session_id", str(session.id))
    return session


@router.get("/sessions", response_model=PaginatedResponse[SessionResponse])
async def list_sessions(
    cursor: Optional[str] = Query(None, description="Opaque cursor from a previous page"),
    limit: int = Query(20, ge=1, le=100),
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session),
):
    page = await service.list_sessions(db, candidate["id"], cursor, limit)
    return {"items": page.items, "next_cursor": page.next_cursor}


@router.get("/sessions/{id}", response_model=SessionResponse)
async def get_session(
    id: uuid.UUID,
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session),
):
    return await service.get_session(db, id, candidate["id"])


@router.get("/sessions/{id}/turns", response_model=List[SessionTurnResponse])
async def get_session_turns(
    id: uuid.UUID,
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session),
):
    return await service.list_turns(db, id, candidate["id"])


@router.get("/sessions/{id}/debrief", response_model=SessionDebriefResponse)
async def get_session_debrief(
    id: uuid.UUID,
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session),
):
    return await service.get_debrief(db, id, candidate["id"])


@router.post("/sessions/{id}/end", response_model=SessionEndResponse, status_code=status.HTTP_202_ACCEPTED)
async def end_session(
    id: uuid.UUID,
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session),
    arq_pool=Depends(get_arq_pool),
):
    """Mark the session completed and queue debrief generation."""
    return await service.end_session(db, arq_pool, id, candidate["id"])
