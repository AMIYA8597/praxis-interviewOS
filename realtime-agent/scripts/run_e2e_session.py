import asyncio
import json
import uuid
import os
import jwt
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import uvicorn
from multiprocessing import Process

temp_db_path = f"praxis_e2e_{uuid.uuid4().hex}.db"
db_url = f"sqlite+aiosqlite:///{temp_db_path}"
os.environ["DATABASE_URL"] = db_url
os.environ["OPENAI_API_KEY"] = "mocked" # Just in case

def create_access_token(data: dict):
    return jwt.encode(data, "dummy_secret", algorithm="HS256")

async def setup_db():
    engine = create_async_engine(db_url)
    async with engine.begin() as conn:
        await conn.execute(text("CREATE TABLE candidates (id TEXT, profile_id TEXT, full_name TEXT)"))
        await conn.execute(text("CREATE TABLE jobs (id TEXT)"))
        await conn.execute(text("CREATE TABLE job_blueprints (job_id TEXT, summary TEXT)"))
        await conn.execute(text("CREATE TABLE practice_sessions (id TEXT, candidate_id TEXT, job_id TEXT, status TEXT, ended_at TEXT)"))
        await conn.execute(text("CREATE TABLE session_debriefs (id TEXT, session_id TEXT, headline_metrics TEXT, strengths TEXT, weaknesses TEXT, flagged_claims TEXT, jd_coverage TEXT, generated_at TEXT)"))
        await conn.execute(text("CREATE TABLE transcript_segments (session_id TEXT, role TEXT, text TEXT, start_ms REAL, end_ms REAL, confidence REAL, source TEXT)"))
        await conn.execute(text("CREATE TABLE session_turns (id TEXT, session_id TEXT, turn_index INT, speaker TEXT, text_content TEXT, started_at TEXT, ended_at TEXT)"))
        await conn.execute(text("CREATE TABLE turn_scores (id TEXT, turn_id TEXT, overall REAL, rationale TEXT, relevance REAL, correctness REAL, structure REAL, grounding REAL, specificity REAL, conciseness REAL)"))
        await conn.execute(text("CREATE TABLE session_claims (id TEXT, session_id TEXT, turn_id TEXT, claim_text TEXT, supported BOOLEAN, contradiction_of_claim_id TEXT)"))
        
    async with engine.connect() as conn:
        await conn.execute(text("INSERT INTO candidates (id, profile_id, full_name) VALUES ('test-cand', 'test-user-id', 'Test Candidate')"))
        await conn.execute(text("INSERT INTO practice_sessions (id, candidate_id, job_id) VALUES ('test-session', 'test-cand', 'test-job')"))
        await conn.execute(text("INSERT INTO job_blueprints (job_id, summary) VALUES ('test-job', '{}')"))
        await conn.commit()
    await engine.dispose()

def run_server():
    # Mock some stuff
    import realtime_agent.app.main as main
    
    async def mock_verify(token, redis):
        return {"sub": "test-user-id"}
    main.verify_jwt = mock_verify
    
    class MockVAD:
        def process_frame(self, frame):
            self.count = getattr(self, "count", 0) + 1
            if self.count == 5:
                return {"confidence": 0.9, "energy_db": -20}, "speech_end"
            return {"confidence": 0.9, "energy_db": -20}, None
    import realtime_agent.app.audio.vad as vad
    vad.VoiceActivityDetector = MockVAD
    
    uvicorn.run(main.app, host="127.0.0.1", port=8099)

async def run_client():
    import websockets
    await asyncio.sleep(2) # let server start
    token = create_access_token({"sub": "test-user-id"})
    uri = f"ws://127.0.0.1:8099/ws/sessions/test-session?token={token}"
    
    async with websockets.connect(uri) as ws:
        # We should receive events
        for _ in range(5):
            msg = await ws.recv()
            data = json.loads(msg)
            print("Got:", data["type"])
            if data["type"] == "interviewer.text":
                break
        
        print("Sending audio bytes to trigger VAD")
        for _ in range(6):
            await ws.send(b"\x00" * 1024)
            
        await asyncio.sleep(2)
        await ws.send(b"\x00" * 1024)
        
        print("Waiting for next turn")
        for _ in range(10):
            msg = await ws.recv()
            data = json.loads(msg)
            print("Got:", data["type"])
            if data["type"] == "interviewer.text":
                break
                
        print("Ending session")
        await ws.send(json.dumps({"type": "session.end"}))
        
        while True:
            try:
                msg = await ws.recv()
                data = json.loads(msg)
                print("Got:", data["type"])
                if data["type"] == "debrief.ready":
                    break
            except Exception as e:
                print("Websocket closed/error:", e)
                break
    engine = create_async_engine(db_url)
    async with engine.connect() as conn:
        res = await conn.execute(text("SELECT * FROM session_debriefs"))
        print("\nDebriefs:", res.fetchall())
    await engine.dispose()
    try:
        os.remove(temp_db_path)
    except PermissionError:
        pass

