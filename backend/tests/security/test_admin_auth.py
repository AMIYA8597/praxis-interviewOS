import pytest
import psycopg2
import os
import uuid
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from backend.app.dependencies import require_admin
import pytest_asyncio

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql+asyncpg://praxis:dev_password@localhost:5432/praxis")

@pytest_asyncio.fixture
async def real_db_session():
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session
    await engine.dispose()

@pytest.fixture
def sync_db():
    sync_url = DATABASE_URL.replace("postgresql+asyncpg", "postgresql")
    conn = psycopg2.connect(sync_url)
    conn.autocommit = True
    yield conn
    conn.close()

@pytest.mark.asyncio
async def test_require_admin_real_db(real_db_session, sync_db):
    cur = sync_db.cursor()
    
    admin_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    
    # Seed auth.users and profiles
    for u in [admin_id, user_id]:
        cur.execute("INSERT INTO auth.users (id) VALUES (%s)", (u,))
        cur.execute("INSERT INTO profiles (id) VALUES (%s)", (u,))
    
    # Seed admin user
    cur.execute("INSERT INTO admin_users (profile_id, role) VALUES (%s, 'admin')", (admin_id,))
    
    # Test admin succeeds
    admin_token_payload = {"sub": admin_id}
    result = await require_admin(current_user=admin_token_payload, db=real_db_session)
    assert result == admin_token_payload, "Admin check failed for valid admin"
    
    # Test non-admin gets 403, not 500
    user_token_payload = {"sub": user_id}
    with pytest.raises(HTTPException) as exc_info:
        await require_admin(current_user=user_token_payload, db=real_db_session)
        
    assert exc_info.value.status_code == 403, "Non-admin did not get 403 Forbidden"
