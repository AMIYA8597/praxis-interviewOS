import logging
import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from realtime_agent.app.protocol import Envelope
from realtime_agent.app.session.state_machine import InvalidTransitionError, SessionState, StateMachine

logger = logging.getLogger(__name__)


class SessionManager:
    def __init__(self, session_id: str, db: AsyncSession, enqueue_event_cb):
        self.session_id = session_id
        self.db = db
        self.enqueue_event = enqueue_event_cb
        self.sm = StateMachine()

    @property
    def state(self) -> SessionState:
        return self.sm.state

    async def log_transition(self, from_state: str, to_state: str, reason: str):
        """Audit row in session_state_log. A DB failure must never break the live session."""
        query = text("""
            INSERT INTO session_state_log (id, session_id, from_state, to_state, reason)
            VALUES (:id, :sid, :from_s, :to_s, :reason)
        """)
        try:
            await self.db.execute(query, {"id": str(uuid.uuid4()), "sid": self.session_id, "from_s": from_state, "to_s": to_state, "reason": reason})
            await self.db.commit()
        except Exception as e:
            logger.warning("state_log_write_failed", extra={"session_id": self.session_id, "error_type": type(e).__name__})
            try:
                await self.db.rollback()
            except Exception:
                pass

    async def _persist_terminal_status(self, status: str) -> None:
        """Record the outcome as soon as the session ends (not only when the socket closes)."""
        try:
            await self.db.execute(
                text("UPDATE practice_sessions SET status = :st, ended_at = CURRENT_TIMESTAMP WHERE id = :sid"),
                {"st": status, "sid": self.session_id},
            )
            await self.db.commit()
        except Exception as e:
            logger.warning("session_status_write_failed", extra={"session_id": self.session_id, "error_type": type(e).__name__})
            try:
                await self.db.rollback()
            except Exception:
                pass

    async def transition(self, to_state: SessionState, reason: str = ""):
        from_state = self.sm.state
        try:
            self.sm.transition(to_state)
        except InvalidTransitionError as e:
            await self.log_transition(e.from_state.value, e.to_state.value, f"rejected: {reason}")
            raise
        logger.info(
            "session_state_transition",
            extra={"session_id": self.session_id, "from_state": from_state.value, "to_state": to_state.value, "reason": reason},
        )
        await self.log_transition(from_state.value, to_state.value, reason or "valid")
        if to_state in (SessionState.STOPPED, SessionState.FAILED):
            await self._persist_terminal_status("completed" if to_state == SessionState.STOPPED else "failed")
        self.enqueue_event(
            Envelope(
                type="state.transitioned",
                session_id=self.session_id,
                sequence=0,  # assigned by the outbound queue
                payload={"from": from_state.value, "to": to_state.value, "to_state": to_state.value, "reason": reason},
            ),
            critical=True,
        )

    async def try_transition(self, to_state: SessionState, reason: str = "") -> bool:
        """Transition if legal; returns False instead of raising."""
        try:
            await self.transition(to_state, reason)
            return True
        except InvalidTransitionError:
            return False
