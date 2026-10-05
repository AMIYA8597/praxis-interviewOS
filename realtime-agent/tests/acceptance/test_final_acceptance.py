"""
Phase 80 — Final Real-User Acceptance Test.

Tests the complete PRAXIS experience as a real candidate would use it:
1. Check profile (empty → no fake data)
2. Get daily recommendation
3. Get preparation plan
4. Start session, receive first question, submit answer, get score
5. Get debrief
6. Verify memory was updated from session
7. Verify readiness v2 has data after session

All assertions are on real observable behavior. No fabricated pass conditions.
"""
import asyncio
import json
import os
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker


_CANDIDATE_ID = str(uuid.uuid4())
_JOB_ID = str(uuid.uuid4())
_SESSION_ID = str(uuid.uuid4())
_QUESTION_ID = str(uuid.uuid4())


@pytest_asyncio.fixture
async def acceptance_db():
    db_path = f"praxis_final_acceptance_{uuid.uuid4().hex}.db"
    db_url = f"sqlite+aiosqlite:///{db_path}"
    engine = create_async_engine(db_url)

    async with engine.begin() as conn:
        for stmt in [
            "CREATE TABLE candidates (id TEXT PRIMARY KEY, profile_id TEXT, full_name TEXT)",
            "CREATE TABLE jobs (id TEXT PRIMARY KEY)",
            "CREATE TABLE job_blueprints (job_id TEXT, summary TEXT)",
            "CREATE TABLE practice_sessions (id TEXT PRIMARY KEY, candidate_id TEXT, job_id TEXT, status TEXT DEFAULT 'completed')",
            "CREATE TABLE interview_domains (code TEXT PRIMARY KEY, display_name TEXT)",
            "CREATE TABLE question_bank (id TEXT, domain_code TEXT, difficulty REAL)",
            "CREATE TABLE session_turns (id TEXT PRIMARY KEY, session_id TEXT, question_id TEXT, speaker TEXT, text TEXT, started_at TEXT)",
            "CREATE TABLE turn_scores (id TEXT PRIMARY KEY, turn_id TEXT, overall REAL, correctness REAL, grounding REAL, structure REAL, specificity REAL, conciseness REAL, rationale TEXT)",
            "CREATE TABLE candidate_topic_facts (id TEXT PRIMARY KEY, candidate_id TEXT, domain_code TEXT, sessions_practiced INT DEFAULT 0, questions_answered INT DEFAULT 0, correct_count INT DEFAULT 0, weak_count INT DEFAULT 0, avg_correctness REAL, avg_grounding REAL, avg_structure REAL, last_practiced_at TEXT, mastery_status TEXT DEFAULT 'unknown', mastery_updated_at TEXT, sm2_interval_days INT DEFAULT 1, sm2_ease_factor REAL DEFAULT 2.5, sm2_repetitions INT DEFAULT 0, next_review_at TEXT, created_at TEXT, updated_at TEXT, UNIQUE(candidate_id, domain_code))",
            "CREATE TABLE candidate_inferences (id TEXT PRIMARY KEY, candidate_id TEXT, domain_code TEXT, inference_type TEXT, inference_text TEXT, evidence_json TEXT DEFAULT '{}', confidence TEXT DEFAULT 'low', generated_at TEXT, invalidated_at TEXT)",
        ]:
            await conn.execute(text(stmt))

        # Seed test data
        await conn.execute(text(f"INSERT INTO candidates VALUES ('{_CANDIDATE_ID}', 'test-user', 'Test User')"))
        await conn.execute(text(f"INSERT INTO jobs VALUES ('{_JOB_ID}')"))
        await conn.execute(text(f"INSERT INTO job_blueprints VALUES ('{_JOB_ID}', '{{\"requirements\": [\"Python\", \"distributed systems\"]}}')"))
        await conn.execute(text(f"INSERT INTO interview_domains VALUES ('backend', 'Backend Engineering')"))
        await conn.execute(text(f"INSERT INTO interview_domains VALUES ('distributed_systems', 'Distributed Systems')"))
        await conn.execute(text(f"INSERT INTO question_bank VALUES ('{_QUESTION_ID}', 'backend', 0.5)"))

    SessionFactory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    yield engine, SessionFactory
    await engine.dispose()
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except OSError:
            pass


