from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import List
import uuid

from backend.app.dependencies import get_db_session, get_current_candidate, get_object_storage, get_redis
from backend.app.schemas.resume import ResumeResponse, ResumeFactResponse, ResumeFactUpdate
from redis.asyncio import Redis

router = APIRouter(tags=['resumes'])

ALLOWED_MIMES = ["application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]

@router.post("/resumes", status_code=status.HTTP_202_ACCEPTED)
async def upload_resume(
    request: Request,
    file: UploadFile = File(...),
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis)
):
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
        
    if file.content_type not in ALLOWED_MIMES:
        raise HTTPException(status_code=400, detail="Unsupported file type")
        
    # Validation of magic bytes + size would happen here
    # Store via get_object_storage
    # Object storage and magic byte validation would be strictly implemented with the real backend.
    
    document_id = str(uuid.uuid4())
    resume_id = str(uuid.uuid4())
    
    # 1. Insert documents row
    doc_query = text("INSERT INTO documents (id, profile_id, filename, content_type, size_bytes, processing_status) VALUES (:id, :profile_id, :filename, :content_type, :size, 'uploading') RETURNING id")
    await db.execute(doc_query, {"id": document_id, "profile_id": candidate.get("user_id", "")[:36], "filename": file.filename, "content_type": file.content_type, "size": 0})
    
    # 2. Insert resumes row
    res_query = text("INSERT INTO resumes (id, candidate_id, document_id, is_active) VALUES (:id, :candidate_id, :document_id, true) RETURNING id")
    await db.execute(res_query, {"id": resume_id, "candidate_id": candidate["id"], "document_id": document_id})
    await db.commit()
    
    # 3. Enqueue the arq job
    from opentelemetry.propagate import inject
    trace_carrier = {}
    inject(trace_carrier)
    
    if hasattr(request.app.state, 'arq_pool'):
        await request.app.state.arq_pool.enqueue_job("process_resume", document_id, trace_carrier)
    
    return {"id": resume_id, "status": "uploading", "message": "Resume accepted for processing"}

@router.get("/resumes/{id}", response_model=dict)
async def get_resume_status(
    id: uuid.UUID,
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session)
):
    if not candidate:
        raise HTTPException(status_code=404, detail="Not found")
        
    query = text("""
        SELECT r.id, d.processing_status 
        FROM resumes r
        JOIN documents d ON r.document_id = d.id
        WHERE r.id = :id AND r.candidate_id = :candidate_id
    """)
    result = await db.execute(query, {"id": str(id), "candidate_id": candidate["id"]})
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
        
    return {"id": row[0], "processing_status": row[1]}

@router.get("/resumes/{id}/facts", response_model=List[ResumeFactResponse])
async def get_resume_facts(
    id: uuid.UUID,
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session)
):
    if not candidate:
        raise HTTPException(status_code=404, detail="Not found")
        
    # Verify ownership
    check = await db.execute(text("SELECT id FROM resumes WHERE id = :id AND candidate_id = :candidate_id"), {"id": str(id), "candidate_id": candidate["id"]})
    if not check.fetchone():
        raise HTTPException(status_code=404, detail="Not found")
        
    query = text("SELECT id, fact_type, content, verified_by_user FROM resume_facts WHERE resume_id = :id ORDER BY created_at ASC")
    result = await db.execute(query, {"id": str(id)})
    return [dict(r._mapping) for r in result.fetchall()]

@router.post("/resumes/{id}/facts/{fact_id}/confirm", response_model=ResumeFactResponse)
async def confirm_resume_fact(
    id: uuid.UUID,
    fact_id: uuid.UUID,
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session)
):
    if not candidate:
        raise HTTPException(status_code=404, detail="Not found")
        
    query = text("""
        UPDATE resume_facts rf
        SET verified_by_user = true
        FROM resumes r
        WHERE rf.resume_id = r.id AND rf.id = :fact_id AND r.id = :resume_id AND r.candidate_id = :candidate_id
        RETURNING rf.id, rf.fact_type, rf.content, rf.verified_by_user
    """)
    result = await db.execute(query, {"fact_id": str(fact_id), "resume_id": str(id), "candidate_id": candidate["id"]})
    row = result.fetchone()
    await db.commit()
    
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
        
    return dict(row._mapping)

@router.post("/resumes/{id}/facts/{fact_id}/reject", status_code=status.HTTP_204_NO_CONTENT)
async def reject_resume_fact(
    id: uuid.UUID,
    fact_id: uuid.UUID,
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session)
):
    if not candidate:
        raise HTTPException(status_code=404, detail="Not found")
        
    query = text("""
        DELETE FROM resume_facts rf
        USING resumes r
        WHERE rf.resume_id = r.id AND rf.id = :fact_id AND r.id = :resume_id AND r.candidate_id = :candidate_id
        RETURNING rf.id
    """)
    result = await db.execute(query, {"fact_id": str(fact_id), "resume_id": str(id), "candidate_id": candidate["id"]})
    row = result.fetchone()
    await db.commit()
    
    if not row:
        raise HTTPException(status_code=404, detail="Not found")

@router.patch("/resumes/{id}/facts/{fact_id}", response_model=ResumeFactResponse)
async def update_resume_fact(
    id: uuid.UUID,
    fact_id: uuid.UUID,
    update_data: ResumeFactUpdate,
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session)
):
    if not candidate:
        raise HTTPException(status_code=404, detail="Not found")
        
    query = text("""
        UPDATE resume_facts rf
        SET content = :content, verified_by_user = true
        FROM resumes r
        WHERE rf.resume_id = r.id AND rf.id = :fact_id AND r.id = :resume_id AND r.candidate_id = :candidate_id
        RETURNING rf.id, rf.fact_type, rf.content, rf.verified_by_user
    """)
    result = await db.execute(query, {
        "content": update_data.content,
        "fact_id": str(fact_id),
        "resume_id": str(id),
        "candidate_id": candidate["id"]
    })
    row = result.fetchone()
    await db.commit()
    
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
        
    return dict(row._mapping)

