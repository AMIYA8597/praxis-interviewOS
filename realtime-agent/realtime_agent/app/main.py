import asyncio
import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text
from redis.asyncio import Redis

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource

from backend.app.auth import verify_jwt
from realtime_agent.app.protocol import Envelope

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql+asyncpg://praxis@localhost:5432/praxis")
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Setup OpenTelemetry
    resource = Resource.create({"service.name": "praxis-realtime-agent"})
    provider = TracerProvider(resource=resource)
    otlp_endpoint = os.environ.get("OTLP_ENDPOINT", "http://localhost:4318/v1/traces")
    exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    
    # Setup DB
    db_url = os.environ.get("DATABASE_URL", DATABASE_URL)
    engine = create_async_engine(db_url, pool_size=20, max_overflow=10)
    app.state.db_session_factory = async_sessionmaker(engine, expire_on_commit=False)
    
    # Setup Redis
    redis_url = os.environ.get("REDIS_URL", REDIS_URL)
    app.state.redis_pool = Redis.from_url(redis_url)
    
    from praxis_ai_gateway.registry import ModelRegistry
    from praxis_ai_gateway.providers.openai import OpenAIProvider
    from praxis_ai_gateway.providers.ollama import OllamaProvider
    from praxis_ai_gateway.router import GatewayRouter
    
    registry = ModelRegistry("config/models.yaml")
    
    providers = {}
    if os.environ.get("OPENAI_API_KEY"):
        providers["openai"] = OpenAIProvider()
    providers["ollama"] = OllamaProvider()
    
    app.state.gateway_router = GatewayRouter(
        registry=registry,
        providers=providers,
        redis=app.state.redis_pool,
        db=None  # Can be overridden per request
    )
    
    logger.info({"event": "realtime_agent_ready", "db": "connected", "redis": "connected", "gateway": "initialized"})
    
    yield
    
    await app.state.redis_pool.close()
    await engine.dispose()

