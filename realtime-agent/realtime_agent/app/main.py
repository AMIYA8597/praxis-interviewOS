"""
PRAXIS realtime agent: one WebSocket per live practice session.

Protocol summary
----------------
* Connect:  /ws/sessions/{session_id}?token=<JWT>   (preferred), or connect
  without the query param and send {"type": "auth", "token": "<JWT>"} as the
  first text frame within WS_AUTH_TIMEOUT_S (desktop client behaviour).
  The JWT is cryptographically verified (backend.app.auth.verify_jwt) and the
  session must belong to the caller's candidate.
* Binary frames: 16-bit PCM audio. Text frames: JSON {"type": ..., "payload": {...}}.
  Malformed frames get a `session.error` event; the session keeps running.
* Close codes: 4401 auth failed, 4404 session not found / not yours,
  4409 session already finished, 4400 bad request, 1011 internal error.
* Disconnect: the live state is saved in Redis (`session:state:<id>`) for
  WS_RECONNECT_GRACE_S. Reconnecting within the grace period resumes the
  session (same sequence numbers, same question); otherwise it is marked failed.
"""
import asyncio
import json
import logging
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from opentelemetry import trace
from redis.asyncio import Redis
from sqlalchemy import text

from backend.app.auth import AuthError, AuthProviderUnavailable, verify_jwt
from backend.app.core.bootstrap import build_gateway, configure_logging, configure_tracing
from backend.app.core.context import bind
from backend.app.db.session import create_engine, create_session_factory
from packages.config.settings import settings
from realtime_agent.app.protocol import Envelope

logger = logging.getLogger("praxis.realtime")

WS_AUTH_FAILED = 4401
WS_NOT_FOUND = 4404
WS_CONFLICT = 4409
WS_BAD_REQUEST = 4400
WS_INTERNAL = 1011
MAX_TEXT_FRAME = 64 * 1024
TERMINAL_DB_STATUSES = {"completed", "abandoned", "failed"}


def _s(value: Any) -> Optional[str]:
    if value is None:
        return None
    return value.decode() if isinstance(value, (bytes, bytearray)) else str(value)


def _state_key(session_id: str) -> str:
    return f"session:state:{session_id}"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Re-read the environment at startup (process managers/tests may set it after import).
    from packages.config.settings import Settings

    cfg = Settings()
    configure_logging(cfg, "praxis-realtime-agent")
    configure_tracing(cfg, "praxis-realtime-agent")

    engine = create_engine(cfg)
    app.state.db_engine = engine
    app.state.db_session_factory = create_session_factory(engine)
    app.state.redis_pool = Redis.from_url(
        cfg.REDIS_URL,
        decode_responses=True,
        max_connections=cfg.REDIS_MAX_CONNECTIONS,
        socket_timeout=cfg.REDIS_SOCKET_TIMEOUT_S,
    )
    app.state.gateway_router = build_gateway(cfg, app.state.redis_pool, app.state.db_session_factory)
    app.state.active_connections = 0
    logger.info("realtime_agent_ready", extra={"providers": sorted(app.state.gateway_router.providers)})
    try:
        yield
    finally:
        try:
            await app.state.redis_pool.aclose()
        except Exception:
            pass
        await engine.dispose()
        logger.info("realtime_agent_stopped")


async def _authenticate(websocket: WebSocket, query_token: Optional[str]) -> Dict[str, Any]:
    """Return verified claims. Uses the query token, or a first-frame auth message."""
    token = query_token
    if not token:
        await websocket.accept()
        try:
            raw = await asyncio.wait_for(websocket.receive_text(), timeout=settings.WS_AUTH_TIMEOUT_S)
            msg = json.loads(raw) if len(raw) <= MAX_TEXT_FRAME else {}
        except (asyncio.TimeoutError, json.JSONDecodeError, WebSocketDisconnect, RuntimeError, KeyError):
            raise AuthError("Missing token", reason="no_auth_message")
        if not isinstance(msg, dict) or msg.get("type") != "auth" or not msg.get("token"):
            raise AuthError("Missing token", reason="no_auth_message")
        token = str(msg["token"])
    return await verify_jwt(token, websocket.app.state.redis_pool)


