import asyncio
import time
import logging
from typing import Callable, Any

from realtime_agent.app.protocol import Envelope
from .metrics import (
    load_coaching_config, compute_wpm, tokenize_text, 
    compute_filler_rate, compute_hedge_count, compute_pause_stats
)

logger = logging.getLogger(__name__)

class CoachingMetricsAccumulator:
    """
    Per-turn accumulator that updates incrementally on a FIXED 250ms timer.
    
    ### ORCHESTRATOR INTERFACE CONTRACT:
    - **Initialization**: Instantiate once per session, passing `session_id` and an `enqueue_event_cb`.
    - **`start_turn()`**: Call precisely when the state machine transitions to `CANDIDATE_TURN`. Starts the 250ms polling loop.
    - **`update_text(partial_text: str)`**: Call whenever a new `transcript.partial` or `transcript.final` arrives from STT.
    - **`register_vad_event(event_type: str)`**: Call with `"speech_start"` or `"speech_end"` when the VAD engine fires these events. Used to calculate pause gaps.
    - **`end_turn()`**: Call precisely when the state machine leaves `CANDIDATE_TURN` (e.g. `TURN_END` or `SCORING`). Hard-cancels the 250ms polling loop.
    """
    def __init__(self, session_id: str, enqueue_event_cb: Callable[[Envelope, bool], None]):
        self.session_id = session_id
        self.enqueue_event_cb = enqueue_event_cb
        
        config = load_coaching_config()
        self.filler_words = config["fillers"]
        self.hedge_words = config["hedges"]
        
        self.is_active = False
        self._update_task = None
        
        # State
        self.turn_start_ts = 0.0
        self.current_text = ""
        self.vad_silence_gaps = []
        self.last_speech_end_ts = 0.0
        
    def start_turn(self):
        self.is_active = True
        self.turn_start_ts = time.perf_counter()
        self.current_text = ""
        self.vad_silence_gaps = []
        self.last_speech_end_ts = self.turn_start_ts
        
        # Start fixed 250ms cadence loop
        loop = asyncio.get_running_loop()
        self._update_task = loop.create_task(self._update_loop())
        
    def end_turn(self):
        self.is_active = False
        if self._update_task:
            self._update_task.cancel()
            self._update_task = None
            
    def update_text(self, partial_text: str):
        self.current_text = partial_text
        
    def register_vad_event(self, event_type: str):
        now = time.perf_counter()
        if event_type == "speech_end":
            self.last_speech_end_ts = now
        elif event_type == "speech_start":
            if self.last_speech_end_ts > 0:
                gap_ms = int((now - self.last_speech_end_ts) * 1000)
                if gap_ms > 50: # Ignore micro-gaps
                    self.vad_silence_gaps.append(gap_ms)
                    
    async def _update_loop(self):
        try:
            while self.is_active:
                await asyncio.sleep(0.25)
                try:
                    self._compute_and_emit()
                except Exception as e:
                    logger.error(f"Error computing coaching metrics: {e}", exc_info=True)
        except asyncio.CancelledError:
            pass
            
    def _compute_and_emit(self):
        start_comp = time.perf_counter()
        
        now = time.perf_counter()
        duration_ms = int((now - self.turn_start_ts) * 1000)
        
        tokens = tokenize_text(self.current_text)
        wpm = compute_wpm(len(tokens), duration_ms)
        filler_stats = compute_filler_rate(self.current_text, self.filler_words)
        hedge_count = compute_hedge_count(self.current_text, self.hedge_words)
        pause_stats = compute_pause_stats(self.vad_silence_gaps, duration_ms)
        
        metrics_payload = {
            "wpm": round(wpm, 1),
            "fillers": filler_stats,
            "hedges": hedge_count,
            "pauses": pause_stats,
            "duration_ms": duration_ms
        }
        
        envelope = Envelope(
            type="coaching.metrics",
            session_id=self.session_id,
            sequence=0,
            payload=metrics_payload
        )
        # We explicitly skip any backpressure coalescing for coaching metrics (Task 3)
        # by passing them as non-critical or flagging them directly. 
        # For our system, non-critical events might be dropped if the queue is full,
        # but UI will just catch the next 250ms tick.
        self.enqueue_event_cb(envelope, critical=False)
        
        # Benchmarking for Task 5
        comp_time_ms = (time.perf_counter() - start_comp) * 1000
        # Only log if it's slow to avoid spamming
        if comp_time_ms > 5.0:
            logger.warning(f"Coaching metrics computation was slow: {comp_time_ms:.2f}ms")
