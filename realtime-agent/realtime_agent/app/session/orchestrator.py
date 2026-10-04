"""
Drives one live interview: interviewer turn -> await answer -> score -> next.

Failure isolation: every AI call (policy, classifier, scoring, claims,
memory compression, TTS, debrief) and every DB write is wrapped. A single
failure degrades the session (a `session.degraded` event is emitted and a
safe fallback is used) instead of killing the WebSocket loop.
"""
import asyncio
import json
import logging
import time
import uuid
from typing import Any, Callable, Dict, List, Optional

from sqlalchemy import text

from praxis_ai_gateway.router import GatewayRouter, RoutingContext
from realtime_agent.app.audio.tts import PiperTTSAdapter
from realtime_agent.app.interview.generation import SessionGenerationManager
from realtime_agent.app.interview.policy import InterviewSession, PolicyDecision
from realtime_agent.app.protocol import Envelope
from realtime_agent.app.scoring.claims import process_candidate_answer_claims
from realtime_agent.app.scoring.service import score_answer_async
from realtime_agent.app.session.manager import SessionManager
from realtime_agent.app.session.state_machine import InvalidTransitionError, SessionState

logger = logging.getLogger(__name__)

FALLBACK_QUESTION = "Let's keep going. Can you walk me through a recent project you're proud of and your specific role in it?"
NUDGE_TEXT = "Take your time. Would you like me to rephrase the question, or shall we move on?"