async def _load_session(factory, session_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    """Ownership-checked lookup. Optional enrichment never blocks the session."""
    async with factory() as db:
        row = (
            await db.execute(
                text("""
                    SELECT s.id, s.status, s.candidate_id
                    FROM practice_sessions s
                    JOIN candidates c ON s.candidate_id = c.id
                    WHERE s.id = :sid AND c.profile_id = :uid
                """),
                {"sid": session_id, "uid": user_id},
            )
        ).first()
        if row is None:
            return None
        info: Dict[str, Any] = {
            "status": row.status,
            "candidate_id": str(row.candidate_id),
            "candidate_name": "Candidate",
            "jd_blueprint": {},
        }
        try:
            extra = (
                await db.execute(
                    text("""
                        SELECT c.full_name, b.summary, b.likely_topics, b.prep_pack,
                               s.difficulty, s.interview_type
                        FROM practice_sessions s
                        JOIN candidates c ON s.candidate_id = c.id
                        LEFT JOIN job_blueprints b ON s.job_id = b.job_id
                        WHERE s.id = :sid
                    """),
                    {"sid": session_id},
                )
            ).first()
            if extra is not None:
                info["candidate_name"] = extra.full_name or "Candidate"
                prep = extra.prep_pack
                if isinstance(prep, str):
                    try:
                        prep = json.loads(prep)
                    except ValueError:
                        prep = []
                info["jd_blueprint"] = {
                    "summary": extra.summary,
                    "likely_topics": list(extra.likely_topics or []),
                    "prep_pack": prep if isinstance(prep, list) else [],
                }
                info["difficulty"] = extra.difficulty
                info["interview_type"] = extra.interview_type
        except Exception as e:
            logger.info("session_enrichment_unavailable", extra={"error_type": type(e).__name__})
            await db.rollback()
        return info


async def _mark_status(factory, session_id: str, status: str, user_id: str, *, started: bool = False, ended: bool = False) -> None:
    sets = ["status = :st"]
    if started:
        sets.append("started_at = COALESCE(started_at, CURRENT_TIMESTAMP)")
    if ended:
        sets.append("ended_at = CURRENT_TIMESTAMP")
    try:
        async with factory() as db:
            claims = json.dumps({"sub": user_id})
            await db.execute(text("SELECT set_config('request.jwt.claims', :claims, true)"), {"claims": claims})
            await db.execute(text(f"UPDATE practice_sessions SET {', '.join(sets)} WHERE id = CAST(:sid AS uuid)"), {"st": status, "sid": session_id})
            await db.commit()
    except Exception as e:
        # Older/test schemas may lack started_at; fall back to status only.
        logger.warning("session_status_update_failed", extra={"session_id": session_id, "error_type": type(e).__name__})
        if started or ended:
            await _mark_status(factory, session_id, status, user_id)


def create_app() -> FastAPI:
    app = FastAPI(title="PRAXIS Realtime Agent", lifespan=lifespan)

    if settings.otel_enabled:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor.instrument_app(app)

    @app.get("/health/live")
    async def health_live():
        return {"status": "ok"}

    @app.get("/health/ready")
    async def health_ready():
        try:
            await app.state.redis_pool.ping()
            async with app.state.db_session_factory() as session:
                await session.execute(text("SELECT 1"))
            return {"status": "ready", "active_connections": app.state.active_connections}
        except Exception as e:
            return JSONResponse(status_code=503, content={"status": "not_ready", "reason": type(e).__name__})

    @app.websocket("/ws/sessions/{session_id}")
    async def websocket_session(websocket: WebSocket, session_id: str, token: str = None):
        await _run_session(websocket, session_id, token)

    return app


async def _close(websocket: WebSocket, code: int, reason: str) -> None:
    try:
        await websocket.close(code=code, reason=reason)
    except Exception:
        pass


async def _run_session(websocket: WebSocket, session_id: str, token: Optional[str]) -> None:
    app = websocket.app
    connected_at = time.monotonic()
    bind(session_id=session_id)
    span = trace.get_current_span()
    if span.is_recording():
        span.set_attribute("session_id", session_id)

    try:
        uuid.UUID(session_id)
    except ValueError:
        await _close(websocket, WS_BAD_REQUEST, "Invalid session id")
        return

    # ── 1. Authenticate (never trust the client) ────────────────────────
    try:
        claims = await _authenticate(websocket, token)
    except AuthProviderUnavailable:
        logger.error("ws_auth_provider_unavailable", extra={"session_id": session_id})
        await _close(websocket, WS_INTERNAL, "Authentication unavailable")
        return
    except AuthError as e:
        logger.info("ws_auth_rejected", extra={"session_id": session_id, "reason": getattr(e, "reason", "invalid")})
        await _close(websocket, WS_AUTH_FAILED, "Invalid or expired session")
        return
    except Exception as e:
        logger.exception("ws_auth_error", extra={"session_id": session_id, "error_type": type(e).__name__})
        await _close(websocket, WS_INTERNAL, "Internal error")
        return
    user_id = str(claims.get("sub"))
    bind(user_id=user_id)

    # ── 2. Authorize: session must belong to the caller ─────────────────
    factory = app.state.db_session_factory
    try:
        info = await _load_session(factory, session_id, user_id)
    except Exception as e:
        logger.error("ws_session_lookup_failed", extra={"session_id": session_id, "error_type": type(e).__name__})
        await _close(websocket, WS_INTERNAL, "Internal error")
        return
    if info is None:
        await _close(websocket, WS_NOT_FOUND, "Session not found or forbidden")
        return
    if info["status"] in TERMINAL_DB_STATUSES:
        await _close(websocket, WS_CONFLICT, f"Session already {info['status']}")
        return
    bind(candidate_id=info["candidate_id"])

    redis = app.state.redis_pool
    state_key = _state_key(session_id)
    try:
        cached_state = await redis.hgetall(state_key)
    except Exception as e:
        logger.warning("ws_reconnect_state_unavailable", extra={"error_type": type(e).__name__})
        cached_state = {}
    cached = {_s(k): _s(v) for k, v in (cached_state or {}).items()}
    is_reconnect = cached.get("state") == "RECONNECTING"
    conn_id = uuid.uuid4().hex

    if websocket.client_state.name != "CONNECTED":
        await websocket.accept()
    app.state.active_connections += 1
    logger.info("ws_connected", extra={"session_id": session_id, "reconnect": is_reconnect})

    # ── 3. Outbound queue with monotonically increasing sequence numbers ─
    outbound_queue: asyncio.Queue = asyncio.Queue(maxsize=200)
    seq = {"next": int(cached.get("sequence") or 1)}

    def enqueue_event(event, critical: bool = False):
        if isinstance(event, Envelope):
            event.sequence = seq["next"]
            seq["next"] += 1
        try:
            outbound_queue.put_nowait(event)
        except asyncio.QueueFull:
            if critical:
                asyncio.create_task(outbound_queue.put(event))
            else:
                logger.warning("ws_outbound_queue_full_dropped", extra={"session_id": session_id})

    def send_error(code: str, message: str) -> None:
        enqueue_event(Envelope(type="session.error", session_id=session_id, sequence=0, payload={"code": code, "message": message}), critical=True)

    async def send_worker():
        while True:
            msg = await outbound_queue.get()
            try:
                if isinstance(msg, (bytes, bytearray)):
                    await websocket.send_bytes(bytes(msg))
                else:
                    await websocket.send_text(msg.model_dump_json())
            except Exception as e:
                logger.info("ws_send_stopped", extra={"session_id": session_id, "error_type": type(e).__name__})
                break
            finally:
                outbound_queue.task_done()

    sender_task = asyncio.create_task(send_worker())

    # ── 4. Session components ───────────────────────────────────────────
    from praxis_ai_gateway.router import RoutingContext
    from realtime_agent.app.audio.tts import PiperTTSAdapter
    from realtime_agent.app.audio.vad import VoiceActivityDetector
    from realtime_agent.app.interview.barge_in import BargeInController
    from realtime_agent.app.interview.generation import SessionGenerationManager
    from realtime_agent.app.interview.policy import InterviewSession
    from realtime_agent.app.session.manager import SessionManager
    from realtime_agent.app.session.orchestrator import SessionOrchestrator
    from realtime_agent.app.session.state_machine import SessionState

    db = factory()
    try:
        import json
        claims_json = json.dumps({"sub": user_id})
        await db.execute(text("SELECT set_config('request.jwt.claims', :claims, true)"), {"claims": claims_json})
    except Exception as e:
        logger.error("ws_session_set_config_failed", extra={"session_id": session_id, "error_type": type(e).__name__})
        await db.close()
        await _close(websocket, WS_INTERNAL, "Internal error")
        return

    sm = SessionManager(session_id, db, enqueue_event)
    generation_manager = SessionGenerationManager()
    barge_in_controller = BargeInController(
        session_id=session_id,
        generation_manager=generation_manager,
        state_transition_cb=sm.transition,
        enqueue_event_cb=enqueue_event,
    )
    interview_kwargs = {k: info[k] for k in ("difficulty", "interview_type") if info.get(k)}
    interview_session = InterviewSession(
        jd_blueprint=info["jd_blueprint"],
        candidate_profile={"id": info["candidate_id"], "name": info["candidate_name"]},
        **interview_kwargs,
    )
    orchestrator = SessionOrchestrator(
        session=interview_session,
        generation_manager=generation_manager,
        session_manager=sm,
        gateway=app.state.gateway_router,
        routing_ctx=RoutingContext(user_id=user_id, session_id=session_id),
        tts=PiperTTSAdapter(),
        enqueue_event=enqueue_event,
    )
    if is_reconnect:
        orchestrator.restore(cached)

    vad = VoiceActivityDetector()
    state_vars = {"current_transcript": "", "speech_end_ts": None, "speech_start_ts": None}
    background: list = []

    transcriber = None  # connected after the start/resume handshake (see step 5)

    async def receive_stt_events():
        try:
            async for ev in transcriber.receive_events():
                state_vars["current_transcript"] = ev.get("text", "") or ""
                orchestrator.handle_transcript_update(state_vars["current_transcript"])
                enqueue_event(
                    Envelope(
                        type="transcript.partial" if ev.get("is_interim") else "transcript.final",
                        session_id=session_id,
                        sequence=0,
                        payload=ev,
                    )
                )
                if sm.sm.state == SessionState.AWAITING_ANSWER:
                    await orchestrator.start_candidate_turn()
                if not ev.get("is_interim"):
                    orchestrator.record_final_segment(ev)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            orchestrator._degraded("stt", e)

    async def no_answer_watchdog():
        """Nudge, then skip, when the candidate stays silent after a question."""
        while True:
            await asyncio.sleep(1.0)
            try:
                since = orchestrator.awaiting_since
                if (
                    sm.sm.state == SessionState.AWAITING_ANSWER
                    and since is not None
                    and state_vars["speech_start_ts"] is None
                    and time.monotonic() - since >= settings.TURN_NO_ANSWER_TIMEOUT_S
                ):
                    await orchestrator.handle_no_answer_timeout(settings.TURN_MAX_NUDGES)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error("no_answer_watchdog_error", extra={"error_type": type(e).__name__})

    def spawn(coro, name: str):
        async def _guard():
            try:
                await coro
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.exception("session_task_failed", extra={"task": name, "error_type": type(e).__name__})
                send_error("internal", "A session step failed; the interview will continue.")

        t = asyncio.create_task(_guard())
        background.append(t)
        return t

    close_reason = "client_disconnect"
    try:
        # ── 5. Start or resume ──────────────────────────────────────────
        if is_reconnect:
            sm.sm.state = SessionState.RECONNECTING
            # Claim the session so a pending reaper for the old socket backs off.
            await redis.hset(state_key, mapping={"state": "ACTIVE", "conn_id": conn_id})
            await sm.transition(SessionState.READY, reason="reconnected")
            if orchestrator.last_interviewer_question:
                enqueue_event(
                    Envelope(type="interviewer.text", session_id=session_id, sequence=0,
                             payload={"text": orchestrator.last_interviewer_question, "repeat": True}),
                    critical=True,
                )
                await sm.transition(SessionState.INTERVIEWER_TURN, reason="resume")
                await orchestrator._transition(SessionState.AWAITING_ANSWER, reason="resume")
            else:
                spawn(orchestrator.begin_interviewer_turn(), "begin_interviewer_turn")
        else:
            await _mark_status(factory, session_id, "active", user_id, started=True)
            await sm.transition(SessionState.PREFLIGHT)
            await sm.transition(SessionState.WARMING)
            await sm.transition(SessionState.READY)
            spawn(orchestrator.begin_interviewer_turn(), "begin_interviewer_turn")

        # Speech-to-text (degrades gracefully: without STT the client can send
        # `candidate.text_answer` frames and the interview continues text-only).
        try:
            from praxis_ai_gateway.transcription.router import select_transcriber

            transcriber = select_transcriber({}, {"LOCAL_ONLY_MODE": str(settings.LOCAL_ONLY_MODE).lower()}, enqueue_event)
            await transcriber.connect({"language": None})
            background.append(asyncio.create_task(receive_stt_events()))
        except Exception as e:
            transcriber = None
            orchestrator._degraded("stt", e)
        background.append(asyncio.create_task(no_answer_watchdog()))

        tracer = trace.get_tracer(__name__)

        # ── 6. Receive loop ─────────────────────────────────────────────
        while True:
            message = await websocket.receive()
            mtype = message.get("type")
            if mtype == "websocket.disconnect":
                break

            if message.get("bytes") is not None:
                raw_bytes = message["bytes"]
                if len(raw_bytes) < 18:
                    send_error("malformed_audio_frame", "Binary frame is too small for header")
                    continue
                import struct
                try:
                    proto_ver, frame_type, client_seq, capture_ts, payload_len = struct.unpack(">BBIdI", raw_bytes[:18])
                except Exception:
                    send_error("malformed_audio_frame", "Failed to parse binary header")
                    continue
                if proto_ver != 1:
                    send_error("unsupported_protocol", f"Unsupported protocol version: {proto_ver}")
                    continue
                if payload_len > 1024 * 1024:
                    send_error("oversized_frame", "Audio frame payload exceeds maximum size")
                    continue
                pcm = raw_bytes[18:]
                if len(pcm) != payload_len:
                    send_error("malformed_audio_frame", "Payload length mismatch")
                    continue
                    
                enqueue_event(Envelope(type="audio.frame_ack", session_id=session_id, sequence=0,
                                       payload={"length": len(pcm), "client_seq": client_seq, "server_seq": seq["next"]}))
                if transcriber is not None:
                    try:
                        await transcriber.send_audio(pcm)
                    except Exception as e:
                        orchestrator._degraded("stt", e)
                try:
                    with tracer.start_as_current_span("vad_process"):
                        res, evt = vad.process_frame(pcm)
                except Exception as e:
                    orchestrator._degraded("vad", e)
                    continue
                if evt:
                    enqueue_event(Envelope(type=evt, session_id=session_id, sequence=0,
                                           payload={"confidence": res.get("confidence"), "energy_db": res.get("energy_db")}))
                    orchestrator.handle_vad_event(evt)
                    if evt == "speech_start":
                        state_vars["speech_start_ts"] = time.perf_counter()
                        state_vars["speech_end_ts"] = None
                        if sm.sm.state == SessionState.AWAITING_ANSWER:
                            await orchestrator.start_candidate_turn()
                        elif sm.sm.state == SessionState.INTERVIEWER_TURN:
                            await barge_in_controller.trigger(reason="vad_speech_detected")
                    elif evt == "speech_end":
                        state_vars["speech_end_ts"] = time.perf_counter()
                        if transcriber is not None:
                            try:
                                await transcriber.signal_segment_end()
                            except Exception as e:
                                orchestrator._degraded("stt", e)

                if sm.sm.state in (SessionState.AWAITING_ANSWER, SessionState.CANDIDATE_TURN) and state_vars["speech_end_ts"]:
                    silence_ms = (time.perf_counter() - state_vars["speech_end_ts"]) * 1000
                    await orchestrator.handle_vad_silence(silence_ms, state_vars["current_transcript"])
                    if sm.sm.state not in (SessionState.AWAITING_ANSWER, SessionState.CANDIDATE_TURN):
                        state_vars.update(current_transcript="", speech_end_ts=None, speech_start_ts=None)
                continue

            raw = message.get("text")
            if raw is None:
                continue
            if len(raw) > MAX_TEXT_FRAME:
                send_error("frame_too_large", "Text frame exceeds 64KB")
                continue
            try:
                evt_data = json.loads(raw)
                if not isinstance(evt_data, dict):
                    raise ValueError("frame must be a JSON object")
            except ValueError:
                send_error("malformed_message", "Expected a JSON object")
                continue

            evt_type = evt_data.get("type")
            payload = evt_data.get("payload") if isinstance(evt_data.get("payload"), dict) else {}
            if evt_type == "auth":
                continue  # already authenticated; ignore duplicate auth frames
            elif evt_type == "audio.playback_stopped":
                if payload.get("reason") == "vad_speech_detected" and state_vars["speech_start_ts"]:
                    latency = (time.perf_counter() - state_vars["speech_start_ts"]) * 1000
                    logger.info("barge_in_latency", extra={"session_id": session_id, "latency_ms": round(latency, 1)})
            elif evt_type == "session.end":
                close_reason = "client_end"
                spawn(orchestrator.end_session_and_debrief(), "end_session")
            elif evt_type == "session.pause":
                if not await sm.try_transition(SessionState.PAUSED, reason="client_pause"):
                    send_error("invalid_state", f"Cannot pause from {sm.sm.state.value}")
            elif evt_type == "session.resume":
                if sm.sm.state == SessionState.PAUSED:
                    await orchestrator._transition(SessionState.AWAITING_ANSWER, reason="client_resume")
            elif evt_type == "candidate.text_answer":
                # Text-mode answer (e.g. STT degraded): treat as a complete turn.
                answer = str(payload.get("text", ""))[:10_000]
                if sm.sm.state == SessionState.AWAITING_ANSWER:
                    await orchestrator.start_candidate_turn()
                if sm.sm.state == SessionState.CANDIDATE_TURN:
                    spawn(orchestrator.on_candidate_turn_end(final_text=answer), "text_answer")
            else:
                send_error("unknown_message_type", f"Unsupported message type: {str(evt_type)[:50]}")

    except WebSocketDisconnect:
        pass
    except Exception as e:
        close_reason = "server_error"
        logger.exception("ws_session_error", extra={"session_id": session_id, "error_type": type(e).__name__})
    finally:
        app.state.active_connections = max(0, app.state.active_connections - 1)
        for t in background:
            t.cancel()
        if transcriber is not None:
            try:
                await transcriber.close()
            except Exception:
                pass
        # Let queued events (e.g. debrief.ready) drain briefly before stopping the sender.
        try:
            await asyncio.wait_for(outbound_queue.join(), timeout=1.0)
        except Exception:
            pass
        sender_task.cancel()

        final_state = sm.sm.state
        # DEBRIEF counts as finished: the interview is over even if the debrief is still
        # being generated (POST /sessions/{id}/end can regenerate it).
        if final_state in (SessionState.STOPPED, SessionState.FAILED, SessionState.DEBRIEF):
            await _mark_status(factory, session_id, "failed" if final_state == SessionState.FAILED else "completed", user_id, ended=True)
            try:
                await redis.delete(state_key)
            except Exception:
                pass
        else:
            await _save_for_reconnect(app, sm, orchestrator, session_id, state_key, conn_id, seq["next"], final_state, user_id)
        try:
            await db.close()
        except Exception:
            pass
        logger.info(
            "ws_disconnected",
            extra={
                "session_id": session_id,
                "reason": close_reason,
                "final_state": final_state.value,
                "duration_s": round(time.monotonic() - connected_at, 1),
            },
        )


async def _save_for_reconnect(app, sm, orchestrator, session_id, state_key, conn_id, next_seq, final_state, user_id: str) -> None:
    """Persist resumable state and schedule failure if the client never returns."""
    from realtime_agent.app.session.manager import SessionManager
    from realtime_agent.app.session.state_machine import SessionState

    redis = app.state.redis_pool
    grace = settings.WS_RECONNECT_GRACE_S
    try:
        await sm.try_transition(SessionState.RECONNECTING, reason="websocket_dropped")
        await redis.hset(
            state_key,
            mapping={
                "state": "RECONNECTING",
                "resume_from": final_state.value,
                "sequence": next_seq,
                "conn_id": conn_id,
                **{k: str(v) for k, v in orchestrator.snapshot().items()},
            },
        )
        # Keep the key past the grace period so the reaper can read it.
        await redis.expire(state_key, grace + 60)
    except Exception as e:
        logger.error("ws_reconnect_save_failed", extra={"session_id": session_id, "error_type": type(e).__name__})
        return

    async def reap_if_not_reconnected():
        await asyncio.sleep(grace)
        try:
            data = {_s(k): _s(v) for k, v in (await redis.hgetall(state_key) or {}).items()}
            # Only fail it if nobody reconnected (a new socket rewrites state/conn_id).
            if data.get("state") != "RECONNECTING" or data.get("conn_id") != conn_id:
                return
            async with app.state.db_session_factory() as cleanup_db:
                claims_json = json.dumps({"sub": user_id})
                await cleanup_db.execute(text("SELECT set_config('request.jwt.claims', :claims, true)"), {"claims": claims_json})
                reaper = SessionManager(session_id, cleanup_db, lambda *a, **k: None)
                reaper.sm.state = SessionState.RECONNECTING
                await reaper.try_transition(SessionState.FAILED, reason="reconnection_timeout")
            await _mark_status(app.state.db_session_factory, session_id, "failed", user_id, ended=True)
            await redis.delete(state_key)
            logger.info("session_reaped", extra={"session_id": session_id})
        except Exception as e:
            logger.error("session_reaper_failed", extra={"session_id": session_id, "error_type": type(e).__name__})

    asyncio.create_task(reap_if_not_reconnected())


app = create_app()