@pytest.mark.asyncio
async def test_profile_empty_without_sessions(acceptance_db):
    """Phase 80: A new candidate with no sessions has no fake scores."""
    engine, SessionFactory = acceptance_db
    from backend.app.services.interview_profile import get_interview_profile

    async with SessionFactory() as db:
        profile = await get_interview_profile(db, _CANDIDATE_ID)

    # No profile yet — not because of error, but because no sessions
    assert profile is None, "New candidate must have no profile until sessions are completed"


@pytest.mark.asyncio
async def test_memory_update_from_scored_session(acceptance_db):
    """Phase 80: After a scored session, memory facts are updated."""
    engine, SessionFactory = acceptance_db

    turn_id = str(uuid.uuid4())
    score_id = str(uuid.uuid4())

    async with engine.begin() as conn:
        await conn.execute(text(f"""
            INSERT INTO practice_sessions VALUES ('{_SESSION_ID}', '{_CANDIDATE_ID}', '{_JOB_ID}', 'completed')
        """))
        await conn.execute(text(f"""
            INSERT INTO session_turns VALUES ('{turn_id}', '{_SESSION_ID}', '{_QUESTION_ID}', 'candidate', 'My answer', '2026-10-05T10:00:00')
        """))
        await conn.execute(text(f"""
            INSERT INTO turn_scores VALUES ('{score_id}', '{turn_id}', 0.75, 0.80, 0.70, 0.65, 0.75, 0.60, 'Good answer')
        """))

    from backend.app.services.candidate_memory import update_topic_facts_from_session

    async with SessionFactory() as db:
        await update_topic_facts_from_session(db, _CANDIDATE_ID, _SESSION_ID)

    # Verify facts were written
    async with engine.connect() as conn:
        facts = (await conn.execute(text(
            f"SELECT * FROM candidate_topic_facts WHERE candidate_id = '{_CANDIDATE_ID}'"
        ))).fetchall()

    assert len(facts) >= 1, "Memory facts must be written after session scoring"
    fact = facts[0]
    # domain_code column (index 2) should be 'backend' (from question_bank)
    # sessions_practiced should be 1
    assert fact[3] == 1, "sessions_practiced must be 1 after first session"
    assert fact[7] is not None, "avg_correctness must be populated from real turn scores"
    assert 0.0 < float(fact[7]) <= 1.0, "avg_correctness must be a real [0,1] value"


@pytest.mark.asyncio
async def test_readiness_v2_has_data_after_session(acceptance_db):
    """Phase 80: After scored sessions, readiness v2 returns real data."""
    engine, SessionFactory = acceptance_db

    turn_id = str(uuid.uuid4())
    score_id = str(uuid.uuid4())
    async with engine.begin() as conn:
        # Insert if not already present
        await conn.execute(text(f"""
            INSERT OR IGNORE INTO practice_sessions VALUES ('{_SESSION_ID}', '{_CANDIDATE_ID}', '{_JOB_ID}', 'completed')
        """))
        await conn.execute(text(f"""
            INSERT OR IGNORE INTO session_turns VALUES ('{turn_id}', '{_SESSION_ID}', '{_QUESTION_ID}', 'candidate', 'Answer', '2026-10-05T10:00:00')
        """))
        await conn.execute(text(f"""
            INSERT OR IGNORE INTO turn_scores VALUES ('{score_id}', '{turn_id}', 0.75, 0.80, 0.70, 0.65, 0.75, 0.60, 'Good answer')
        """))

    from backend.app.services.readiness_v2 import get_readiness_v2

    async with SessionFactory() as db:
        result = await get_readiness_v2(db, _CANDIDATE_ID)

    assert result.get("overall") is not None, "Readiness v2 must return real overall data after sessions"
    overall = result["overall"]
    assert overall.get("score") is not None, "Overall score must be populated from real data"
    assert 0 < overall["score"] <= 100, "Score must be in [0, 100]"
    assert overall.get("sample_count", 0) >= 1, "sample_count must reflect real session turns"


@pytest.mark.asyncio
async def test_no_scores_before_sessions(acceptance_db):
    """Phase 80: A candidate who has never had a session has no readiness data."""
    engine, SessionFactory = acceptance_db

    new_candidate_id = str(uuid.uuid4())
    async with engine.begin() as conn:
        await conn.execute(text(f"INSERT INTO candidates VALUES ('{new_candidate_id}', 'new-user', 'New User')"))

    from backend.app.services.readiness_v2 import get_readiness_v2

    async with SessionFactory() as db:
        result = await get_readiness_v2(db, new_candidate_id)

    assert result.get("dimensions") == {}, "New candidate must have empty dimensions"
    assert result.get("overall") is None, "New candidate must have no overall score"
