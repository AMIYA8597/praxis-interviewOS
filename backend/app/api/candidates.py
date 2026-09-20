from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from backend.app.dependencies import get_db_session, get_current_candidate
from backend.app.schemas.candidate import CandidateResponse, CandidateUpdate

router = APIRouter(tags=['candidates'])

@router.get("/candidates/me", response_model=CandidateResponse)
async def get_me(
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session)
):
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
        
    query = text("SELECT id, profile_id, full_name, headline, target_roles, preferred_language, speaking_style, created_at, updated_at FROM candidates WHERE id = :id")
    result = await db.execute(query, {"id": candidate["id"]})
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Candidate not found")
        
    return dict(row._mapping)

@router.patch("/candidates/me", response_model=CandidateResponse)
async def update_me(
    update_data: CandidateUpdate,
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session)
):
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
        
    update_dict = update_data.model_dump(exclude_unset=True)
    if not update_dict:
        return await get_me(candidate, db)
        
    set_clauses = []
    values = {"id": candidate["id"]}
    
    for key, value in update_dict.items():
        set_clauses.append(f"{key} = :{key}")
        values[key] = value
        
    set_clauses.append("updated_at = NOW()")
    
    query_str = f"UPDATE candidates SET {', '.join(set_clauses)} WHERE id = :id RETURNING id, profile_id, full_name, headline, target_roles, preferred_language, speaking_style, created_at, updated_at"
    
    result = await db.execute(text(query_str), values)
    row = result.fetchone()
    await db.commit()
    
    if not row:
        raise HTTPException(status_code=404, detail="Candidate not found")
        
    return dict(row._mapping)

