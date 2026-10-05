import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.dependencies import get_current_candidate, get_db_session
from backend.app.schemas.common import COMMON_ERROR_RESPONSES
from backend.app.schemas.question_bank import (
    InterviewDomainResponse,
    QuestionBankCreate,
    QuestionBankResponse,
)

router = APIRouter(tags=["questions"], responses=COMMON_ERROR_RESPONSES)


@router.get("/questions/domains", response_model=List[InterviewDomainResponse])
async def list_domains(
    category: Optional[str] = Query(None, description="Filter by category: TECHNICAL, BEHAVIORAL, SPECIALIZED"),
    db: AsyncSession = Depends(get_db_session),
    _: dict = Depends(get_current_candidate),
):
    q = "SELECT id, code, parent_code, category, label, description, sort_order FROM interview_domains"
    params: dict = {}
    if category:
        q += " WHERE category = :category"
        params["category"] = category.upper()
    q += " ORDER BY sort_order"
    rows = (await db.execute(text(q), params)).mappings().all()
    return [dict(r) for r in rows]


@router.get("/questions", response_model=List[QuestionBankResponse])
async def list_questions(
    domain_code: Optional[str] = Query(None),
    difficulty: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db_session),
    _: dict = Depends(get_current_candidate),
):
    filters = ["quality_status = 'approved'"]
    params: dict = {"limit": limit, "offset": offset}
    if domain_code:
        filters.append("domain_code = :domain_code")
        params["domain_code"] = domain_code.upper()
    if difficulty:
        filters.append("difficulty = :difficulty")
        params["difficulty"] = difficulty.lower()
    where = " AND ".join(filters)
    q = f"""
        SELECT id, domain_code, subcategory, difficulty, title, body,
               expected_concepts, rubric, role_tags, source, quality_status, created_at
        FROM question_bank
        WHERE {where}
        ORDER BY created_at DESC
        LIMIT :limit OFFSET :offset
    """
    rows = (await db.execute(text(q), params)).mappings().all()
    return [dict(r) for r in rows]


@router.get("/questions/{question_id}", response_model=QuestionBankResponse)
async def get_question(
    question_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    _: dict = Depends(get_current_candidate),
):
    q = """
        SELECT id, domain_code, subcategory, difficulty, title, body,
               expected_concepts, rubric, role_tags, source, quality_status, created_at
        FROM question_bank
        WHERE id = :id AND quality_status = 'approved'
    """
    row = (await db.execute(text(q), {"id": str(question_id)})).mappings().first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
    return dict(row)


@router.post("/questions", response_model=QuestionBankResponse, status_code=status.HTTP_201_CREATED)
async def create_question(
    body: QuestionBankCreate,
    db: AsyncSession = Depends(get_db_session),
    _: dict = Depends(get_current_candidate),
):
    # Verify domain exists
    domain_check = await db.execute(
        text("SELECT code FROM interview_domains WHERE code = :code"),
        {"code": body.domain_code.upper()},
    )
    if not domain_check.first():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Unknown domain_code: {body.domain_code}")

    q = """
        INSERT INTO question_bank
          (domain_code, subcategory, difficulty, title, body, expected_concepts, rubric, role_tags, source, quality_status)
        VALUES
          (:domain_code, :subcategory, :difficulty, :title, :body, :expected_concepts, :rubric, :role_tags, :source, 'draft')
        RETURNING id, domain_code, subcategory, difficulty, title, body,
                  expected_concepts, rubric, role_tags, source, quality_status, created_at
    """
    row = (await db.execute(text(q), {
        "domain_code": body.domain_code.upper(),
        "subcategory": body.subcategory,
        "difficulty": body.difficulty,
        "title": body.title,
        "body": body.body,
        "expected_concepts": body.expected_concepts,
        "rubric": body.rubric,
        "role_tags": body.role_tags,
        "source": body.source,
    })).mappings().first()
    await db.commit()
    return dict(row)
