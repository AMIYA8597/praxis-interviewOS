import asyncio
import os
import uuid
import datetime
from sqlalchemy.ext.asyncio import create_async_engine
from backend.app.worker_tasks import process_resume, analyze_job, cleanup_old_sessions
from sqlalchemy import text
from praxis_ai_gateway.providers.ollama import OllamaProvider

async def main():
    db_url = os.environ.get("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/praxis")
    engine = create_async_engine(db_url)
    
    ctx = {
        'db_engine': engine,
        'providers': {"ollama": OllamaProvider()}
    }
    
    async with engine.begin() as conn:
        # 1. Setup a fake candidate
        user_id = uuid.uuid4()
        await conn.execute(text("""
            INSERT INTO candidates (profile_id, first_name, last_name, primary_email)
            VALUES (:uid, 'Test', 'Candidate', 'test@test.com')
        """), {"uid": user_id})
        
        await conn.execute(text("""
            INSERT INTO user_settings (profile_id, data_retention_days)
            VALUES (:uid, 30)
        """), {"uid": user_id})
        
        # 2. Setup a fake document
        doc_id = uuid.uuid4()
        await conn.execute(text("""
            INSERT INTO documents (id, candidate_id, filename, file_type, storage_path, processing_status)
            VALUES (:did, :uid, 'test.txt', 'text/plain', 'test/test.txt', 'pending')
        """), {"did": doc_id, "uid": user_id})
        
        # We need a fake file in storage
        from backend.storage.local import get_object_storage
        storage = get_object_storage()
        
        content = "Resume of Test Candidate\nSkills: Python, TypeScript, Postgres\nProjects: Built a realtime AI agent"
        await storage.put('test/test.txt', content.encode('utf-8'), 'text/plain')
        
    print(f"Testing process_resume for doc {doc_id}...")
    await process_resume(ctx, str(doc_id))
    
    async with engine.begin() as conn:
        status = await conn.execute(text("SELECT processing_status FROM documents WHERE id = :did"), {"did": doc_id})
        print("Document status:", status.scalar())
        
        skills = await conn.execute(text("SELECT name FROM candidate_skills WHERE candidate_id = :uid"), {"uid": user_id})
        print("Extracted skills:", [row[0] for row in skills.fetchall()])
        
        chunks = await conn.execute(text("SELECT chunk_index FROM document_chunks WHERE document_id = :did"), {"did": doc_id})
        print("Chunks embedded:", len(chunks.fetchall()))
        
    # 3. Test cleanup_old_sessions
    print("Testing cleanup_old_sessions...")
    async with engine.begin() as conn:
        sess_id = uuid.uuid4()
        await conn.execute(text("""
            INSERT INTO practice_sessions (id, candidate_id, job_id, status)
            VALUES (:sid, :uid, NULL, 'active')
        """), {"sid": sess_id, "uid": user_id})
        
        await conn.execute(text("""
            INSERT INTO session_state_log (session_id, from_state, to_state, occurred_at)
            VALUES (:sid, 'IDLE', 'READY', NOW() - INTERVAL '3 hours')
        """), {"sid": sess_id})
        
    await cleanup_old_sessions(ctx)
    
    async with engine.begin() as conn:
        status = await conn.execute(text("SELECT status FROM practice_sessions WHERE id = :sid"), {"sid": sess_id})
        print("Session status after cleanup:", status.scalar())

if __name__ == "__main__":
    asyncio.run(main())
