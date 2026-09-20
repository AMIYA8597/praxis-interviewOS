import pytest
import pytest_asyncio
import uuid
import os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql+asyncpg://praxis:dev_password@localhost:5432/praxis")

@pytest_asyncio.fixture(scope="function")
async def real_db_engine():
    engine = create_async_engine(DATABASE_URL, echo=False)
    
    try:
        async with engine.connect() as conn:
            pass
    except Exception as e:
        await engine.dispose()
        pytest.skip(f"Database not accessible, skipping real deletion job test: {e}")

    yield engine
        
    await engine.dispose()

@pytest.mark.asyncio
async def test_delete_candidate_account_job_status(real_db_engine):
    from backend.app.worker_tasks import delete_candidate_account_job

    profile_id = str(uuid.uuid4())
    candidate_id = str(uuid.uuid4())
    job_id = str(uuid.uuid4())
    
    async with real_db_engine.begin() as conn:
        try:
            await conn.execute(text("INSERT INTO auth.users (id) VALUES (:pid)"), {"pid": profile_id})
        except Exception:
            pass
        await conn.execute(text("INSERT INTO profiles (id) VALUES (:pid)"), {"pid": profile_id})
        
        await conn.execute(text("""
            INSERT INTO candidates (id, profile_id, full_name)
            VALUES (:cid, :pid, 'Test Candidate')
        """), {"cid": candidate_id, "pid": profile_id})
        
        await conn.execute(text("""
            INSERT INTO deletion_jobs (id, profile_id, status)
            VALUES (:jid, :pid, 'pending')
        """), {"jid": job_id, "pid": profile_id})

    ctx = {"db_engine": real_db_engine}
    await delete_candidate_account_job(ctx, job_id, candidate_id)

    async with real_db_engine.begin() as conn:
        res = await conn.execute(text("SELECT status FROM deletion_jobs WHERE id = :jid"), {"jid": job_id})
        row = res.fetchone()
        assert row is not None
        assert row[0] == 'completed', f"Expected 'completed', got '{row[0]}'"

        # Cleanup
        await conn.execute(text("DELETE FROM candidates WHERE id = :cid"), {"cid": candidate_id})
        await conn.execute(text("DELETE FROM profiles WHERE id = :pid"), {"pid": profile_id})
        try:
            await conn.execute(text("DELETE FROM auth.users WHERE id = :pid"), {"pid": profile_id})
        except Exception:
            pass
