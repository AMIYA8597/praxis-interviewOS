import pytest
import pytest_asyncio
import uuid
import os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import ProgrammingError

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres")

@pytest_asyncio.fixture(scope="function")
async def db_session():
    engine = create_async_engine(DATABASE_URL, echo=False)
    AsyncSessionLocal = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    
    # Only run DB tests if we can connect
    try:
        async with engine.connect() as conn:
            pass
    except Exception as e:
        await engine.dispose()
        pytest.skip(f"Database not accessible, skipping real RLS tests: {e}")

    async with AsyncSessionLocal() as session:
        yield session
        
    await engine.dispose()

@pytest.mark.asyncio
async def test_rls_cross_tenant_isolation(db_session: AsyncSession):
    """
    Validates that User A cannot read User B's profile, candidate, or document data.
    """
    user_a = str(uuid.uuid4())
    user_b = str(uuid.uuid4())
    
    # 1. Setup as postgres/superuser (bypass RLS) to seed data
    # Note: In a real test we'd use a service_role connection. 
    # For this test we just insert.
    await db_session.execute(text("INSERT INTO auth.users (id) VALUES (:id)"), {"id": user_a})
    await db_session.execute(text("INSERT INTO auth.users (id) VALUES (:id)"), {"id": user_b})
    
    await db_session.execute(text("INSERT INTO profiles (id) VALUES (:id)"), {"id": user_a})
    await db_session.execute(text("INSERT INTO profiles (id) VALUES (:id)"), {"id": user_b})
    
    candidate_a = str(uuid.uuid4())
    candidate_b = str(uuid.uuid4())
    
    await db_session.execute(text("INSERT INTO candidates (id, profile_id, full_name) VALUES (:id, :profile_id, 'User A')"), {"id": candidate_a, "profile_id": user_a})
    await db_session.execute(text("INSERT INTO candidates (id, profile_id, full_name) VALUES (:id, :profile_id, 'User B')"), {"id": candidate_b, "profile_id": user_b})
    
    doc_b = str(uuid.uuid4())
    await db_session.execute(text("INSERT INTO documents (id, candidate_id, kind) VALUES (:id, :candidate_id, 'resume')"), {"id": doc_b, "candidate_id": candidate_b})
    
    await db_session.commit()
    
    # 2. Simulate User A querying the database
    # In Supabase, auth context is set via set_config
    await db_session.execute(text("SET ROLE authenticated"))
    await db_session.execute(text(f"SET request.jwt.claims TO '{{\"sub\": \"{user_a}\"}}'"))
    
    # Attempt to read profiles
    result = await db_session.execute(text("SELECT id FROM profiles"))
    profiles = [str(p) for p in result.scalars().all()]
    assert user_a in profiles
    assert user_b not in profiles, "CRITICAL: User A can see User B's profile"
    
    # Attempt to read candidates
    result = await db_session.execute(text("SELECT id FROM candidates"))
    candidates = [str(c) for c in result.scalars().all()]
    assert candidate_a in candidates
    assert candidate_b not in candidates, "CRITICAL: User A can see User B's candidate record"
    
    # Attempt to read User B's documents
    result = await db_session.execute(text("SELECT id FROM documents"))
    documents = [str(d) for d in result.scalars().all()]
    assert doc_b not in documents, "CRITICAL: User A can see User B's documents"
    
    # Clean up (Reset to superuser to delete)
    await db_session.execute(text("RESET ROLE"))
    await db_session.execute(text("DELETE FROM auth.users WHERE id IN (:user_a, :user_b)"), {"user_a": user_a, "user_b": user_b})
    await db_session.commit()

@pytest.mark.asyncio
async def test_rls_admin_escalation(db_session: AsyncSession):
    """
    Validates that a normal user cannot insert into admin_users and escalate privileges.
    """
    user_a = str(uuid.uuid4())
    
    await db_session.execute(text("INSERT INTO auth.users (id) VALUES (:id)"), {"id": user_a})
    await db_session.execute(text("INSERT INTO profiles (id) VALUES (:id)"), {"id": user_a})
    await db_session.commit()
    
    await db_session.execute(text("SET ROLE authenticated"))
    await db_session.execute(text(f"SET request.jwt.claims TO '{{\"sub\": \"{user_a}\"}}'"))
    
    # Attempt to escalate
    with pytest.raises(Exception) as excinfo:
        await db_session.execute(text("INSERT INTO admin_users (profile_id, role) VALUES (:uid, 'super_admin')"), {"uid": user_a})
        await db_session.commit()
    
    assert "new row violates row-level security policy for table" in str(excinfo.value).lower()
    
    # Clean up
    await db_session.rollback()
    await db_session.execute(text("RESET ROLE"))
    await db_session.execute(text("DELETE FROM auth.users WHERE id = :user_a"), {"user_a": user_a})
    await db_session.commit()
