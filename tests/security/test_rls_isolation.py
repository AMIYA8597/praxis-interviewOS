import os
import psycopg2
import pytest
import uuid

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://praxis@localhost:5432/praxis")

@pytest.fixture
def db_conn():
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    yield conn
    conn.close()

def set_auth_context(cur, user_id):
    """
    Simulates a Supabase authenticated request for a specific user ID.
    This sets the same variables that PostgREST sets before evaluating RLS.
    """
    cur.execute("SET ROLE authenticated;")
    cur.execute(f"SET request.jwt.claims TO '{{\"sub\": \"{user_id}\", \"role\": \"authenticated\"}}';")

def test_rls_cross_tenant_isolation(db_conn):
    cur = db_conn.cursor()
    
    # 1. Bypass RLS temporarily (as postgres superuser) to set up test users
    cur.execute("RESET ROLE;")
    
    user_a = str(uuid.uuid4())
    user_b = str(uuid.uuid4())
    
    # Insert users into auth.users and profiles (simulate signup)
    for u in [user_a, user_b]:
        cur.execute("INSERT INTO auth.users (id) VALUES (%s) ON CONFLICT DO NOTHING", (u,))
        cur.execute("INSERT INTO profiles (id) VALUES (%s) ON CONFLICT DO NOTHING", (u,))

    # 2. Build a realistic connected graph of data for User A
    cand_a = str(uuid.uuid4())
    cur.execute("INSERT INTO candidates (id, profile_id, full_name) VALUES (%s, %s, 'User A')", (cand_a, user_a))
    
    proj_a = str(uuid.uuid4())
    cur.execute("INSERT INTO candidate_projects (id, candidate_id, name) VALUES (%s, %s, 'Project A')", (proj_a, cand_a))
    
    doc_a = str(uuid.uuid4())
    cur.execute("INSERT INTO documents (id, candidate_id, kind) VALUES (%s, %s, 'other')", (doc_a, cand_a))
    
    cur.execute("INSERT INTO document_chunks (document_id, chunk_index, content, embedding_model, embedding_version) VALUES (%s, 1, 'Chunk A', 'test', '1.0')", (doc_a,))
    
    job_a = str(uuid.uuid4())
    cur.execute("INSERT INTO jobs (id, candidate_id, company_name, role_title) VALUES (%s, %s, 'Acme', 'Engineer')", (job_a, cand_a))
    
    session_a = str(uuid.uuid4())
    cur.execute("INSERT INTO practice_sessions (id, candidate_id, job_id, mode, interview_type, difficulty, status) VALUES (%s, %s, %s, 'drill', 'behavioral', 'warmup', 'active')", (session_a, cand_a, job_a))
    
    turn_a = str(uuid.uuid4())
    cur.execute("INSERT INTO session_turns (id, session_id, turn_index, speaker, text) VALUES (%s, %s, 1, 'candidate', 'Hello')", (turn_a, session_a))

    item_a = str(uuid.uuid4())
    cur.execute("INSERT INTO study_items (id, candidate_id, topic, source, prompt) VALUES (%s, %s, 'Topic A', 'manual', 'Prompt A')", (item_a, cand_a))

    # 3. Authenticate as User B
    set_auth_context(cur, user_b)
    
    # 4. Assert User B cannot SELECT User A's data
    cur.execute("SELECT count(*) FROM candidates WHERE id = %s", (cand_a,))
    assert cur.fetchone()[0] == 0, "User B could read User A's candidate profile!"
    
    cur.execute("SELECT count(*) FROM candidate_projects WHERE id = %s", (proj_a,))
    assert cur.fetchone()[0] == 0, "User B could read User A's project!"
    
    cur.execute("SELECT count(*) FROM practice_sessions WHERE id = %s", (session_a,))
    assert cur.fetchone()[0] == 0, "User B could read User A's session!"

    # Assert User B cannot UPDATE User A's data
    cur.execute("UPDATE candidate_projects SET name = 'Hacked' WHERE id = %s", (proj_a,))
    assert cur.rowcount == 0, "User B could update User A's project!"

    # Assert User B cannot DELETE User A's data
    cur.execute("DELETE FROM session_turns WHERE id = %s", (turn_a,))
    assert cur.rowcount == 0, "User B could delete User A's session turn!"

    # Assert User B cannot INSERT claiming User A's candidate_id
    with pytest.raises(psycopg2.errors.InsufficientPrivilege) as excinfo:
        cur.execute("INSERT INTO candidate_projects (candidate_id, name) VALUES (%s, 'Fake Project B')", (cand_a,))
    
    # 5. Authenticate as User A and confirm they CAN access their own data
    db_conn.rollback() # Clear the failed transaction state
    set_auth_context(cur, user_a)
    
    cur.execute("SELECT count(*) FROM candidates WHERE id = %s", (cand_a,))
    assert cur.fetchone()[0] == 1, "User A could NOT read their own candidate profile! RLS is broken."
    
    cur.execute("UPDATE candidate_projects SET name = 'Valid Update' WHERE id = %s", (proj_a,))
    assert cur.rowcount == 1, "User A could NOT update their own project!"
    
    print("All isolation assertions passed perfectly.")
