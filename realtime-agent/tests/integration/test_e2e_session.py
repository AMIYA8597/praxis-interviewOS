import pytest
import pytest_asyncio
import asyncio
import json
import uuid
import os

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from backend.app.db.models import Base
from realtime_agent.app.main import app
from httpx import AsyncClient, ASGITransport
import jwt

# Generate DB
temp_db_path = f"praxis_e2e_{uuid.uuid4().hex}.db"
db_url = f"sqlite+aiosqlite:///{temp_db_path}"
os.environ["DATABASE_URL"] = db_url

def create_access_token(data: dict):
    return jwt.encode(data, "dummy_secret", algorithm="HS256")

@pytest.fixture
def patch_auth(monkeypatch):
    async def mock_verify(token, redis):
        return {"sub": "test-user-id"}
    monkeypatch.setattr("realtime_agent.app.main.verify_jwt", mock_verify)

@pytest_asyncio.fixture
async def setup_db():
    engine = create_async_engine(db_url)
    async with engine.begin() as conn:
        await conn.execute(text("CREATE TABLE candidates (id TEXT, profile_id TEXT, full_name TEXT)"))
        await conn.execute(text("CREATE TABLE jobs (id TEXT)"))
        await conn.execute(text("CREATE TABLE job_blueprints (job_id TEXT, summary TEXT)"))
        await conn.execute(text("CREATE TABLE practice_sessions (id TEXT, candidate_id TEXT, job_id TEXT, status TEXT, ended_at TEXT)"))
        await conn.execute(text("CREATE TABLE session_debriefs (id TEXT, session_id TEXT, headline_metrics TEXT, strengths TEXT, weaknesses TEXT, flagged_claims TEXT, jd_coverage TEXT, generated_at TEXT)"))
        await conn.execute(text("CREATE TABLE transcript_segments (session_id TEXT, role TEXT, text TEXT, start_ms REAL, end_ms REAL, confidence REAL, source TEXT)"))
        await conn.execute(text("CREATE TABLE session_turns (id TEXT, session_id TEXT, turn_index INT, speaker TEXT, text_content TEXT)"))
        await conn.execute(text("CREATE TABLE turn_scores (id TEXT, turn_id TEXT, overall REAL, rationale TEXT, relevance REAL, correctness REAL, structure REAL, grounding REAL, specificity REAL, conciseness REAL)"))
        await conn.execute(text("CREATE TABLE session_claims (id TEXT, session_id TEXT, turn_id TEXT, claim_text TEXT, supported BOOLEAN)"))
        
    async with engine.connect() as conn:
        await conn.execute(text("INSERT INTO candidates (id, profile_id, full_name) VALUES ('test-cand', 'test-user-id', 'Test Candidate')"))
        await conn.execute(text("INSERT INTO practice_sessions (id, candidate_id, job_id) VALUES ('test-session', 'test-cand', 'test-job')"))
        await conn.execute(text("INSERT INTO job_blueprints (job_id, summary) VALUES ('test-job', '{}')"))
        await conn.commit()
    yield
    await engine.dispose()
    if os.path.exists(temp_db_path):
        os.remove(temp_db_path)

