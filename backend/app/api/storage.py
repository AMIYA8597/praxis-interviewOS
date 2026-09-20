from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from backend.app.dependencies import get_db_session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

router = APIRouter(prefix="/storage", tags=["storage"])

class UploadResponse(BaseModel):
    document_id: str
    storage_path: str
    status: str

@router.post("/resumes/upload", response_model=UploadResponse)
async def upload_resume(
    candidate_id: UUID = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db_session)
):
    """Upload resume to storage bucket"""
    # 1. Validate file type (PDF, DOCX only)
    allowed_types = ["application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid file type. Only PDF and DOCX are allowed.")
    
    # 2. Upload to Supabase storage (mocked logic for integration)
    # The actual integration would use supabase.storage.from_("resumes").upload(...)
    file_bytes = await file.read()
    
    # Check 5MB limit
    if len(file_bytes) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Max 5MB.")
        
    storage_path = f"{candidate_id}/resumes/{file.filename}"
    
    # 5. Create document record
    async with db.begin():
        res = await db.execute(text("""
            INSERT INTO documents (candidate_id, kind, original_filename, storage_path, mime_type, size_bytes, processing_status)
            VALUES (:cid, 'resume', :fname, :spath, :mtype, :size, 'uploading')
            RETURNING id
        """), {
            "cid": str(candidate_id),
            "fname": file.filename,
            "spath": storage_path,
            "mtype": file.content_type,
            "size": len(file_bytes)
        })
        doc_id = res.scalar()
        
    # 6. Enqueue processing job
    # (In a real implementation, we would call arq's enqueue_job here)
    
    return UploadResponse(
        document_id=str(doc_id),
        storage_path=storage_path,
        status="uploading"
    )

@router.get("/download")
async def get_signed_download_url(
    storage_path: str,
    expires_in: int = 3600
):
    """Generate signed URL for secure download"""
    # Placeholder for actual Supabase signed URL generation
    # supabase.storage.from_("resumes").create_signed_url(storage_path, expires_in)
    return {"url": f"https://mock-storage.interviewos.com/signed/{storage_path}?expires={expires_in}"}
