import numpy as np
from realtime_agent.audio.vad_engine import VADBuffer

class PauseAnalyzer:
    """Extract pause metrics from VAD stream."""
    
    def __init__(self, min_pause_ms: int = 200):
        self.min_pause_ms = min_pause_ms
        self.pauses = []  # List of (start_time, duration_ms)
    
    async def analyze_vad_stream(self, vad_buffer: VADBuffer):
        """
        Scan VAD buffer for pauses longer than min_pause_ms.
        Called at end of candidate response.
        """
        recent = await vad_buffer.get_recent(1000)
        
        in_pause = False
        pause_start = None
        
        for result in recent:
            if not result["is_speech"]:
                if not in_pause:
                    pause_start = result["timestamp"]
                    in_pause = True
            else:
                if in_pause and pause_start:
                    pause_duration = (result["timestamp"] - pause_start) * 1000
                    if pause_duration >= self.min_pause_ms:
                        self.pauses.append((pause_start, pause_duration))
                    in_pause = False
        
        return {
            "pause_count": len(self.pauses),
            "avg_pause_ms": np.mean([p[1] for p in self.pauses]) if self.pauses else 0,
            "max_pause_ms": max([p[1] for p in self.pauses]) if self.pauses else 0,
        }
