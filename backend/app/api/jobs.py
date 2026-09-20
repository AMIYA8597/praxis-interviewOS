from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional
import uuid

from backend.app.dependencies import get_db_session, get_current_candidate
from backend.app.schemas.job import JobCreate, JobResponse
from backend.app.schemas.common import PaginatedResponse

router = APIRouter(tags=['jobs'])

@router.post("/jobs", status_code=status.HTTP_202_ACCEPTED)
async def create_job(
    request: Request,
    job_data: JobCreate,
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session)
):
    job_id = str(uuid.uuid4())
    query = text("""
        INSERT INTO jobs (id, candidate_id, company, role_title, description, processing_status)
        VALUES (:id, :candidate_id, :company, :role_title, :description, 'analyzing')
        RETURNING id
    """)
    values = job_data.model_dump()
    values.update({"id": job_id, "candidate_id": candidate["id"]})
    
    await db.execute(query, values)
    await db.commit()
    
    # Enqueue analysis job
    from opentelemetry.propagate import inject
    trace_carrier = {}
    inject(trace_carrier)
    
    if hasattr(request.app.state, 'arq_pool'):
        await request.app.state.arq_pool.enqueue_job("analyze_job", job_id, trace_carrier)
    
    return {"id": job_id, "status": "analyzing", "message": "Job accepted for analysis"}

@router.get("/jobs", response_model=PaginatedResponse[JobResponse])
async def list_jobs(
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
        SELECT id, candidate_id, company, role_title, processing_status, created_at
        FROM jobs
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

@router.get("/jobs/{id}", response_model=dict)
async def get_job(
    id: uuid.UUID,
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session)
):
    query = text("""
        SELECT id, candidate_id, company, role_title, processing_status, created_at
        FROM jobs WHERE id = :id AND candidate_id = :candidate_id
    """)
    result = await db.execute(query, {"id": str(id), "candidate_id": candidate["id"]})
    row = result.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Job not found")
        
    job_data = dict(row._mapping)
    
    # Fetch nested job_blueprints
    bp_query = text("SELECT id, summary, competency_dimensions FROM job_blueprints WHERE job_id = :id")
    bp_result = await db.execute(bp_query, {"id": str(id)})
    blueprints = [dict(r._mapping) for r in bp_result.fetchall()]
    job_data["blueprints"] = blueprints
    
    # Fetch nested matches
    match_query = text("SELECT id, match_score, match_rationale, missing_competencies FROM job_matches WHERE job_id = :id")
    match_result = await db.execute(match_query, {"id": str(id)})
    matches = [dict(r._mapping) for r in match_result.fetchall()]
    job_data["matches"] = matches
    
    return job_data

