import pytest
import pytest_asyncio
import asyncio
import json
import websockets
from multiprocessing import Process
import uvicorn
import socket

import os
import tempfile
import uuid
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
# Create a temporary SQLite DB for this test to share between test process and uvicorn process
if "TEST_DB_URL" not in os.environ:
    temp_db_path = f"praxis_test_{uuid.uuid4().hex}.db"
    db_url = f"sqlite+aiosqlite:///{temp_db_path}"
    os.environ["TEST_DB_URL"] = db_url
else:
    db_url = os.environ["TEST_DB_URL"]
    temp_db_path = db_url.split("///")[-1]
    
temp_db = temp_db_path
os.environ["DATABASE_URL"] = db_url

def create_access_token(data: dict):
    # Dummy function for the test
    import jwt
    return jwt.encode(data, "dummy_secret", algorithm="HS256")

import fakeredis

fake_redis = fakeredis.FakeAsyncRedis()

@pytest_asyncio.fixture(scope="function")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture(scope="function")
async def realtime_server():
    # Setup DB schema first
    import sqlite3
    conn = sqlite3.connect(temp_db)
    conn.execute("CREATE TABLE users (id TEXT PRIMARY KEY, email TEXT, password_hash TEXT)")
    conn.execute("CREATE TABLE candidates (id TEXT PRIMARY KEY, profile_id TEXT)")
    conn.execute("CREATE TABLE practice_sessions (id TEXT PRIMARY KEY, candidate_id TEXT, status TEXT, ended_at TEXT)")
    conn.execute("CREATE TABLE session_state_log (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, from_state TEXT, to_state TEXT, reason TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP)")
    conn.commit()
    conn.close()

    import os
    os.environ["DATABASE_URL"] = db_url
    os.environ["REDIS_URL"] = "redis://localhost:6379/0"
    from packages.config.settings import settings
    settings.DATABASE_URL = db_url

    from realtime_agent.app.main import create_app
    app = create_app()
    
    from unittest import mock
    with mock.patch("redis.asyncio.Redis.from_url", return_value=fake_redis):
        # We also need to patch it directly in app state if it's already created
        app.state.redis_pool = fake_redis
        
        config = uvicorn.Config(app, host="127.0.0.1", port=8002, log_level="info")
        server = uvicorn.Server(config)
        
        # Start server as a task
        task = asyncio.create_task(server.serve())
        
        # Wait for startup
        import time
        await asyncio.sleep(2)
        
        yield "ws://127.0.0.1:8002/ws/sessions"
        
        # Teardown
        server.should_exit = True
        await task

    # Cleanup DB
    if os.path.exists(temp_db):
        try:
            os.remove(temp_db)
        except Exception:
            pass

@pytest.mark.asyncio
async def test_reconnect_hard_tcp_drop(realtime_server):
    db_url = os.environ["DATABASE_URL"]
    engine = create_async_engine(db_url)
    
    session_id = str(uuid.uuid4())
    user_id = "00000000-0000-0000-0000-000000000000"
    candidate_id = str(uuid.uuid4())
    
    async with engine.begin() as conn:
        await conn.execute(text("INSERT INTO users (id, email, password_hash) VALUES (:id, :email, 'hash') ON CONFLICT (id) DO NOTHING"), {"id": user_id, "email": f"test_{user_id}@example.com"})
        await conn.execute(text("INSERT INTO candidates (id, profile_id) VALUES (:cid, :uid) ON CONFLICT (id) DO NOTHING"), {"cid": candidate_id, "uid": user_id})
        await conn.execute(text("""
            INSERT INTO practice_sessions (id, candidate_id, status)
            VALUES (:sid, :cid, 'pending')
        """), {"sid": session_id, "cid": candidate_id})
        
    token = create_access_token({"sub": user_id})
    uri = f"{realtime_server}/{session_id}?token={token}"
    
    print(f"Connecting to {uri}")
    
    # First connection
    ws = await websockets.connect(uri)
    
    ready_seen = False
    for _ in range(5):
        msg = await asyncio.wait_for(ws.recv(), 2.0)
        evt = json.loads(msg)
        if evt.get("type") == "state.transitioned" and evt["payload"]["to"] == "READY":
            ready_seen = True
            break
            
    assert ready_seen, "Should have reached READY state"
    
    # HARD TCP DROP
    # We abort the transport to simulate a hard TCP drop
    ws.transport.abort()
    
    # Now it's abruptly dropped. Wait a moment for server to detect EOF and trigger RECONNECTING
    await asyncio.sleep(2)
    
    # Check DB or Redis? 
    # Redis should have "session:state:{session_id}"
    state = await fake_redis.hget(f"session:state:{session_id}", "state")
    assert state.decode() == "RECONNECTING"
    
    # Reconnect!
    ws2 = await websockets.connect(uri)
    msg = await asyncio.wait_for(ws2.recv(), 2.0)
    evt = json.loads(msg)
    
    assert evt["type"] == "state.transitioned"
    assert evt["payload"]["from"] == "RECONNECTING"
    assert evt["payload"]["to"] == "READY"
    assert evt["payload"]["reason"] == "reconnected"
    
    await ws2.close()
    await fake_redis.close()
    await engine.dispose()
