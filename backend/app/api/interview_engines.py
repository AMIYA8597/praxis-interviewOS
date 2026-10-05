"""
Phase 61-65 — Interviewer Personality, System Design Engine, Coding Engine, Behavioral Engine APIs.
"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.dependencies import get_current_candidate, get_db_session
from backend.app.schemas.common import COMMON_ERROR_RESPONSES
from backend.app.services import behavioral_engine as beh_svc
from backend.app.services import coding_engine as code_svc
from backend.app.services import interviewer_personality as personality_svc
from backend.app.services import system_design_engine as sd_svc

router = APIRouter(tags=["interview-engines"], responses=COMMON_ERROR_RESPONSES)


# ── Phase 61: Interviewer Personality ──────────────────────────────────────

@router.get("/interviewer/personalities")
async def list_personalities():
    return {"personalities": personality_svc.get_available_personalities()}


class SetPersonalityRequest(BaseModel):
    session_id: uuid.UUID
    personality: str


@router.post("/interviewer/personality")
async def set_personality(
    body: SetPersonalityRequest,
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session),
):
    valid = [p["personality"] for p in personality_svc.get_available_personalities()]
    if body.personality not in valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Invalid personality. Choose from: {valid}")

    desc = personality_svc.get_personality_description(body.personality)
    await db.execute(text("""
        INSERT INTO session_interviewer_config (session_id, personality, description)
        VALUES (:sid, :p, :d)
        ON CONFLICT (session_id) DO UPDATE SET personality = EXCLUDED.personality, description = EXCLUDED.description
    """), {"sid": str(body.session_id), "p": body.personality, "d": desc})
    await db.commit()
    return {"session_id": str(body.session_id), "personality": body.personality, "description": desc}


# ── Phase 62: System Design Engine ─────────────────────────────────────────

@router.get("/sessions/{session_id}/system-design/state")
async def get_sd_state(
    session_id: uuid.UUID,
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session),
):
    return await sd_svc.get_or_create_sd_state(db, str(session_id))


@router.post("/sessions/{session_id}/system-design/advance")
async def advance_sd_phase(
    session_id: uuid.UUID,
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session),
):
    return await sd_svc.advance_sd_phase(db, str(session_id))


# ── Phase 63: Diagram Intelligence ─────────────────────────────────────────

class DiagramAnalysisRequest(BaseModel):
    spoken_reasoning: str
    diagram_components: list[str]


@router.post("/sessions/{session_id}/diagram/analyze")
async def analyze_diagram(
    session_id: uuid.UUID,
    body: DiagramAnalysisRequest,
    candidate: dict = Depends(get_current_candidate),
):
    contradictions = sd_svc.analyze_diagram_contradictions(
        body.spoken_reasoning, body.diagram_components
    )
    return {
        "session_id": str(session_id),
        "contradictions": contradictions,
        "contradiction_count": len(contradictions),
    }


# ── Phase 64: Coding Engine ─────────────────────────────────────────────────

class CodeRunRequest(BaseModel):
    code: str
    test_cases: list[dict]
    language: str = "python"
    time_limit_ms: int = 2000


@router.post("/sessions/{session_id}/code/run")
async def run_code(
    session_id: uuid.UUID,
    body: CodeRunRequest,
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session),
):
    if body.language not in ("python",):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Only 'python' is currently supported.")
    if len(body.test_cases) > 20:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Maximum 20 test cases per run.")
    return await code_svc.run_code_against_tests(
        db, str(session_id), body.code, body.test_cases,
        body.language, body.time_limit_ms,
    )


@router.get("/sessions/{session_id}/code/state")
async def get_code_state(
    session_id: uuid.UUID,
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session),
):
    state = await code_svc.get_coding_state(db, str(session_id))
    if state is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="No coding state for this session.")
    return state


# ── Phase 65: Behavioral Engine ─────────────────────────────────────────────

class StarAnalysisRequest(BaseModel):
    answer: str


@router.post("/behavioral/star-analysis")
async def analyze_star(body: StarAnalysisRequest):
    star = beh_svc.detect_star_components(body.answer)
    feedback = beh_svc.generate_star_feedback(star, body.answer)
    return {"star_components": star, "feedback": feedback}


class ResumeProbingRequest(BaseModel):
    resume_claim: str
    context: str = ""


@router.post("/behavioral/resume-probe")
async def generate_resume_probe(body: ResumeProbingRequest):
    question = beh_svc.generate_resume_defense_question(body.resume_claim, body.context)
    return {"probe_question": question}
