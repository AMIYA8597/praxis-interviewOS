import logging
import time
from typing import Dict

logger = logging.getLogger(__name__)

class CoachingMetricsExtractor:
    """
    Pure-DSP feature extraction. NO LLM INVOLVED.
    Computes WPM, filler rates, and pauses in single-digit milliseconds.
    """
    def __init__(self):
        self.filler_words = {"um", "uh", "like", "you know", "sort of", "basically", "literally"}
        self.total_words = 0
        self.filler_count = 0
        self.start_time = time.time()
        self.last_pause_duration_ms = 0
        
    def process_transcript_chunk(self, partial_text: str) -> Dict:
        """
        Called incrementally as the STT pipeline emits words.
        """
        start = time.perf_counter()
        
        words = partial_text.lower().split()
        self.total_words = len(words)
        self.filler_count = sum(1 for w in words if w in self.filler_words)
        
        elapsed_minutes = (time.time() - self.start_time) / 60.0
        wpm = (self.total_words / elapsed_minutes) if elapsed_minutes > 0 else 0
        
        latency = (time.perf_counter() - start) * 1000
        # logger.debug(f"DSP Coaching Metrics extracted in {latency:.3f}ms")
        
        return {
            "wpm": round(wpm),
            "filler_count": self.filler_count,
            "filler_rate_pct": round((self.filler_count / self.total_words) * 100) if self.total_words > 0 else 0,
            "last_pause_ms": self.last_pause_duration_ms
        }
