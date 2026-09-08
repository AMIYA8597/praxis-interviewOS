import time
from typing import Callable, Awaitable
from realtime_agent.app.interview.generation import SessionGenerationManager
from realtime_agent.app.session.state_machine import SessionState
from realtime_agent.app.protocol import Envelope

class BargeInController:
    def __init__(
        self, 
        session_id: str, 
        generation_manager: SessionGenerationManager, 
        state_transition_cb: Callable[[SessionState, str], Awaitable[None]],
        enqueue_event_cb: Callable[[Envelope, bool], None]
    ):
        self.session_id = session_id
        self.generation_manager = generation_manager
        self.transition = state_transition_cb
        self.enqueue_event = enqueue_event_cb
        self.last_trigger_ts = 0.0

    async def trigger(self, reason: str):
        """Called when candidate speech is detected during INTERVIEWER_TURN."""
        self.last_trigger_ts = time.time() * 1000.0
        
        # 1. Cancel current generation
        self.generation_manager.cancel_current(reason)
        
        # 2. Transition state
        # The prompt specifies: INTERVIEWER_TURN -> YIELDING -> AWAITING_ANSWER
        await self.transition(SessionState.YIELDING, "barge_in_triggered")
        await self.transition(SessionState.AWAITING_ANSWER, "yield_complete")
        
        # 3. Signal client to immediately stop TTS playback
        stop_tts_evt = Envelope(
            type="audio.stop_playback",
            session_id=self.session_id,
            sequence=0, # Assigned by queue
            payload={"reason": reason, "trigger_ts": self.last_trigger_ts}
        )
        self.enqueue_event(stop_tts_evt, critical=True)
