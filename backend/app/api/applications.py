from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from backend.app.dependencies import get_current_candidate, get_db_session

router = APIRouter(tags=["applications"])

class ApplicationCreate(BaseModel):
    company: str
    role: str
    source: Optional[str] = None
    status: str = "applied"
    recruiter: Optional[str] = None
    interview_round: Optional[str] = None
    next_action: Optional[str] = None
    notes: Optional[str] = None

class ApplicationUpdate(BaseModel):
    company: Optional[str] = None
    role: Optional[str] = None
    source: Optional[str] = None
    status: Optional[str] = None
    recruiter: Optional[str] = None
    interview_round: Optional[str] = None
    next_action: Optional[str] = None
    notes: Optional[str] = None

@router.get("/applications")
async def list_applications(
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session)
):
    query = text("""
        SELECT id, company, role, source, status, recruiter, interview_round, next_action, notes, created_at, updated_at
        FROM applications
        WHERE candidate_id = :cid AND deleted_at IS NULL
        ORDER BY created_at DESC
    """)
    res = await db.execute(query, {"cid": candidate["id"]})
    return {"applications": [dict(r._mapping) for r in res.fetchall()]}

@router.post("/applications")
async def create_application(
    req: ApplicationCreate, 
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session)
):
    query = text("""
        INSERT INTO applications (candidate_id, company, role, source, status, recruiter, interview_round, next_action, notes)
        VALUES (:cid, :company, :role, :source, :status, :recruiter, :interview_round, :next_action, :notes)
        RETURNING id
    """)
    res = await db.execute(query, {
        "cid": candidate["id"],
        "company": req.company,
        "role": req.role,
        "source": req.source,
        "status": req.status,
        "recruiter": req.recruiter,
        "interview_round": req.interview_round,
        "next_action": req.next_action,
        "notes": req.notes
    })
    await db.commit()
    row = res.fetchone()
    return {"status": "created", "id": str(row[0])}

@router.patch("/applications/{app_id}")
async def update_application(
    app_id: str,
    req: ApplicationUpdate, 
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session)
):
    # Verify ownership
    check = text("SELECT id FROM applications WHERE id = :id AND candidate_id = :cid")
    if not (await db.execute(check, {"id": app_id, "cid": candidate["id"]})).fetchone():
        raise HTTPException(status_code=404, detail="Application not found")
        
    update_fields = req.model_dump(exclude_unset=True)
    if not update_fields:
        return {"status": "updated", "id": app_id}
        
    set_clause = ", ".join([f"{k} = :{k}" for k in update_fields.keys()])
    query = text(f"UPDATE applications SET {set_clause} WHERE id = :id AND candidate_id = :cid")
    update_fields["id"] = app_id
    update_fields["cid"] = candidate["id"]
    
    await db.execute(query, update_fields)
    await db.commit()
    
    return {"status": "updated", "id": app_id}

@router.delete("/applications/{app_id}")
async def delete_application(
    app_id: str,
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session)
):
    query = text("UPDATE applications SET deleted_at = now() WHERE id = :id AND candidate_id = :cid")
    res = await db.execute(query, {"id": app_id, "cid": candidate["id"]})
    if res.rowcount == 0:
        raise HTTPException(status_code=404, detail="Application not found")
    await db.commit()
    return {"status": "deleted"}
