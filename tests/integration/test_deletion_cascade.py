import os
import psycopg2
import pytest
import uuid
import json

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://praxis@localhost:5432/praxis")

@pytest.fixture
def db_conn():
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    yield conn
    conn.close()

def test_full_deletion_cascade(db_conn):
    cur = db_conn.cursor()
    
    # 1. Setup - Create two users
    user_a = str(uuid.uuid4())
    user_b = str(uuid.uuid4())
    
    cur.execute("INSERT INTO auth.users (id) VALUES (%s) ON CONFLICT DO NOTHING", (user_a,))
    cur.execute("INSERT INTO profiles (id) VALUES (%s) ON CONFLICT DO NOTHING", (user_a,))
    cur.execute("INSERT INTO auth.users (id) VALUES (%s) ON CONFLICT DO NOTHING", (user_b,))
    cur.execute("INSERT INTO profiles (id) VALUES (%s) ON CONFLICT DO NOTHING", (user_b,))

    # User A's data graph
    cand_a = str(uuid.uuid4())
    cur.execute("INSERT INTO candidates (id, profile_id, full_name) VALUES (%s, %s, 'User A')", (cand_a, user_a))
    
    # User B's data graph
    cand_b = str(uuid.uuid4())
    cur.execute("INSERT INTO candidates (id, profile_id, full_name) VALUES (%s, %s, 'User B')", (cand_b, user_b))
    
    # User A has a project, document, and chunk
    proj_a = str(uuid.uuid4())
    cur.execute("INSERT INTO candidate_projects (id, candidate_id, name) VALUES (%s, %s, 'Project A')", (proj_a, cand_a))
    
    doc_a = str(uuid.uuid4())
    cur.execute("INSERT INTO documents (id, candidate_id, kind) VALUES (%s, %s, 'other')", (doc_a, cand_a))
    
    chunk_a = str(uuid.uuid4())
    cur.execute("INSERT INTO document_chunks (id, document_id, chunk_index, content, embedding_model, embedding_version) VALUES (%s, %s, 1, 'Chunk A', 'test', '1.0')", (chunk_a, doc_a))
    
    # User B has a session, and a claim referencing User A's chunk
    # (In a real system, cross-candidate references shouldn't happen, but we want to ensure SET NULL safety if it does, preventing a cascade failure)
    job_b = str(uuid.uuid4())
    cur.execute("INSERT INTO jobs (id, candidate_id, company_name, role_title) VALUES (%s, %s, 'Acme', 'Engineer')", (job_b, cand_b))
    
    session_b = str(uuid.uuid4())
    cur.execute("INSERT INTO practice_sessions (id, candidate_id, job_id, mode, interview_type) VALUES (%s, %s, %s, 'drill', 'behavioral')", (session_b, cand_b, job_b))
    
    turn_b = str(uuid.uuid4())
    cur.execute("INSERT INTO session_turns (id, session_id, turn_index, speaker, text) VALUES (%s, %s, 1, 'candidate', 'Hello')", (turn_b, session_b))

    claim_b = str(uuid.uuid4())
    cur.execute("INSERT INTO session_claims (id, session_id, turn_id, claim_text, source_chunk_id) VALUES (%s, %s, %s, 'Claim B', %s)", (claim_b, session_b, turn_b, chunk_a))

    # User A has their own session
    session_a = str(uuid.uuid4())
    cur.execute("INSERT INTO practice_sessions (id, candidate_id, mode, interview_type) VALUES (%s, %s, 'drill', 'behavioral')", (session_a, cand_a))
    turn_a = str(uuid.uuid4())
    cur.execute("INSERT INTO session_turns (id, session_id, turn_index, speaker, text) VALUES (%s, %s, 1, 'candidate', 'Hello')", (turn_a, session_a))
    
    # 2. Add a deletion job
    job_id = str(uuid.uuid4())
    cur.execute("INSERT INTO deletion_jobs (id, profile_id, candidate_id, status) VALUES (%s, %s, %s, 'pending')", (job_id, user_a, cand_a))

    # 3. Simulate the Worker Job Contract (Delete database rows)
    # The actual arq job would also wipe storage, but we are just simulating the DB wipe
    
    # Explicitly verify rows exist before delete
    cur.execute("SELECT count(*) FROM candidates WHERE id = %s", (cand_a,))
    assert cur.fetchone()[0] == 1
    cur.execute("SELECT count(*) FROM session_turns WHERE session_id = %s", (session_a,))
    assert cur.fetchone()[0] == 1
    
    # Run candidate deletion
    try:
        cur.execute("DELETE FROM candidates WHERE id = %s", (cand_a,))
        
        cur.execute("UPDATE deletion_jobs SET status = 'completed', completed_at = now(), rows_deleted_summary = %s WHERE id = %s", 
                    (json.dumps({"candidates": 1}), job_id))
    except Exception as e:
        cur.execute("UPDATE deletion_jobs SET status = 'failed', error_message = %s WHERE id = %s", 
                    (str(e), job_id))
        raise

    # 4. Assert User A's data is wiped completely via cascade
    cur.execute("SELECT count(*) FROM candidates WHERE id = %s", (cand_a,))
    assert cur.fetchone()[0] == 0, "Candidate A not deleted"
    
    cur.execute("SELECT count(*) FROM candidate_projects WHERE candidate_id = %s", (cand_a,))
    assert cur.fetchone()[0] == 0, "Candidate A's projects not cascaded"
    
    cur.execute("SELECT count(*) FROM practice_sessions WHERE candidate_id = %s", (cand_a,))
    assert cur.fetchone()[0] == 0, "Candidate A's sessions not cascaded"
    
    cur.execute("SELECT count(*) FROM session_turns WHERE session_id = %s", (session_a,))
    assert cur.fetchone()[0] == 0, "Candidate A's session turns not cascaded"
    
    cur.execute("SELECT count(*) FROM documents WHERE candidate_id = %s", (cand_a,))
    assert cur.fetchone()[0] == 0, "Candidate A's documents not cascaded"

    # 5. Assert User B's data remains intact
    cur.execute("SELECT count(*) FROM candidates WHERE id = %s", (cand_b,))
    assert cur.fetchone()[0] == 1, "Candidate B was accidentally deleted"

    # 6. CRITICAL: Confirm the cross-candidate reference was cleanly SET NULL, 
    # instead of aborting the cascade or deleting the claim!
    cur.execute("SELECT source_chunk_id FROM session_claims WHERE id = %s", (claim_b,))
    res = cur.fetchone()
    assert res is not None, "Claim B was accidentally cascaded"
    assert res[0] is None, "source_chunk_id was not set to NULL! FK constraint broken."

    print("SUCCESS: Full deletion cascade round-tripped perfectly, including cross-candidate SET NULL edge case.")