class SessionOrchestrator:
    def __init__(
        self,
        session: InterviewSession,
        generation_manager: SessionGenerationManager,
        session_manager: SessionManager,
        gateway: GatewayRouter,
        routing_ctx: RoutingContext,
        tts: PiperTTSAdapter,
        enqueue_event: Callable[[Any], None],
    ):
        self.session = session
        self.generation_manager = generation_manager
        self.session_manager = session_manager
        self.gateway = gateway
        self.routing_ctx = routing_ctx
        self.tts = tts
        self.enqueue_event = enqueue_event

        self.current_candidate_answer = ""
        self.last_interviewer_question = ""
        self.last_interviewer_turn_id: Optional[str] = None
        self.awaiting_since: Optional[float] = None
        self.nudges_sent = 0
        self.degraded_components: set = set()
        self._pending_segments: List[Dict[str, Any]] = []
        self._turn_lock = asyncio.Lock()

        from realtime_agent.app.interview.turn_detection import TurnEndDetector

        self.turn_detector = TurnEndDetector(router=self.gateway)
        from praxis_ai_gateway.classification import FastClassifier

        self.classifier = FastClassifier(router=self.gateway)

        from realtime_agent.app.coaching.accumulator import CoachingMetricsAccumulator

        self.coaching = CoachingMetricsAccumulator(
            session_id=self.session_manager.session_id,
            enqueue_event_cb=lambda env, critical=False: self.enqueue_event(env, critical=critical),
        )

    # ── helpers ─────────────────────────────────────────────────────────
    @property
    def session_id(self) -> str:
        return self.session_manager.session_id

    def _state(self) -> Optional[SessionState]:
        machine = getattr(self.session_manager, "sm", None)
        state = getattr(machine, "state", None)
        return state if isinstance(state, SessionState) else None

    async def _transition(self, state: SessionState, reason: str = "") -> bool:
        try:
            if reason:
                await self.session_manager.transition(state, reason=reason)
            else:
                await self.session_manager.transition(state)
            if state == SessionState.AWAITING_ANSWER:
                self.awaiting_since = time.monotonic()
            return True
        except InvalidTransitionError as e:
            logger.warning("orchestrator_invalid_transition", extra={"session_id": self.session_id, "error": str(e)})
            return False

    def _degraded(self, component: str, error: BaseException) -> None:
        """Record & announce degraded mode for a component; never raises."""
        logger.error(
            "session_component_degraded",
            extra={"session_id": self.session_id, "component": component, "error_type": type(error).__name__},
        )
        first = component not in self.degraded_components
        self.degraded_components.add(component)
        if first:
            try:
                self.enqueue_event(
                    Envelope(
                        type="session.degraded",
                        session_id=self.session_id,
                        sequence=0,
                        payload={"component": component, "message": f"{component} temporarily unavailable; continuing"},
                    ),
                    critical=True,
                )
            except Exception:
                pass

    async def _db(self, query, params: Dict[str, Any], what: str) -> bool:
        db = self.session_manager.db
        try:
            await db.execute(query, params)
            await db.commit()
            return True
        except Exception as e:
            logger.error("session_db_write_failed", extra={"session_id": self.session_id, "what": what, "error_type": type(e).__name__})
            try:
                await db.rollback()
            except Exception:
                pass
            return False

    async def _insert_turn(self, speaker: str, text_value: str, parent_turn_id: Optional[str] = None) -> Optional[str]:
        """Insert a session_turns row with the next turn_index; returns its id (None on failure)."""
        turn_id = str(uuid.uuid4())
        db = self.session_manager.db
        for _ in range(3):  # retry on a concurrent turn_index collision
            try:
                res = await db.execute(
                    text("SELECT COALESCE(MAX(turn_index), -1) + 1 FROM session_turns WHERE session_id = :sid"),
                    {"sid": self.session_id},
                )
                idx = int(res.scalar() or 0)
            except Exception as e:
                logger.error("turn_index_lookup_failed", extra={"session_id": self.session_id, "error_type": type(e).__name__})
                try:
                    await db.rollback()
                except Exception:
                    pass
                return None
            ok = await self._db(
                text("""
                    INSERT INTO session_turns (id, session_id, turn_index, speaker, parent_turn_id, text, started_at, ended_at)
                    VALUES (:id, :sid, :idx, :speaker, :parent, :text, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """),
                {"id": turn_id, "sid": self.session_id, "idx": idx, "speaker": speaker, "parent": parent_turn_id, "text": text_value},
                what="session_turn",
            )
            if ok:
                return turn_id
        return None

    # ── event hooks from the transport ──────────────────────────────────
    async def start_candidate_turn(self):
        if await self._transition(SessionState.CANDIDATE_TURN):
            self.awaiting_since = None
            self.nudges_sent = 0
            self.coaching.start_turn()

    def handle_vad_event(self, evt: str):
        self.coaching.register_vad_event(evt)

    def handle_transcript_update(self, text_value: str):
        self.coaching.update_text(text_value)

    def record_final_segment(self, segment: Dict[str, Any]) -> None:
        """Buffer final STT segments; persisted once the candidate turn row exists (turn_id is NOT NULL)."""
        self._pending_segments.append(segment)

    async def _flush_segments(self, turn_id: str) -> None:
        segments, self._pending_segments = self._pending_segments, []
        for seg in segments:
            await self._db(
                text("""
                    INSERT INTO transcript_segments (id, session_id, turn_id, is_interim, text, start_ms, end_ms, confidence, language)
                    VALUES (:id, :sid, :tid, false, :text, :st, :en, :conf, :lang)
                """),
                {
                    "id": str(uuid.uuid4()),
                    "sid": self.session_id,
                    "tid": turn_id,
                    "text": seg.get("text"),
                    "st": seg.get("start_ms"),
                    "en": seg.get("end_ms"),
                    "conf": seg.get("confidence"),
                    "lang": seg.get("language"),
                },
                what="transcript_segment",
            )

    async def handle_vad_silence(self, vad_silence_ms: int, partial_transcript: str) -> None:
        """Evaluate turn completeness (the detector itself falls back to VAD on AI failure)."""
        try:
            decision = await self.turn_detector.evaluate(vad_silence_ms, partial_transcript)
        except Exception as e:
            self._degraded("turn_detection", e)
            from realtime_agent.app.interview.turn_detection import TurnEndDecision

            decision = TurnEndDecision(is_turn_end=vad_silence_ms >= 1500, reason="detector_error_fallback")
        if decision.is_turn_end:
            await self.on_candidate_turn_end(final_text=partial_transcript)

    async def handle_no_answer_timeout(self, max_nudges: int) -> None:
        """Candidate silent too long after a question: nudge, then move on."""
        if self._state() != SessionState.AWAITING_ANSWER:
            return
        if self.nudges_sent < max_nudges:
            self.nudges_sent += 1
            self.awaiting_since = time.monotonic()
            logger.info("no_answer_nudge", extra={"session_id": self.session_id, "nudge": self.nudges_sent})
            self.enqueue_event(
                Envelope(type="interviewer.text", session_id=self.session_id, sequence=0, payload={"text": NUDGE_TEXT, "nudge": True}),
                critical=True,
            )
            return
        logger.info("no_answer_skip", extra={"session_id": self.session_id})
        self.nudges_sent = 0
        if not await self._transition(SessionState.TURN_END, reason="no_answer_timeout"):
            return
        await self._insert_turn("candidate", "", parent_turn_id=self.last_interviewer_turn_id)
        await self._transition(SessionState.PLANNING_NEXT, reason="no_answer_timeout")
        await self._advance()

    # ── interviewer turn ────────────────────────────────────────────────
    async def begin_interviewer_turn(self, is_follow_up: bool = False, parent_turn_id: str = None) -> None:
        await self._transition(SessionState.INTERVIEWER_TURN)

        candidate_answer = getattr(self, "current_candidate_answer", "")
        try:
            decision = await self.session.generate_next_turn(
                candidate_answer=candidate_answer,
                gateway_router=self.gateway,
                routing_ctx=self.routing_ctx,
                is_follow_up=is_follow_up,
                parent_turn_id=parent_turn_id,
            )
        except Exception as e:
            self._degraded("llm", e)
            prep = list(getattr(self.session, "prep_pack", []) or [])
            idx = getattr(self.session, "current_question_idx", 0) or 0
            fallback = prep[idx] if idx < len(prep) else FALLBACK_QUESTION
            if idx < len(prep):
                self.session.current_question_idx = idx + 1
            decision = PolicyDecision(is_clarifying_follow_up=False, response_text=fallback)

        self.current_candidate_answer = ""
        self.last_interviewer_question = decision.response_text

        self.enqueue_event(
            Envelope(type="interviewer.text", session_id=self.session_id, sequence=0, payload={"text": decision.response_text}),
            critical=True,
        )

        turn_id = await self._insert_turn("interviewer", decision.response_text) or str(uuid.uuid4())
        self.last_interviewer_turn_id = turn_id
        gen_ctx = self.generation_manager.start_generation(turn_id=turn_id)

        async def text_iterator():
            yield decision.response_text

        tts_failed = False
        try:
            async for audio_chunk in self.tts.synthesize_streaming(text_iterator(), gen_ctx.token):
                if gen_ctx.token.is_cancelled():
                    break
                self.enqueue_event(audio_chunk, critical=False)
        except Exception as e:
            # The question text was already delivered; the candidate can read it.
            tts_failed = True
            self._degraded("tts", e)

        if gen_ctx.token.is_cancelled():
            return  # barge-in: the barge-in controller owns the next transition

        if tts_failed and await self._transition(SessionState.DEGRADED_TTS, reason="tts_failed"):
            pass
        await self._transition(SessionState.AWAITING_ANSWER)

    # ── candidate turn end ──────────────────────────────────────────────
    async def on_candidate_turn_end(self, final_text: str = "") -> None:
        if self._turn_lock.locked():
            return  # a turn end is already being processed
        async with self._turn_lock:
            await self._on_candidate_turn_end(final_text)

    async def _on_candidate_turn_end(self, final_text: str) -> None:
        candidate_id = self.session.candidate_profile.get("id", "unknown_candidate")

        await self._transition(SessionState.TURN_END)
        self.coaching.end_turn()
        self.current_candidate_answer = f"{getattr(self, 'current_candidate_answer', '')} {final_text}".strip()
        last_question = getattr(self, "last_interviewer_question", "")

        try:
            classification = await self.classifier.classify(self.current_candidate_answer, last_question)
            is_answer = bool(getattr(classification, "is_question", True))
        except Exception as e:
            # If we cannot classify, assume it is a real answer and score it.
            self._degraded("classifier", e)
            is_answer = True
        if not is_answer:
            logger.info("short_affirmation_not_scored", extra={"session_id": self.session_id})
            await self._transition(SessionState.AWAITING_ANSWER)
            return

        await self._transition(SessionState.SCORING)
        turn_id = await self._insert_turn("candidate", self.current_candidate_answer, parent_turn_id=self.last_interviewer_turn_id)
        if turn_id:
            await self._flush_segments(turn_id)

        score_res, claims_res = await asyncio.gather(
            score_answer_async(
                question=last_question,
                candidate_answer=self.current_candidate_answer,
                is_behavioral=False,
                verified_context="",
                gateway_router=self.gateway,
                routing_ctx=self.routing_ctx,
            ),
            process_candidate_answer_claims(
                answer_text=self.current_candidate_answer,
                question_context=last_question,
                session_id=self.session_id,
                turn_id=turn_id,
                candidate_id=candidate_id,
                gateway_router=self.gateway,
                routing_ctx=self.routing_ctx,
            )
            if turn_id
            else asyncio.sleep(0, result=[]),
            return_exceptions=True,
        )
        if isinstance(claims_res, BaseException):
            self._degraded("claims", claims_res)

        if isinstance(score_res, BaseException):
            self._degraded("scoring", score_res)
            await self._transition(SessionState.DEGRADED_LLM, reason="scoring_failed")
        else:
            if turn_id:
                await self._db(
                    text("""
                        INSERT INTO turn_scores (id, turn_id, rubric_version, relevance, correctness, structure, grounding,
                                                 specificity, conciseness, overall, rationale, scored_at)
                        VALUES (:id, :tid, :rv, :rel, :cor, :struc, :grnd, :spec, :conc, :overall, :rat, CURRENT_TIMESTAMP)
                    """),
                    {
                        "id": str(uuid.uuid4()),
                        "tid": turn_id,
                        "rv": getattr(score_res, "rubric_version", None),
                        "rel": score_res.relevance,
                        "cor": score_res.correctness,
                        "struc": score_res.structure,
                        "grnd": score_res.grounding,
                        "spec": score_res.specificity,
                        "conc": score_res.conciseness,
                        "overall": score_res.overall,
                        "rat": score_res.rationale,
                    },
                    what="turn_score",
                )
            try:
                self.enqueue_event(
                    Envelope(
                        type="turn.scoring_result",
                        session_id=self.session_id,
                        sequence=0,
                        payload={"turn_id": turn_id, "overall": float(score_res.overall), "rationale": score_res.rationale},
                    ),
                    critical=False,
                )
            except Exception:
                pass

        await self._transition(SessionState.PLANNING_NEXT)
        try:
            if len(self.session.memory.turns) > self.session.memory.turn_count_threshold:
                await self.session.memory.compress(self.gateway, self.routing_ctx)
        except Exception as e:
            self._degraded("memory", e)
        await self._advance()

    async def _advance(self) -> None:
        await self._transition(SessionState.READY)
        if self.session.current_question_idx >= len(self.session.prep_pack) and len(self.session.prep_pack) > 0:
            await self.end_session_and_debrief()
        else:
            await self.begin_interviewer_turn()

    # ── end of session ──────────────────────────────────────────────────
    async def end_session_and_debrief(self) -> None:
        from realtime_agent.app.interview.debrief import generate_debrief

        if self._state() in (SessionState.DEBRIEF, SessionState.STOPPED, SessionState.FAILED):
            return
        self.generation_manager.cancel_current("session_end")
        await self._transition(SessionState.DEBRIEF)

        status = "ready"
        try:
            debrief_result = await generate_debrief(self.session_id, self.session_manager.db, self.gateway, self.routing_ctx)
            await self._persist_debrief(debrief_result)
        except Exception as e:
            status = "pending"  # the backend's POST /sessions/{id}/end job can regenerate it
            self._degraded("debrief", e)
            try:
                await self.session_manager.db.rollback()
            except Exception:
                pass

        # STOPPED first: clients disconnect as soon as they see debrief.ready, and the
        # transport must already consider the session finished (not a dropped socket).
        await self._transition(SessionState.STOPPED)
        self.enqueue_event(
            Envelope(type="debrief.ready", session_id=self.session_id, sequence=0, payload={"status": status}),
            critical=True,
        )

    async def _persist_debrief(self, debrief_result) -> None:
        """Portable upsert (works on Postgres and the SQLite test schema)."""
        from sqlalchemy import delete, insert
        from backend.app.db.models import SessionDebrief

        table = SessionDebrief.__table__
        db = self.session_manager.db
        await db.execute(delete(table).where(table.c.session_id == uuid.UUID(str(self.session_id))))
        await db.execute(
            insert(table).values(
                id=uuid.uuid4(),
                session_id=uuid.UUID(str(self.session_id)),
                headline_metrics=json.loads(json.dumps(debrief_result.headline_metrics.model_dump())),
                strengths=list(debrief_result.strengths),
                weaknesses=list(debrief_result.weaknesses),
                flagged_claims=list(debrief_result.flagged_claims),
                jd_coverage=json.loads(json.dumps(debrief_result.jd_coverage, default=str)),
            )
        )
        await db.commit()

    # ── reconnect support ───────────────────────────────────────────────
    def snapshot(self) -> Dict[str, Any]:
        return {
            "current_question_idx": getattr(self.session, "current_question_idx", 0),
            "last_interviewer_question": self.last_interviewer_question,
            "last_interviewer_turn_id": self.last_interviewer_turn_id or "",
        }

    def restore(self, data: Dict[str, Any]) -> None:
        try:
            self.session.current_question_idx = int(data.get("current_question_idx") or 0)
        except (TypeError, ValueError):
            pass
        self.last_interviewer_question = data.get("last_interviewer_question") or ""
        self.last_interviewer_turn_id = data.get("last_interviewer_turn_id") or None
