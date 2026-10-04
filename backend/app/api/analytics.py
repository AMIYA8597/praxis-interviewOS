from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.dependencies import get_current_candidate, get_db_session
from backend.app.schemas.common import COMMON_ERROR_RESPONSES
from backend.app.services import analytics as service

router = APIRouter(tags=["analytics"], responses=COMMON_ERROR_RESPONSES)


class DashboardResponse(BaseModel):
    interviews_completed: int
    total_sessions: int
    average_pace_wpm: float
    filler_word_density: float
    average_score: float
    star_consistency: Optional[float] = None


class ReportsResponse(BaseModel):
    reports: List[Dict[str, Any]]


@router.get("/analytics/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session),
):
    return await service.dashboard(db, candidate["id"])


@router.get("/analytics/reports", response_model=ReportsResponse)
async def get_reports(
    limit: int = Query(20, ge=1, le=100),
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session),
):
    return await service.reports(db, candidate["id"], limit)