async def run_all():
    import uvicorn
    import realtime_agent.app.main as main
    import fakeredis
    fake_redis = fakeredis.FakeAsyncRedis()
    import redis.asyncio as redis_async
    redis_async.Redis.from_url = lambda url, **kw: fake_redis
    
    async def mock_verify(token, redis):
        return {"sub": "test-user-id"}
    main.verify_jwt = mock_verify
    
    class MockVAD:
        def process_frame(self, frame):
            self.count = getattr(self, "count", 0) + 1
            if self.count == 2:
                return {"confidence": 0.9, "energy_db": -20}, "speech_start"
            if self.count == 5:
                return {"confidence": 0.9, "energy_db": -20}, "speech_end"
            return {"confidence": 0.9, "energy_db": -20}, None
    import realtime_agent.app.audio.vad as vad
    vad.VoiceActivityDetector = MockVAD
    
    # Mock Gateway Route
    async def mock_route(self, task, ctx, method_name, *args, **kw):
        schema = kw.get('schema')
        class MockCall:
            async def execute(self):
                from collections import namedtuple
                Res = namedtuple('Res', ['result'])
                from realtime_agent.app.scoring.models import AnswerScore
                from realtime_agent.app.interview.debrief import SessionDebrief, HeadlineMetrics
                from realtime_agent.app.scoring.claims import SessionClaim
                
                if "scoring" in task or schema == AnswerScore:
                    return Res(result=AnswerScore(
                        relevance=0.8, correctness=0.9, structure=0.7, grounding=0.8, specificity=0.7, conciseness=0.6, overall=0.8, rationale="Good answer"
                    ))
                elif "debrief" in task or schema == SessionDebrief:
                    return Res(result=SessionDebrief(
                        headline_metrics=HeadlineMetrics(average_wpm=100.0, average_filler_rate=0.1, average_score=0.8),
                        strengths=["Knows Python"], weaknesses=["Short answer"], flagged_claims=[], jd_coverage={}
                    ))
                elif "policy" in task or "next_question" in task or "next" in task:
                    from realtime_agent.app.interview.policy import PolicyDecision
                    return Res(result=PolicyDecision(
                        response_text="Can you elaborate on React?",
                        decision_rationale="Follow up",
                        is_closing=False,
                        focus_area="frontend"
                    ))
                elif "claims" in task or (isinstance(schema, list) and schema and schema[0] == SessionClaim):
                    return Res(result=[SessionClaim(claim="I used Python", is_supported=True, rationale="")])
                return Res(result=None)
        return MockCall()
    import praxis_ai_gateway.router as router
    router.GatewayRouter.route = mock_route
    
    # Mock Transcriber
    class MockTranscriber:
        async def connect(self, config): pass
        async def close(self): pass
        async def send_audio(self, pcm): pass
        async def receive_events(self):
            await asyncio.sleep(0.5)
            yield {"is_interim": False, "text": "I used Python and React.", "start_ms": 0.0, "end_ms": 2.0, "confidence": 0.9, "source": "user"}
            while True: await asyncio.sleep(1)
        async def signal_segment_end(self): pass
    import praxis_ai_gateway.transcription.router as transcriber_router
    transcriber_router.select_transcriber = lambda *args: MockTranscriber()
    
    # Mock TTS
    async def mock_tts_stream(self, text_stream, token): yield b"fake_audio_bytes"
    import realtime_agent.app.audio.tts as tts
    tts.PiperTTSAdapter.synthesize_streaming = mock_tts_stream

    config = uvicorn.Config(main.app, host="127.0.0.1", port=8099, log_level="info")
    server = uvicorn.Server(config)
    server_task = asyncio.create_task(server.serve())
    await asyncio.sleep(2)
    await run_client()
    server.should_exit = True
    await server_task

if __name__ == "__main__":
    asyncio.run(setup_db())
    asyncio.run(run_all())
