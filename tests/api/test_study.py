import uuid
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from backend.app.db.models import Base
from backend.app.dependencies import get_arq_pool, get_current_candidate, get_db_session
from backend.app.main import app


class FakeArq:
    def __init__(self):
        self.jobs = []

    async def enqueue_job(self, name, *args, **kwargs):
        self.jobs.append((name, args, kwargs))
        return SimpleNamespace(job_id=kwargs.get("_job_id"))


@pytest.fixture
def client():
    """Scoped overrides (never at import time) backed by a real SQLite schema."""
    import asyncio

    engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    candidate_id = str(uuid.uuid4())

    async def setup():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await conn.execute(
                text("INSERT INTO study_items (id, candidate_id, topic, source, prompt, reference_answer, difficulty) "
                     "VALUES (:i, :c, 'Python', 'manual', 'test', 'ans', 'easy')"),
                {"i": str(uuid.uuid4()), "c": candidate_id},
            )

    asyncio.run(setup())

    async def _db():
        async with factory() as s:
            yield s

    arq = FakeArq()
    app.dependency_overrides[get_current_candidate] = lambda: {"id": candidate_id, "user_id": candidate_id}
    app.dependency_overrides[get_db_session] = _db
    app.dependency_overrides[get_arq_pool] = lambda: arq
    with TestClient(app) as c:
        c.arq = arq
        yield c
    app.dependency_overrides.clear()
    asyncio.run(engine.dispose())


def test_get_study_materials(client):
    response = client.get("/api/v1/study/materials")
    assert response.status_code == 200
    data = response.json()
    assert len(data["materials"]) == 1
    assert data["materials"][0]["topic"] == "Python"

    items = client.get("/api/v1/study/items").json()
    assert [i["topic"] for i in items["items"]] == ["Python"]


def test_generate_study_material(client):
    req_data = {"topic": "FastAPI", "difficulty": "Hard"}
    r1 = client.post("/api/v1/study/generate", json=req_data)
    r2 = client.post("/api/v1/study/generate", json=req_data)

    assert r1.status_code == 202 and r2.status_code == 202
    d1, d2 = r1.json(), r2.json()
    assert d1["status"] == d2["status"] == "queued"
    assert d1["task_id"] != d2["task_id"]
    assert [j[0] for j in client.arq.jobs] == ["generate_study_material_job"] * 2
