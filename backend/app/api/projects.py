from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional
import uuid

from backend.app.dependencies import get_db_session, get_current_candidate
from backend.app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse
from backend.app.schemas.common import PaginatedResponse

router = APIRouter(tags=['projects'])

@router.post("/projects", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session)
):
    project_id = str(uuid.uuid4())
    query = text("""
        INSERT INTO candidate_projects (id, candidate_id, name, summary, business_value, tech_stack, verified_by_user)
        VALUES (:id, :candidate_id, :name, :summary, :business_value, :tech_stack, true)
        RETURNING id, candidate_id, name, summary, business_value, tech_stack, verified_by_user, created_at, updated_at
    """)
    values = project_data.model_dump()
    values.update({"id": project_id, "candidate_id": candidate["id"]})
    
    result = await db.execute(query, values)
    row = result.fetchone()
    await db.commit()
    return dict(row._mapping)

@router.get("/projects", response_model=PaginatedResponse[ProjectResponse])
async def list_projects(
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
        SELECT id, candidate_id, name, summary, business_value, tech_stack, verified_by_user, created_at, updated_at
        FROM candidate_projects
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

@router.get("/projects/{id}", response_model=ProjectResponse)
async def get_project(
    id: uuid.UUID,
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session)
):
    query = text("SELECT * FROM candidate_projects WHERE id = :id AND candidate_id = :candidate_id")
    result = await db.execute(query, {"id": str(id), "candidate_id": candidate["id"]})
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Project not found")
    return dict(row._mapping)

@router.patch("/projects/{id}", response_model=ProjectResponse)
async def update_project(
    id: uuid.UUID,
    update_data: ProjectUpdate,
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session)
):
    update_dict = update_data.model_dump(exclude_unset=True)
    if not update_dict:
        return await get_project(id, candidate, db)
        
    set_clauses = []
    values = {"id": str(id), "candidate_id": candidate["id"]}
    
    for key, value in update_dict.items():
        set_clauses.append(f"{key} = :{key}")
        values[key] = value
        
    set_clauses.append("updated_at = NOW()")
    
    query = text(f"""
        UPDATE candidate_projects
        SET {', '.join(set_clauses)}
        WHERE id = :id AND candidate_id = :candidate_id
        RETURNING *
    """)
    result = await db.execute(query, values)
    row = result.fetchone()
    await db.commit()
    
    if not row:
        raise HTTPException(status_code=404, detail="Project not found")
    return dict(row._mapping)

@router.delete("/projects/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    id: uuid.UUID,
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session)
):
    query = text("DELETE FROM candidate_projects WHERE id = :id AND candidate_id = :candidate_id RETURNING id")
    result = await db.execute(query, {"id": str(id), "candidate_id": candidate["id"]})
    row = result.fetchone()
    await db.commit()
    
    if not row:
        raise HTTPException(status_code=404, detail="Project not found")

