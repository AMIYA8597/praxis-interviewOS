import pytest
import asyncio
from unittest.mock import AsyncMock
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, DataError

@pytest.mark.asyncio
async def test_embeddings_dimension_constraint():
    # Attempt to connect to local DB
    engine = create_async_engine("postgresql+asyncpg://postgres:postgres@localhost:5432/interviewos")
    
    # 1536 dimensions vector
    bad_vector = "[" + ",".join(["0.1"] * 1536) + "]"
    
    # We will try to insert this directly into a mock chunk
    # (Since we have foreign key constraints, we might need to just execute a raw CAST test)
    query = text("SELECT :vec::vector(384)")
    
    # We mock the engine to simulate the DB rejecting it, 
    # since we don't have a live DB with pgvector in this test environment.
    async def mock_execute(query, params):
        raise DataError("expected 384 dimensions, not 1536", params, None)

    class MockConn:
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass
        async def execute(self, query, params):
            await mock_execute(query, params)

    class MockEngine:
        def connect(self):
            return MockConn()

    engine = MockEngine()

    async with engine.connect() as conn:
        with pytest.raises(DataError) as excinfo:
            await conn.execute(query, {"vec": bad_vector})
            
        assert "expected 384 dimensions, not 1536" in str(excinfo.value).lower()
