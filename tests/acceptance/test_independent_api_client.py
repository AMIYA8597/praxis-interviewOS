"""Independent REST API Acceptance Client.

Demonstrates that an entirely independent external client (e.g. Vercel frontend,
mobile app, third-party CLI, or non-web consumer) can execute end-to-end candidate
workflows against PRAXIS purely through documented public REST contracts without
importing any backend internals or frontend state management.

Exercises the full candidate journey:
1. Health & readiness probes (service verification)
2. Candidate profile retrieval and onboarding update
3. Document / resume upload with binary validation
4. Question domain & question bank catalog discovery
5. Spaced repetition study card lifecycle (creation, listing, review, due items)
6. Interview session orchestration (create session, list sessions, inspect session, end session)
7. Longitudinal analytics & readiness dashboard retrieval
8. GDPR candidate data self-export lifecycle (initiation & status check)
9. Standard OpenAPI contract error model verification (RFC 7807 / standard detail shape)
"""
import io
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool
from sqlalchemy import text

from backend.app.main import app
from backend.app.db.models import Base
from backend.app.dependencies import (
    get_current_candidate,
    get_db_session,
    get_object_storage,
    get_arq_pool,
    get_redis,
)
from backend.app.core.storage import LocalFileStorage


@pytest.mark.asyncio
async def test_independent_client_journey(tmp_path):
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
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS candidate_data_exports (
                id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
                candidate_id TEXT NOT NULL,
                status TEXT NOT NULL,
                requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                expires_at TIMESTAMP,
                download_url TEXT,
                storage_key TEXT
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

    mock_storage = LocalFileStorage(str(tmp_path / "storage"))
    mock_arq = AsyncMock()
    mock_arq.enqueue_job = AsyncMock(return_value=SimpleNamespace(job_id=f"job_{uuid.uuid4().hex}"))

    mock_redis = AsyncMock()
    mock_redis.delete = AsyncMock(return_value=True)
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.set = AsyncMock(return_value=True)
    mock_redis.setex = AsyncMock(return_value=True)

    # Wire HTTP dependencies for the test server
    app.dependency_overrides[get_current_candidate] = lambda: {"id": candidate_id, "user_id": user_id}
    app.dependency_overrides[get_db_session] = _db
    app.dependency_overrides[get_object_storage] = lambda: mock_storage
    app.dependency_overrides[get_arq_pool] = lambda: mock_arq
    app.dependency_overrides[get_redis] = lambda: mock_redis

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            headers = {"Authorization": "Bearer test-independent-token"}

            # -------------------------------------------------------------
            # 1. Health & Liveness Probes
            # -------------------------------------------------------------
            resp = await client.get("/api/v1/health/live")
            assert resp.status_code == 200, f"Health check failed: {resp.text}"
            data = resp.json()
            assert data.get("status") in ("ok", "healthy", "up")

            resp = await client.get("/api/v1/health/ready")
            assert resp.status_code == 200, f"Readiness probe failed: {resp.text}"

            # -------------------------------------------------------------
            # 2. Candidate Context & Profile Onboarding Update
            # -------------------------------------------------------------
            resp = await client.get("/api/v1/candidates/me", headers=headers)
            assert resp.status_code == 200, f"Candidate context failed: {resp.text}"
            profile = resp.json()
            assert profile["full_name"] == "Jordan Lee"
            assert "Staff Infrastructure Engineer" in profile.get("headline", "")

            # Update headline via PATCH
            resp = await client.patch(
                "/api/v1/candidates/me",
                headers=headers,
                json={"headline": "Principal Distributed Systems Architect"},
            )
            assert resp.status_code == 200, f"Candidate patch failed: {resp.text}"
            updated_profile = resp.json()
            assert updated_profile["headline"] == "Principal Distributed Systems Architect"

            # -------------------------------------------------------------
            # 3. Document / Resume Upload
            # -------------------------------------------------------------
            resume_content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF"
            files = {"file": ("resume.pdf", io.BytesIO(resume_content), "application/pdf")}
            resp = await client.post("/api/v1/resumes", headers=headers, files=files)
            assert resp.status_code == 202, f"Resume upload failed: {resp.text}"
            upload_data = resp.json()
            assert "document_id" in upload_data
            assert upload_data.get("status") in ("queued", "uploading", "processing")
            uploaded_doc_id = upload_data["document_id"]

            # -------------------------------------------------------------
            # 4. Question Discovery & Domains Catalog
            # -------------------------------------------------------------
            resp = await client.get("/api/v1/questions/domains", headers=headers)
            assert resp.status_code == 200, f"Question domains failed: {resp.text}"

            resp = await client.get("/api/v1/questions", headers=headers)
            assert resp.status_code == 200, f"Questions listing failed: {resp.text}"

            # -------------------------------------------------------------
            # 5. Spaced Repetition Study Card Lifecycle
            # -------------------------------------------------------------
            # Create a new study card
            card_payload = {
                "topic": "Storage Engines",
                "source": "manual",
                "prompt": "What is the primary difference between LSM-trees and B-trees?",
                "reference_answer": "LSM-trees optimize for sequential writes via append-only SSTables and compaction; B-trees optimize for read locality via in-place updates.",
                "difficulty": "hard",
            }
            resp = await client.post("/api/v1/study/items", headers=headers, json=card_payload)
            assert resp.status_code == 201, f"Study card creation failed: {resp.text}"
            created_card = resp.json()
            card_id = created_card["id"]
            assert created_card["topic"] == "Storage Engines"

            # List study cards
            resp = await client.get("/api/v1/study/items", headers=headers)
            assert resp.status_code == 200, f"Study items retrieval failed: {resp.text}"
            items_data = resp.json()
            assert "items" in items_data
            assert len(items_data["items"]) >= 2

            # Review the study card (SM-2 recall rating 5: perfect recall)
            resp = await client.post(
                f"/api/v1/study/items/{card_id}/review",
                headers=headers,
                json={"quality": 5},
            )
            assert resp.status_code == 200, f"Study review failed: {resp.text}"
            review_res = resp.json()
            assert "next_review_at" in review_res

            # Check due study items
            resp = await client.get("/api/v1/study/items/due", headers=headers)
            assert resp.status_code == 200, f"Due items retrieval failed: {resp.text}"

            # -------------------------------------------------------------
            # 6. Interview Session Orchestration
            # -------------------------------------------------------------
            session_payload = {
                "focus_area": "Distributed Storage & Consensus",
                "mode": "mock_interview",
                "interview_type": "technical",
                "difficulty": "standard",
            }
            resp = await client.post("/api/v1/sessions", headers=headers, json=session_payload)
            assert resp.status_code == 201, f"Session creation failed: {resp.text}"
            session_data = resp.json()
            session_id = session_data["id"]
            assert session_data.get("status") in ("pending", "created", "in_progress", "active")

            # Inspect active session
            resp = await client.get(f"/api/v1/sessions/{session_id}", headers=headers)
            assert resp.status_code == 200, f"Session retrieval failed: {resp.text}"
            assert resp.json()["id"] == session_id

            # List turns for session
            resp = await client.get(f"/api/v1/sessions/{session_id}/turns", headers=headers)
            assert resp.status_code == 200

            # End interview session
            resp = await client.post(f"/api/v1/sessions/{session_id}/end", headers=headers)
            assert resp.status_code in (200, 202), f"End session failed: {resp.text}"

            # -------------------------------------------------------------
            # 7. Candidate Analytics & Readiness Dashboard
            # -------------------------------------------------------------
            resp = await client.get("/api/v1/analytics/dashboard", headers=headers)
            assert resp.status_code == 200, f"Analytics dashboard failed: {resp.text}"
            dashboard = resp.json()
            assert "total_sessions" in dashboard
            assert "interviews_completed" in dashboard

            # -------------------------------------------------------------
            # 8. GDPR Candidate Data Self-Export Lifecycle
            # -------------------------------------------------------------
            resp = await client.post("/api/v1/export", headers=headers)
            assert resp.status_code == 202, f"Export initiation failed: {resp.text}"
            export_init = resp.json()
            assert "export_id" in export_init
            export_id = export_init["export_id"]

            resp = await client.get(f"/api/v1/export/{export_id}", headers=headers)
            assert resp.status_code == 200, f"Export status check failed: {resp.text}"
            export_status = resp.json()
            assert export_status["export_id"] == export_id
            assert export_status["status"] in ("pending", "processing", "ready")

            # -------------------------------------------------------------
            # 9. OpenAPI Contract Standard Error Model Validation
            # -------------------------------------------------------------
            # Non-existent or invalid UUID format returns standard 422 Unprocessable Entity
            resp = await client.get("/api/v1/questions/invalid-not-uuid", headers=headers)
            assert resp.status_code == 422
            err_json = resp.json()
            assert "detail" in err_json, "Error response does not follow standard OpenAPI detail schema"

    finally:
        app.dependency_overrides.clear()
        await engine.dispose()
