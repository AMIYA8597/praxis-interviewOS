"""
Phase 57-60 — Real Preparation Engine, Readiness 2.0, JD-Driven Preparation, Adaptive Difficulty.
"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.dependencies import get_current_candidate, get_db_session
from backend.app.schemas.common import COMMON_ERROR_RESPONSES
from backend.app.services import adaptive_difficulty as adiff_svc
from backend.app.services import jd_preparation as jd_svc
from backend.app.services import preparation_engine as prep_svc
from backend.app.services import readiness_v2 as r2_svc

router = APIRouter(tags=["preparation"], responses=COMMON_ERROR_RESPONSES)


@router.get("/preparation/plan")
async def get_preparation_plan(
    job_id: Optional[uuid.UUID] = Query(None),
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session),
):
    """Phase 57: Real preparation plan ordered by weakness × job_relevance × impact."""
    return await prep_svc.generate_real_preparation_plan(db, candidate["id"], str(job_id) if job_id else None)


@router.get("/readiness/v2")
async def get_readiness_v2(
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session),
):
    """Phase 58: Per-dimension readiness with confidence, trend, and evidence."""
    return await r2_svc.get_readiness_v2(db, candidate["id"])


class JdParseRequest(BaseModel):
    job_id: uuid.UUID
    jd_text: str


@router.post("/preparation/jd-parse")
async def parse_jd(
    body: JdParseRequest,
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session),
):
    """Phase 59: Parse JD into requirement graph."""
    return await jd_svc.parse_and_store_jd_requirements(
        db, str(body.job_id), body.jd_text
    )


@router.get("/preparation/jd-coverage")
async def get_jd_coverage(
    job_id: uuid.UUID = Query(...),
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session),
):
    """Phase 59: Candidate evidence map for a job's requirements."""
    return await jd_svc.build_candidate_evidence_map(db, candidate["id"], str(job_id))


@router.get("/sessions/{session_id}/difficulty")
async def get_difficulty(
    session_id: uuid.UUID,
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session),
):
    """Phase 60: Current adaptive difficulty state for a session."""
    return await adiff_svc.get_session_difficulty(db, str(session_id))
