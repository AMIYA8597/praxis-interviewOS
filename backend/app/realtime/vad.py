import time

class VADEngine:
    """
    Voice Activity Detection stub simulating Silero ONNX behavior.
    """
    def __init__(self, silence_threshold_ms=500):
        self.is_speaking = False
        self.last_speech_time = time.time()
        self.silence_threshold_ms = silence_threshold_ms

    def process_frame(self, audio_bytes: bytes) -> dict:
        """
        Process a chunk of audio and return VAD events.
        """
        # Simulated logic: if audio has energy > threshold, consider it speech.
        # For this stub, we just pretend any non-empty bytes means speech.
        energy = len(audio_bytes)
        current_time = time.time()
        
        events = []
        if energy > 100:  # Arbitrary threshold
            if not self.is_speaking:
                self.is_speaking = True
                events.append("speech_start")
            self.last_speech_time = current_time
        else:
            if self.is_speaking and (current_time - self.last_speech_time) * 1000 > self.silence_threshold_ms:
                self.is_speaking = False
                events.append("speech_end")
                
        return {
            "is_speaking": self.is_speaking,
            "events": events,
            "energy": energy
        }
