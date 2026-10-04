"""
Harness for API-level tests that exercise the *real* routers, services,
repositories and SQL against a real (SQLite, in-memory) database built from
the ORM models. Only identity, Redis, the job queue and object storage are
replaced with test doubles.
"""
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from backend.app.core.storage import LocalFileStorage
from backend.app.db.models import Base
from backend.app.dependencies import (
    get_arq_pool,
    get_current_candidate,
    get_db_session,
    get_object_storage,
    get_redis,
)
from backend.app.main import app


class FakeArqPool:
    """Records enqueued jobs instead of talking to Redis."""

    def __init__(self):
        self.jobs = []

    async def enqueue_job(self, name, *args, **kwargs):
        self.jobs.append(SimpleNamespace(name=name, args=args, kwargs=kwargs))
        return SimpleNamespace(job_id=kwargs.get("_job_id") or str(uuid.uuid4()))


@pytest_asyncio.fixture
async def db_factory():
    engine = create_async_engine(
        "sqlite+aiosqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    await engine.dispose()


async def _make_candidate(factory, name: str) -> dict:
    profile_id, candidate_id = str(uuid.uuid4()), str(uuid.uuid4())
    async with factory() as s:
        await s.execute(text("INSERT INTO profiles (id) VALUES (:p)"), {"p": profile_id})
        await s.execute(
            text("INSERT INTO candidates (id, profile_id, full_name) VALUES (:c, :p, :n)"),
            {"c": candidate_id, "p": profile_id, "n": name},
        )
        await s.commit()
    return {"id": candidate_id, "user_id": profile_id, "profile_id": profile_id}


@pytest_asyncio.fixture
async def alice(db_factory):
    return await _make_candidate(db_factory, "Alice")


@pytest_asyncio.fixture
async def bob(db_factory):
    return await _make_candidate(db_factory, "Bob")


@pytest.fixture
def arq_pool():
    return FakeArqPool()


@pytest.fixture
def storage(tmp_path):
    return LocalFileStorage(str(tmp_path / "objects"))


@pytest_asyncio.fixture
async def api(db_factory, arq_pool, storage):
    """Returns (client, act_as) where act_as(candidate) switches the caller."""
    current = {"candidate": None}

    async def _db():
        async with db_factory() as s:
            yield s

    async def _candidate():
        if current["candidate"] is None:
            from backend.app.exceptions import UnauthorizedError

            raise UnauthorizedError("Not authenticated")
        return current["candidate"]

    redis = AsyncMock()
    redis.get.return_value = None
    app.dependency_overrides[get_db_session] = _db
    app.dependency_overrides[get_current_candidate] = _candidate
    app.dependency_overrides[get_redis] = lambda: redis
    app.dependency_overrides[get_arq_pool] = lambda: arq_pool
    app.dependency_overrides[get_object_storage] = lambda: storage

    def act_as(candidate):
        current["candidate"] = candidate

    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test/api/v1") as client:
        yield client, act_as
    app.dependency_overrides.clear()
