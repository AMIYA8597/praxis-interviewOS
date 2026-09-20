import pytest
import uuid
from sqlalchemy import text
from backend.app.worker_tasks import delete_candidate_account_job

@pytest.mark.asyncio
async def test_delete_candidate_account_job_status(db_engine):
    # Setup test data
    profile_id = str(uuid.uuid4())
    candidate_id = str(uuid.uuid4())
    job_id = str(uuid.uuid4())
    
    async with db_engine.begin() as conn:
        await conn.execute(text("""
            INSERT INTO candidates (id, profile_id, full_name, email)
            VALUES (:cid, :pid, 'Test Candidate', 'test@test.com')
        """), {"cid": candidate_id, "pid": profile_id})
        
        await conn.execute(text("""
            INSERT INTO deletion_jobs (id, profile_id, status)
            VALUES (:jid, :pid, 'pending')
        """), {"jid": job_id, "pid": profile_id})

    # Run the job
    ctx = {"db_engine": db_engine}
    await delete_candidate_account_job(ctx, job_id, candidate_id)

    # Check status
    async with db_engine.begin() as conn:
        res = await conn.execute(text("SELECT status FROM deletion_jobs WHERE id = :jid"), {"jid": job_id})
        row = res.fetchone()
        assert row is not None
        assert row[0] == 'completed'
