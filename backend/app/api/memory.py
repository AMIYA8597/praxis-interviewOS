"""
Phase 55-56 — Candidate Memory & Interview Profile API.
"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.dependencies import get_current_candidate, get_db_session
from backend.app.schemas.common import COMMON_ERROR_RESPONSES
from backend.app.services import candidate_memory as mem_svc
from backend.app.services import interview_profile as profile_svc

router = APIRouter(tags=["memory"], responses=COMMON_ERROR_RESPONSES)


@router.get("/memory/summary")
async def get_memory_summary(
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Returns candidate's topic facts + active inferences.
    Facts are measurable observations; inferences are tagged as interpretations.
    """
    return await mem_svc.get_candidate_memory_summary(db, candidate["id"])


@router.post("/memory/update-from-session")
async def update_memory_from_session(
    session_id: uuid.UUID = Query(...),
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Trigger memory update from a completed session.
    Called internally after debrief; also exposed for manual re-trigger.
    """
    # Verify session belongs to this candidate
    from sqlalchemy import text
    row = (await db.execute(text(
        "SELECT id FROM practice_sessions WHERE id = :sid AND candidate_id = :cid"
    ), {"sid": str(session_id), "cid": candidate["id"]})).fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Session not found for this candidate.")

    await mem_svc.update_topic_facts_from_session(db, candidate["id"], str(session_id))
    return {"status": "updated"}


@router.get("/profile")
async def get_profile(
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Return computed interview profile. All scores are derived from real sessions.
    Null = insufficient data — complete more practice sessions.
    """
    profile = await profile_svc.get_interview_profile(db, candidate["id"])
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No profile computed yet. Complete practice sessions to build your profile.",
        )
    return profile


@router.post("/profile/compute")
async def compute_profile(
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Recompute interview profile from all available session data.
    Returns the updated profile.
    """
    return await profile_svc.compute_interview_profile(db, candidate["id"])