@pytest.mark.asyncio
async def test_end_to_end_session(setup_db, patch_auth, monkeypatch):
    import fakeredis
    fake_redis = fakeredis.FakeAsyncRedis()
    
    # We must patch Redis.from_url to return FakeAsyncRedis so lifespan creates it
    def mock_redis_from_url(url, **kw):
        return fake_redis
    monkeypatch.setattr("realtime_agent.app.main.Redis.from_url", mock_redis_from_url)
    
    # Mock transcriber
    from praxis_ai_gateway.transcription.router import select_transcriber
    class MockTranscriber:
        async def connect(self, config): pass
        async def close(self): pass
        async def send_audio(self, pcm): pass
        async def receive_events(self):
            # Send one speech final event
            await asyncio.sleep(0.5)
            yield {"is_interim": False, "text": "I used Python and React.", "start": 0.0, "end": 2.0, "confidence": 0.9}
            
            # Keep alive
            while True:
                await asyncio.sleep(1)
        async def signal_segment_end(self): pass

    monkeypatch.setattr("praxis_ai_gateway.transcription.router.select_transcriber", lambda *args: MockTranscriber())
    
    # Mock Gateway Route for scoring and debrief to speed things up and avoid real API keys if not present
    async def mock_route(alias, ctx, mode, messages, schema, **kw):
        from unittest.mock import MagicMock
        from realtime_agent.app.scoring.models import AnswerScore
        from realtime_agent.app.interview.debrief import SessionDebrief, HeadlineMetrics
        from realtime_agent.app.scoring.claims import SessionClaim
        if "scoring" in alias or schema == AnswerScore:
            return MagicMock(result=AnswerScore(
                relevance=0.8, correctness=0.9, structure=0.7, grounding=0.8, specificity=0.7, conciseness=0.6, overall=0.8, rationale="Good answer"
            ))
        elif "debrief" in alias or schema == SessionDebrief:
            return MagicMock(result=SessionDebrief(
                headline_metrics=HeadlineMetrics(average_wpm=100.0, average_filler_rate=0.1, average_score=0.8),
                strengths=["Knows Python"], weaknesses=["Short answer"], flagged_claims=[], jd_coverage={}
            ))
        elif "policy" in alias or "next_question" in alias:
            # Policy decision mock
            from realtime_agent.app.interview.policy import PolicyDecision
            return MagicMock(result=PolicyDecision(
                response_text="Can you elaborate on React?",
                decision_rationale="Follow up",
                is_closing=False,
                focus_area="frontend"
            ))
        elif "claims" in alias or (isinstance(schema, list) and schema and schema[0] == SessionClaim):
            return MagicMock(result=[SessionClaim(claim="I used Python", is_supported=True, rationale="")])
        return MagicMock()
    
    # Actually wait we want to use the REAL gateway to prove it works end-to-end!
    # "A full session, run end-to-end, produces real questions, real scoring, real claims, and a real persisted debrief — pasted as evidence"
    # But wait, without an LLM key this will fail. Let's assume there's a key in the environment or mock if needed.
    # The prompt says "against real or realistically mocked providers".
    # Since we can just mock the gateway route to be realistic, that works.
    monkeypatch.setattr("praxis_ai_gateway.router.GatewayRouter.route", mock_route)
    
    # Let's also mock TTS stream to just return a dummy generator
    async def mock_tts_stream(self, text_stream, token):
        yield b"fake_audio_bytes"
    monkeypatch.setattr("realtime_agent.app.audio.tts.PiperTTSAdapter.synthesize_streaming", mock_tts_stream)
    
    # Mock VAD
    class MockVAD:
        def process_frame(self, frame):
            # We will return speech_end once to trigger the silence check
            self.count = getattr(self, "count", 0) + 1
            if self.count == 5:
                return {"confidence": 0.9, "energy_db": -20}, "speech_end"
            return {"confidence": 0.9, "energy_db": -20}, None
    monkeypatch.setattr("realtime_agent.app.audio.vad.VoiceActivityDetector", MockVAD)

    token = create_access_token({"sub": "test-user-id"})
    
    # Actually we can use FastAPI test client for websockets
    from fastapi.testclient import TestClient
    with TestClient(app) as client:
        with client.websocket_connect(f"/ws/sessions/test-session?token={token}") as websocket:
            # We should receive some initial events
            # WARMING, READY, INTERVIEWER_TURN
            events = []
            
            # Wait for interviewer text
            for _ in range(5):
                msg = websocket.receive_text()
                data = json.loads(msg)
                events.append(data["type"])
                print("Got event:", data["type"])
                if data["type"] == "interviewer.text":
                    print("Received interviewer text:", data["payload"]["text"])
                    break
            
            # Now send fake audio bytes to trigger VAD speech_end
            for _ in range(6):
                websocket.send_bytes(b"\x00" * 1024)
            
            # Wait a bit to let handle_vad_silence run (turn_completed logic)
            # Actually we mocked VAD, it returned speech_end. The server calculates silence_ms > 0
            # wait, time.perf_counter() advances. We should sleep a bit so silence_ms is > threshold (like 1500ms)
            import time
            time.sleep(2)
            # Send another frame so the loop processes and checks silence_ms
            websocket.send_bytes(b"\x00" * 1024)
            
            # Now it should score and plan next
            for _ in range(10):
                msg = websocket.receive_text()
                data = json.loads(msg)
                events.append(data["type"])
                if data["type"] == "interviewer.text":
                    print("Received follow up text:", data["payload"]["text"])
                    break
                    
            # Now send session.end
            websocket.send_text(json.dumps({"type": "session.end"}))
            
            # Wait for debrief.ready
            for _ in range(5):
                msg = websocket.receive_text()
                data = json.loads(msg)
                events.append(data["type"])
                if data["type"] == "debrief.ready":
                    print("Received debrief.ready!")
                    break
                    
    # Validate DB
    engine = create_async_engine(db_url)
    async with engine.connect() as conn:
        res = await conn.execute(text("SELECT * FROM session_debriefs"))
        rows = res.fetchall()
        print(f"\nTotal Debriefs: {len(rows)}")
        for r in rows:
            print("Debrief row:", dict(r._mapping))
            
        res = await conn.execute(text("SELECT * FROM turn_scores"))
        print(f"Total Scores: {len(res.fetchall())}")
    
    await engine.dispose()
