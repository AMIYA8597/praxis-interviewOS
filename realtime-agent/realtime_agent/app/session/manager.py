import asyncio
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from realtime_agent.app.session.state_machine import StateMachine, SessionState, InvalidTransitionError
from realtime_agent.app.protocol import Envelope

class SessionManager:
    def __init__(self, session_id: str, db: AsyncSession, enqueue_event_cb):
        self.session_id = session_id
        self.db = db
        self.enqueue_event = enqueue_event_cb
        self.sm = StateMachine()
        
    async def log_transition(self, from_state: str, to_state: str, reason: str):
        occurred_at = datetime.now(timezone.utc).isoformat()
        query = text("""
            INSERT INTO session_state_log (session_id, from_state, to_state, reason)
            VALUES (:sid, :from_s, :to_s, :reason)
        """)
        try:
            await self.db.execute(query, {
                "sid": self.session_id,
                "from_s": from_state,
                "to_s": to_state,
                "reason": reason
            })
            await self.db.commit()
        except Exception as e:
            # We don't want a DB logging failure to crash the whole session loop 
            # if we can avoid it, but we should log it.
            print(f"Failed to write session_state_log: {e}")

    async def transition(self, to_state: SessionState, reason: str = ""):
        from_state = self.sm.state
        try:
            self.sm.transition(to_state)
            # Log valid transition
            await self.log_transition(from_state.value, to_state.value, reason or "valid")
            
            # Broadcast to client
            evt = Envelope(
                type="state.transitioned",
                session_id=self.session_id,
                sequence=0, # The caller/queue manages real sequence
                payload={"from": from_state.value, "to": to_state.value, "reason": reason}
            )
            # The callback handles enqueueing and sequence assignment
            self.enqueue_event(evt, critical=True)
            
        except InvalidTransitionError as e:
            await self.log_transition(e.from_state.value, e.to_state.value, f"rejected: {reason}")
            raise e
