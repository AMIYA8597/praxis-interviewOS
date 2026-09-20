import pytest
import pytest_asyncio
import uuid
import os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql+asyncpg://praxis:dev_password@localhost:5432/praxis")

@pytest_asyncio.fixture(scope="function")
async def db_session():
    engine = create_async_engine(DATABASE_URL, echo=False)
    AsyncSessionLocal = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    
    try:
        async with engine.connect() as conn:
            pass
    except Exception as e:
        await engine.dispose()
        pytest.skip(f"Database not accessible: {e}")

    async with AsyncSessionLocal() as session:
        yield session
        
    await engine.dispose()

@pytest.mark.asyncio
async def test_rls_storage_cross_tenant_isolation(db_session: AsyncSession):
    user_a = str(uuid.uuid4())
    user_b = str(uuid.uuid4())
    
    # Bypass RLS
    await db_session.execute(text("RESET ROLE"))
    
    # Insert users
    await db_session.execute(text("INSERT INTO auth.users (id) VALUES (:id)"), {"id": user_a})
    await db_session.execute(text("INSERT INTO auth.users (id) VALUES (:id)"), {"id": user_b})
    
    await db_session.execute(text("INSERT INTO profiles (id) VALUES (:id)"), {"id": user_a})
    await db_session.execute(text("INSERT INTO profiles (id) VALUES (:id)"), {"id": user_b})
    
    candidate_a = str(uuid.uuid4())
    candidate_b = str(uuid.uuid4())
    
    await db_session.execute(text("INSERT INTO candidates (id, profile_id, full_name) VALUES (:id, :profile_id, 'User A')"), {"id": candidate_a, "profile_id": user_a})
    await db_session.execute(text("INSERT INTO candidates (id, profile_id, full_name) VALUES (:id, :profile_id, 'User B')"), {"id": candidate_b, "profile_id": user_b})
    await db_session.commit()
    
    # 1. Authenticate as User A and insert object
    await db_session.execute(text("SET ROLE authenticated"))
    await db_session.execute(text(f"SET request.jwt.claims TO '{{\"sub\": \"{user_a}\"}}'"))
    
    obj_a = str(uuid.uuid4())
    key_a = f"{candidate_a}/documents/resume_a.pdf"
    await db_session.execute(text("INSERT INTO storage.objects (id, bucket_id, name, owner) VALUES (:id, 'documents', :name, :owner)"), {"id": obj_a, "name": key_a, "owner": user_a})
    await db_session.commit()
    
    # 2. Authenticate as User B and insert object
    await db_session.execute(text(f"SET request.jwt.claims TO '{{\"sub\": \"{user_b}\"}}'"))
    
    obj_b = str(uuid.uuid4())
    key_b = f"{candidate_b}/documents/resume_b.pdf"
    await db_session.execute(text("INSERT INTO storage.objects (id, bucket_id, name, owner) VALUES (:id, 'documents', :name, :owner)"), {"id": obj_b, "name": key_b, "owner": user_b})
    await db_session.commit()
    
    # User B should not be able to select User A's object
    res = await db_session.execute(text("SELECT count(*) FROM storage.objects WHERE id = :id"), {"id": obj_a})
    assert res.scalar() == 0, "User B could read User A's object!"
    
    # User B should not be able to update User A's object
    res = await db_session.execute(text("UPDATE storage.objects SET metadata = '{\"hacked\": true}' WHERE id = :id"), {"id": obj_a})
    assert res.rowcount == 0, "User B could update User A's object!"
    
    # User B should not be able to delete User A's object
    res = await db_session.execute(text("DELETE FROM storage.objects WHERE id = :id"), {"id": obj_a})
    assert res.rowcount == 0, "User B could delete User A's object!"
    
    # User B should be able to read/update/delete their own object
    res = await db_session.execute(text("SELECT count(*) FROM storage.objects WHERE id = :id"), {"id": obj_b})
    assert res.scalar() == 1, "User B could NOT read their own object!"
    
    res = await db_session.execute(text("UPDATE storage.objects SET metadata = '{\"hacked\": false}' WHERE id = :id"), {"id": obj_b})
    assert res.rowcount == 1, "User B could NOT update their own object!"
    
    res = await db_session.execute(text("DELETE FROM storage.objects WHERE id = :id"), {"id": obj_b})
    assert res.rowcount == 1, "User B could NOT delete their own object!"
    
    print("Storage RLS cross-tenant isolation passed.")
