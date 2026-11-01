import asyncio
import uuid
from sqlalchemy.ext.asyncio import create_async_engine
from backend.app.worker_tasks import process_resume, cleanup_old_sessions
from sqlalchemy import text
from packages.config.settings import settings
from backend.app.core.storage import get_storage_client

async def main():
    db_url = settings.async_database_url
    engine = create_async_engine(db_url)
    storage = get_storage_client()

    ctx = {
        'db_engine': engine,
        'admin_db_engine': engine,
        'storage': storage,
        'providers': {},
    }

    async with engine.begin() as conn:
        profile_id = uuid.uuid4()
        candidate_id = uuid.uuid4()
        doc_id = uuid.uuid4()
        resume_id = uuid.uuid4()

        await conn.execute(text("INSERT INTO auth.users (id) VALUES (:pid)"), {"pid": profile_id})
        await conn.execute(text("INSERT INTO profiles (id) VALUES (:pid)"), {"pid": profile_id})
        await conn.execute(text("""
            INSERT INTO candidates (id, profile_id, full_name, headline)
            VALUES (:cid, :pid, 'Test Candidate', 'Senior Backend Engineer')
        """), {"cid": candidate_id, "pid": profile_id})

        await conn.execute(text("""
            INSERT INTO user_settings (id, candidate_id, data_retention_days)
            VALUES (gen_random_uuid(), :cid, 30)
        """), {"cid": candidate_id})

        storage_path = f"resumes/{candidate_id}/{doc_id}.txt"
        await conn.execute(text("""
            INSERT INTO documents (id, candidate_id, kind, original_filename, storage_path, mime_type, processing_status)
            VALUES (:did, :cid, 'resume', 'resume.txt', :path, 'text/plain', 'uploading')
        """), {"did": doc_id, "cid": candidate_id, "path": storage_path})

        await conn.execute(text("""
            INSERT INTO resumes (id, candidate_id, document_id, is_primary)
            VALUES (:rid, :cid, :did, true)
        """), {"rid": resume_id, "cid": candidate_id, "did": doc_id})

        content = "Resume of Test Candidate\nSkills: Python, TypeScript, Postgres, Distributed Systems\nProjects: Built a realtime AI agent"
        await storage.put(storage_path, content.encode('utf-8'), 'text/plain')

    print(f"Testing process_resume for doc {doc_id}...")
    res = await process_resume(ctx, str(doc_id))
    print(f"process_resume result: {res}")

    async with engine.begin() as conn:
        status = await conn.execute(text("SELECT processing_status FROM documents WHERE id = :did"), {"did": doc_id})
        print("Document status:", status.scalar())

        chunks = await conn.execute(text("SELECT chunk_index, content FROM document_chunks WHERE document_id = :did"), {"did": doc_id})
        chunk_rows = chunks.fetchall()
        print("Chunks stored:", len(chunk_rows))
        for row in chunk_rows:
            print(f"  Chunk {row[0]}: {row[1][:60]}...")

    # 2. Test cleanup_old_sessions
    print("\nTesting cleanup_old_sessions...")
    async with engine.begin() as conn:
        sess_id = uuid.uuid4()
        await conn.execute(text("""
            INSERT INTO practice_sessions (id, candidate_id, job_id, status, mode, interview_type)
            VALUES (:sid, :cid, NULL, 'active', 'mock_interview', 'technical')
        """), {"sid": sess_id, "cid": candidate_id})

    await cleanup_old_sessions(ctx)
    print("cleanup_old_sessions completed successfully.")

    await engine.dispose()
    print("\nAll worker tasks tested successfully!")

if __name__ == "__main__":
    asyncio.run(main())
