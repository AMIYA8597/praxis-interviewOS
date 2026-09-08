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
    engine = create_async_engine(DATABASE_URL, pool_size=20, max_overflow=10)
    app.state.db_session_factory = async_sessionmaker(engine, expire_on_commit=False)
    
    # Setup Redis
    app.state.redis_pool = Redis.from_url(REDIS_URL)
    
    logger.info({"event": "realtime_agent_ready", "db": "connected", "redis": "connected"})
    
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
            
            # 2. Verify Session ownership
            async with websocket.app.state.db_session_factory() as db:
                query = text("""
                    SELECT s.id 
                    FROM practice_sessions s
                    JOIN candidates c ON s.candidate_id = c.id
                    WHERE s.id = :sid AND c.profile_id = :uid
                """)
                res = await db.execute(query, {"sid": session_id, "uid": user_id})
                if not res.scalar():
                    await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Session not found or forbidden")
                    return
        except ValueError as e:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason=str(e))
            return
            
        # Sequence state for session
        # We store sequence and last state in Redis for reconnections
        session_redis_key = f"session:state:{session_id}"
        
        # Check if reconnecting
        cached_state = await websocket.app.state.redis_pool.hgetall(session_redis_key)
        
        await websocket.accept()
        
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
        
        sm = SessionManager(session_id, db, enqueue_event)
        
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
                
            while True:
                message = await websocket.receive()
                if "bytes" in message:
                    frame_len = len(message["bytes"])
                    ack_evt = Envelope(
                        type="audio.frame_ack",
                        session_id=session_id,
                        sequence=0, # populated by enqueue
                        payload={"length": frame_len, "server_seq": sequence}
                    )
                    enqueue_event(ack_evt)
                elif "text" in message:
                    pass
                    
        except WebSocketDisconnect:
            logger.info("Client disconnected normally")
        except Exception as e:
            logger.error(f"WS error: {e}")
        finally:
            sender_task.cancel()
            
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
                    query = text("UPDATE practice_sessions SET status = 'completed', ended_at = NOW() WHERE id = :sid")
                    await db.execute(query, {"sid": session_id})
                    await db.commit()
                except Exception as e:
                    logger.error(f"Failed to update session status on clean end: {e}")
                    
            await db.close()
            
    return app

app = create_app()