def test_real_deletion_job(db_conn):
    import asyncio
    from sqlalchemy.ext.asyncio import create_async_engine
    from backend.app.worker_tasks import delete_candidate_account_job
    
    async def run_test():
        engine = create_async_engine(DATABASE_URL.replace('postgresql://', 'postgresql+asyncpg://'))
        ctx = {'db_engine': engine}
        
        user_id = str(uuid.uuid4())
        cand_id = str(uuid.uuid4())
        job_id = str(uuid.uuid4())
        
        cur = db_conn.cursor()
        cur.execute("INSERT INTO auth.users (id) VALUES (%s) ON CONFLICT DO NOTHING", (user_id,))
        cur.execute("INSERT INTO profiles (id) VALUES (%s) ON CONFLICT DO NOTHING", (user_id,))
        cur.execute("INSERT INTO candidates (id, profile_id, full_name) VALUES (%s, %s, 'Test')", (cand_id, user_id))
        cur.execute("INSERT INTO deletion_jobs (id, profile_id, candidate_id, status) VALUES (%s, %s, %s, 'pending')", (job_id, user_id, cand_id))
        
        await delete_candidate_account_job(ctx, deletion_job_id=job_id, candidate_id=cand_id)
        
        cur.execute("SELECT status FROM deletion_jobs WHERE id = %s", (job_id,))
        status = cur.fetchone()[0]
        assert status == 'completed', f"Expected completed, got {status}"
        
        cur.execute("SELECT count(*) FROM candidates WHERE id = %s", (cand_id,))
        assert cur.fetchone()[0] == 0, "Candidate was not deleted"
        
    asyncio.run(run_test())
