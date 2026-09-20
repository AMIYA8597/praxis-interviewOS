from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional, List
import uuid

from backend.app.dependencies import get_db_session, get_current_candidate
from backend.app.schemas.session import SessionCreate, SessionResponse
from backend.app.schemas.common import PaginatedResponse

router = APIRouter(tags=['sessions'])

@router.post("/sessions", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    session_data: SessionCreate,
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session)
):
    session_id = str(uuid.uuid4())
    from opentelemetry import trace
    span = trace.get_current_span()
    if span.is_recording():
        span.set_attribute("session_id", session_id)
        
    query = text("""
        INSERT INTO practice_sessions (id, candidate_id, job_id, status, focus_area)
        VALUES (:id, :candidate_id, :job_id, 'pending', :focus_area)
        RETURNING id, candidate_id, job_id, status, focus_area, started_at, ended_at
    """)
    values = session_data.model_dump()
    values.update({
        "id": session_id,
        "candidate_id": candidate["id"],
        "job_id": str(values["job_id"]) if values["job_id"] else None
    })
    
    result = await db.execute(query, values)
    row = result.fetchone()
    await db.commit()
    return dict(row._mapping)

@router.get("/sessions", response_model=PaginatedResponse[SessionResponse])
async def list_sessions(
    cursor: Optional[str] = Query(None, description="Cursor formatted as 'timestamp_uuid'"),
    limit: int = Query(20, ge=1, le=100),
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session)
):
    where_clause = "candidate_id = :candidate_id"
    params = {"candidate_id": candidate["id"], "limit": limit + 1}
    
    if cursor:
        try:
            ts_str, id_str = cursor.split("_", 1)
            params["cursor_ts"] = ts_str
            params["cursor_id"] = id_str
            where_clause += " AND (created_at, id) < (:cursor_ts::timestamptz, :cursor_id::uuid)"
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid cursor format")
            
    query = text(f"""
        SELECT id, candidate_id, job_id, status, focus_area, started_at, ended_at, created_at
        FROM practice_sessions
        WHERE {where_clause}
        ORDER BY created_at DESC, id DESC
        LIMIT :limit
    """)
    
    result = await db.execute(query, params)
    rows = result.fetchall()
    
    items = [dict(r._mapping) for r in rows]
    next_cursor = None
    
    if len(items) > limit:
        items = items[:limit]
        last_item = items[-1]
        next_cursor = f"{last_item['created_at'].isoformat()}_{last_item['id']}"
        
    return {"items": items, "next_cursor": next_cursor}

@router.get("/sessions/{id}", response_model=SessionResponse)
async def get_session(
    id: uuid.UUID,
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session)
):
    query = text("""
        SELECT id, candidate_id, job_id, status, focus_area, started_at, ended_at
        FROM practice_sessions WHERE id = :id AND candidate_id = :candidate_id
    """)
    result = await db.execute(query, {"id": str(id), "candidate_id": candidate["id"]})
    row = result.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")
        
    return dict(row._mapping)

@router.get("/sessions/{id}/turns")
async def get_session_turns(
    id: uuid.UUID,
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session)
):
    # Verify ownership
    check = await db.execute(text("SELECT id FROM practice_sessions WHERE id = :id AND candidate_id = :candidate_id"), {"id": str(id), "candidate_id": candidate["id"]})
    if not check.fetchone():
        raise HTTPException(status_code=404, detail="Session not found")
        
    query = text("SELECT id, turn_sequence, role, content_text, duration_ms, created_at FROM session_turns WHERE session_id = :id ORDER BY turn_sequence ASC")
    result = await db.execute(query, {"id": str(id)})
    return [dict(r._mapping) for r in result.fetchall()]

@router.get("/sessions/{id}/debrief")
async def get_session_debrief(
    id: uuid.UUID,
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session)
):
    # Verify ownership
    check = await db.execute(text("SELECT id FROM practice_sessions WHERE id = :id AND candidate_id = :candidate_id"), {"id": str(id), "candidate_id": candidate["id"]})
    if not check.fetchone():
        raise HTTPException(status_code=404, detail="Session not found")
        
    query = text("SELECT id, headline_metrics, strengths, weaknesses, flagged_claims, jd_coverage FROM session_debriefs WHERE session_id = :id")
    result = await db.execute(query, {"id": str(id)})
    row = result.fetchone()
    if not row:
        return {} # No debrief yet
        
    mapping = dict(row._mapping)
    # The API might be expecting the old schema structure on the frontend, but we should return what we have
    # Actually, returning the real columns is safer than trying to remap if they are completely different
    return mapping