def create_app() -> FastAPI:
    app = FastAPI(title="PRAXIS Realtime Agent", lifespan=lifespan)
    
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    FastAPIInstrumentor.instrument_app(app)
    
    @app.get("/health/live")
    async def health_live():
        return {"status": "ok"}
        
    @app.get("/health/ready")
    async def health_ready():
        # verify redis and db
        try:
            await app.state.redis_pool.ping()
            async with app.state.db_session_factory() as session:
                await session.execute(text("SELECT 1"))
            return {"status": "ready"}
        except Exception as e:
            from fastapi import HTTPException
            raise HTTPException(status_code=503, detail=str(e))
            
    # WebSocket Endpoint
    @app.websocket("/ws/sessions/{session_id}")
    async def websocket_session(websocket: WebSocket, session_id: str, token: str = None):
        span = trace.get_current_span()
        if span.is_recording():
            span.set_attribute("session_id", session_id)
            
        if not token:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Missing token")
            return
            
        try:
            # 1. Verify JWT
            user_payload = await verify_jwt(token, websocket.app.state.redis_pool)
            user_id = user_payload.get("sub")
            
            # 2. Verify Session ownership and fetch initial data
            async with websocket.app.state.db_session_factory() as db:
                query = text("""
                    SELECT s.id, b.summary as blueprint, c.id as candidate_id, c.full_name as candidate_name
                    FROM practice_sessions s
                    JOIN candidates c ON s.candidate_id = c.id
                    LEFT JOIN job_blueprints b ON s.job_id = b.job_id
                    WHERE s.id = :sid AND c.profile_id = :uid
                """)
                res = await db.execute(query, {"sid": session_id, "uid": user_id})
                row = res.fetchone()
                if not row:
                    await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Session not found or forbidden")
                    return
                
                # Fetch prep_pack questions from DB or generate if not exists.
                # Actually, prep_pack should already be populated by worker_tasks before session starts.
                # Let's get them from interview_prep_packs or similar if they exist. Wait, the DB model for practice_sessions doesn't have a prep_pack column, but we can query session_turns for the initial questions if they are stored there, or just generate them.
                # We'll just create the InterviewSession with the data.
                import json
                raw_bp = row.blueprint
                if isinstance(raw_bp, str):
                    try:
                        jd_blueprint = json.loads(raw_bp)
                    except:
                        jd_blueprint = {}
                else:
                    jd_blueprint = raw_bp or {}
                candidate_profile = {"id": str(row.candidate_id), "name": row.candidate_name or "Candidate"}
        except ValueError as e:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason=str(e))
            return
            
        # Sequence state for session
        # We store sequence and last state in Redis for reconnections
        session_redis_key = f"session:state:{session_id}"
        
        # Check if reconnecting
        cached_state = await websocket.app.state.redis_pool.hgetall(session_redis_key)
        
        await websocket.accept()
        
        # Initialize VAD
        from realtime_agent.app.audio.vad import VoiceActivityDetector
        vad = VoiceActivityDetector()
        
        # Initialize STT
        from praxis_ai_gateway.transcription.router import select_transcriber
        import os
        settings = {
            "LOCAL_ONLY_MODE": os.environ.get("LOCAL_ONLY_MODE", "true").lower()
        }
        transcriber = select_transcriber({}, settings, enqueue_event)
        await transcriber.connect({"language": None})
        
        # Setup DB session for logging
        db = websocket.app.state.db_session_factory()
        
        outbound_queue = asyncio.Queue(maxsize=100)
        
        async def send_worker():
            while True:
                msg = await outbound_queue.get()
                try:
                    if isinstance(msg, bytes):
                        await websocket.send_bytes(msg)
                    else:
                        await websocket.send_text(msg.model_dump_json())
                except Exception as e:
                    logger.error(f"Send worker failed: {e}")
                    break
                outbound_queue.task_done()
                
        sender_task = asyncio.create_task(send_worker())
        
        sequence = 1
        if cached_state:
            sequence = int(cached_state.get(b"sequence", b"1").decode())
        
        def enqueue_event(event: Envelope, critical: bool = False):
            nonlocal sequence
            event.sequence = sequence
            sequence += 1
            try:
                outbound_queue.put_nowait(event)
            except asyncio.QueueFull:
                if critical:
                    asyncio.create_task(outbound_queue.put(event))
                else:
                    logger.warning("Outbound queue full, dropping non-critical event")
                    
        # Initialize Manager
        from realtime_agent.app.session.manager import SessionManager
        from realtime_agent.app.session.state_machine import SessionState
        from realtime_agent.app.interview.generation import SessionGenerationManager
        from realtime_agent.app.interview.barge_in import BargeInController
        
        sm = SessionManager(session_id, db, enqueue_event)
        
        generation_manager = SessionGenerationManager()
        barge_in_controller = BargeInController(
            session_id=session_id,
            generation_manager=generation_manager,
            state_transition_cb=sm.transition,
            enqueue_event_cb=enqueue_event
        )
        
        from realtime_agent.app.interview.policy import InterviewSession
        from realtime_agent.app.session.orchestrator import SessionOrchestrator
        from realtime_agent.app.audio.tts import PiperTTSAdapter
        from praxis_ai_gateway.router import RoutingContext
        
        interview_session = InterviewSession(jd_blueprint=jd_blueprint, candidate_profile=candidate_profile)
        tts_adapter = PiperTTSAdapter()
        routing_ctx = RoutingContext(user_id=user_id)
        
        orchestrator = SessionOrchestrator(
            session=interview_session,
            generation_manager=generation_manager,
            session_manager=sm,
            gateway=websocket.app.state.gateway_router,
            routing_ctx=routing_ctx,
            tts=tts_adapter,
            enqueue_event=enqueue_event
        )

        
        # STT Background Event Receiver
        async def receive_stt_events():
            async for ev in transcriber.receive_events():
                evt_type = "transcript.partial" if ev["is_interim"] else "transcript.final"
                # Update transcript
                state_vars["current_transcript"] = ev.get("text", "")
                
                # Send to CoachingMetricsAccumulator
                orchestrator.handle_transcript_update(state_vars["current_transcript"])
                
                envelope = Envelope(
                    type=evt_type,
                    session_id=session_id,
                    sequence=0,
                    payload=ev
                )
                enqueue_event(envelope)
                
                if sm.sm.state == SessionState.AWAITING_ANSWER:
                    await orchestrator.start_candidate_turn()
                
                # Write to transcript_segments on final
                if not ev["is_interim"]:
                    async with websocket.app.state.db_session_factory() as write_db:
                        try:
                            q = text("""
                                INSERT INTO transcript_segments (session_id, role, text, start_ms, end_ms, confidence, source)
                                VALUES (:sid, 'candidate', :text, :st, :en, :conf, :src)
                            """)
                            await write_db.execute(q, {
                                "sid": session_id,
                                "text": ev["text"],
                                "st": ev["start_ms"],
                                "en": ev["end_ms"],
                                "conf": ev["confidence"],
                                "src": ev["source"]
                            })
                            await write_db.commit()
                        except Exception as e:
                            logger.error(f"Failed writing transcript segment: {e}")

        stt_task = asyncio.create_task(receive_stt_events())
        
        reconnect_task = None
        
        try:
            # Reconnect vs Fresh
            if cached_state:
                prev_state = cached_state.get(b"state", b"IDLE").decode()
                logger.info(f"Reconnected! Resuming from {prev_state}")
                sm.sm.state = SessionState(prev_state) # Force internal state to prev
                
                if prev_state == SessionState.RECONNECTING.value:
                    await sm.transition(SessionState.READY, reason="reconnected")
                else:
                    # Depending on state machine, maybe we can just jump directly
                    # or we assume we are recovering
                    await sm.transition(SessionState(prev_state), reason="reconnected")
            else:
                await sm.transition(SessionState.PREFLIGHT)
                # Client would do checks, then we go to WARMING
                await sm.transition(SessionState.WARMING)
                # Then READY
                await sm.transition(SessionState.READY)
                
                # Start the interview for fresh session
                asyncio.create_task(orchestrator.begin_interviewer_turn())
                
            import time
            tracer = trace.get_tracer(__name__)
            
            vad_speech_start_ts = None
            vad_speech_end_ts = None
            state_vars = {"current_transcript": "", "turn_completed": False}
            
            while True:
                message = await websocket.receive()
                if "bytes" in message:
                    ingest_ts = time.perf_counter()
                    pcm_data = message["bytes"]
                    frame_len = len(pcm_data)
                    
                    ack_evt = Envelope(
                        type="audio.frame_ack",
                        session_id=session_id,
                        sequence=0, # populated by enqueue
                        payload={"length": frame_len, "server_seq": sequence}
                    )
                    enqueue_event(ack_evt)
                    
                    # Feed audio to STT
                    await transcriber.send_audio(pcm_data)
                    
                    # Process VAD
                    with tracer.start_as_current_span("vad_process") as span:
                        res, evt = vad.process_frame(pcm_data)
                        vad_ts = time.perf_counter()
                        span.set_attribute("latency_ms", (vad_ts - ingest_ts) * 1000)
                        
                        if evt:
                            # Push event
                            vad_envelope = Envelope(
                                type=evt,
                                session_id=session_id,
                                sequence=0,
                                payload={"confidence": res["confidence"], "energy_db": res["energy_db"]}
                            )
                            enqueue_event(vad_envelope)
                            
                            # Send to CoachingMetricsAccumulator
                            orchestrator.handle_vad_event(evt)
                            
                            # Task 5: Barge-in trigger
                            if evt == "speech_start":
                                vad_speech_start_ts = time.perf_counter()
                                vad_speech_end_ts = None
                                if sm.sm.state == SessionState.AWAITING_ANSWER:
                                    await orchestrator.start_candidate_turn()
                                elif sm.sm.state == SessionState.INTERVIEWER_TURN:
                                    logger.info("VAD detected speech during INTERVIEWER_TURN, triggering barge-in")
                                    await barge_in_controller.trigger(reason="vad_speech_detected")
                            
                            elif evt == "speech_end":
                                vad_speech_end_ts = time.perf_counter()
                                await transcriber.signal_segment_end()
                                
                    # If we are in AWAITING_ANSWER or CANDIDATE_TURN and speech has ended, track silence
                    if sm.sm.state in (SessionState.AWAITING_ANSWER, SessionState.CANDIDATE_TURN) and vad_speech_end_ts:
                        silence_ms = (time.perf_counter() - vad_speech_end_ts) * 1000
                        
                        # Call handle_vad_silence (it checks if it should call on_candidate_turn_end)
                        await orchestrator.handle_vad_silence(silence_ms, state_vars["current_transcript"])
                        
                        # If transition occurred, reset tracking
                        if sm.sm.state not in (SessionState.AWAITING_ANSWER, SessionState.CANDIDATE_TURN):
                            vad_speech_end_ts = None
                            state_vars["current_transcript"] = ""
                                
                elif "text" in message:
                    try:
                        import json
                        evt_data = json.loads(message["text"])
                        evt_type = evt_data.get("type")
                        logger.info(f"Received text event: {evt_type}")
                        
                        if evt_type == "audio.playback_stopped":
                            # Task 3: Client confirmation
                            payload = evt_data.get("payload", {})
                            reason = payload.get("reason", "unknown")
                            trigger_ts = payload.get("trigger_ts")
                            
                            logger.info(f"Received audio.playback_stopped confirmation. Reason: {reason}")
                            
                            # Complete the barge-in latency measurement chain
                            if reason == "vad_speech_detected" and vad_speech_start_ts and trigger_ts:
                                # We compute the end-to-end chain
                                conf_ts = time.perf_counter()
                                # trigger_ts from client is probably in different clock, but if it passes server time:
                                # For our test, we'll just measure from our own vad_speech_start_ts
                                latency = (conf_ts - vad_speech_start_ts) * 1000
                                logger.info(f"--- BARGE-IN LATENCY CHAIN COMPLETED ---")
                                logger.info(f"End-to-End Latency: {latency:.2f} ms")
                        
                        elif evt_type == "session.end":
                            logger.info("Client explicitly requested session end")
                            await orchestrator.end_session_and_debrief()
                                
                    except Exception as e:
                        logger.error(f"Failed to process text message: {e}")
                    
        except WebSocketDisconnect:
            logger.info("Client disconnected normally")
        except Exception as e:
            logger.error(f"WS error: {e}")
        finally:
            sender_task.cancel()
            stt_task.cancel()
            await transcriber.close()
            
            # The websocket dropped or finished.
            # Are we cleanly STOPPED or FAILED?
            if sm.sm.state not in (SessionState.STOPPED, SessionState.FAILED):
                # Network drop mid-session
                try:
                    await sm.transition(SessionState.RECONNECTING, reason="websocket_dropped")
                    # Hold in Redis for 30s
                    await websocket.app.state.redis_pool.hset(session_redis_key, mapping={
                        "state": sm.sm.state.value,
                        "sequence": sequence
                    })
                    await websocket.app.state.redis_pool.expire(session_redis_key, 30)
                    
                    # We spawn a background task to check if it reconnects
                    async def reap_if_not_reconnected():
                        await asyncio.sleep(30)
                        # Check if key still exists and hasn't been picked up/updated
                        # Actually, if reconnected, the TTL is refreshed or key is read.
                        # We can just check if state is still RECONNECTING.
                        async with websocket.app.state.db_session_factory() as cleanup_db:
                            sm_reap = SessionManager(session_id, cleanup_db, lambda *args, **kwargs: None)
                            sm_reap.sm.state = SessionState.RECONNECTING
                            curr_state = await websocket.app.state.redis_pool.hget(session_redis_key, "state")
                            if curr_state and curr_state.decode() == SessionState.RECONNECTING.value:
                                await sm_reap.transition(SessionState.FAILED, reason="reconnection_timeout")
                                await websocket.app.state.redis_pool.delete(session_redis_key)
                                
                                # Update DB status
                                query = text("UPDATE practice_sessions SET status = 'failed', ended_at = NOW() WHERE id = :sid")
                                await cleanup_db.execute(query, {"sid": session_id})
                                await cleanup_db.commit()
                                
                    asyncio.create_task(reap_if_not_reconnected())
                except Exception as e:
                    logger.error(f"Failed to handle reconnect logic: {e}")
            else:
                # Cleanly ended
                try:
                    query = text("UPDATE practice_sessions SET status = 'completed', ended_at = CURRENT_TIMESTAMP WHERE id = :sid")
                    await db.execute(query, {"sid": session_id})
                    await db.commit()
                except Exception as e:
                    logger.error(f"Failed to update session status on clean end: {e}")
                    
            await db.close()
            
    return app

app = create_app()
