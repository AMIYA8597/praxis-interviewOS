"""Independent REST API Acceptance Client.

Demonstrates that an entirely independent external client (e.g. mobile app,
third-party CLI, or non-web consumer) can execute end-to-end candidate
workflows against PRAXIS purely through documented REST contracts without
importing any frontend libraries or frontend state management.
"""
import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool
from sqlalchemy import text

from backend.app.main import app
from backend.app.db.models import Base
from backend.app.dependencies import get_current_candidate, get_db_session


@pytest.mark.asyncio
async def test_independent_client_journey():
    # Setup isolated test database schema
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    candidate_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Create raw DDL tables that are queried with text()
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS interview_domains (
                id TEXT PRIMARY KEY,
                code TEXT UNIQUE,
                parent_code TEXT,
                category TEXT,
                label TEXT,
                description TEXT,
                sort_order INTEGER DEFAULT 0
            )
        """))
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS question_bank (
                id TEXT PRIMARY KEY,
                domain_code TEXT,
                subcategory TEXT,
                difficulty TEXT,
                title TEXT,
                body TEXT,
                expected_concepts TEXT,
                rubric TEXT,
                role_tags TEXT,
                source TEXT,
                quality_status TEXT DEFAULT 'approved',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        # Seed candidate record
        await conn.execute(
            text("""
                INSERT INTO candidates (id, profile_id, full_name, headline)
                VALUES (:cid, :uid, 'Jordan Lee', 'Staff Infrastructure Engineer')
            """),
            {"cid": candidate_id, "uid": user_id},
        )
        # Seed test study card
        await conn.execute(
            text("""
                INSERT INTO study_items (id, candidate_id, topic, source, prompt, reference_answer, difficulty)
                VALUES (:sid, :cid, 'Distributed Systems', 'manual', 'Explain Raft consensus', 'Leader election + log replication', 'hard')
            """),
            {"sid": str(uuid.uuid4()), "cid": candidate_id},
        )

    async def _db():
        async with factory() as session:
            yield session

    # Wire HTTP dependencies
    app.dependency_overrides[get_current_candidate] = lambda: {"id": candidate_id, "user_id": user_id}
    app.dependency_overrides[get_db_session] = _db

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            headers = {"Authorization": "Bearer test-independent-token"}

            # 1. Health Probe
            resp = await client.get("/api/v1/health/live")
            assert resp.status_code == 200, f"Health check failed: {resp.text}"
            data = resp.json()
            assert data.get("status") in ("ok", "healthy", "up")

            # 2. Candidate Context
            resp = await client.get("/api/v1/candidates/me", headers=headers)
            assert resp.status_code in (200, 404)

            # 3. List Study Cards
            resp = await client.get("/api/v1/study/items", headers=headers)
            assert resp.status_code == 200, f"Study items retrieval failed: {resp.text}"
            items_data = resp.json()
            assert "items" in items_data
            assert len(items_data["items"]) >= 1
            assert items_data["items"][0]["topic"] == "Distributed Systems"

            # 4. List Questions
            resp = await client.get("/api/v1/questions", headers=headers)
            assert resp.status_code == 200

            # 5. Question Domains
            resp = await client.get("/api/v1/questions/domains", headers=headers)
            assert resp.status_code == 200

            # 6. Contract Error Model Check (Invalid UUID returns standard 422 JSON)
            resp = await client.get("/api/v1/questions/invalid-not-uuid", headers=headers)
            assert resp.status_code == 422
            err_json = resp.json()
            assert "detail" in err_json, "Error response does not follow standard OpenAPI detail schema"

    finally:
        app.dependency_overrides.clear()
        await engine.dispose()
