import time
import logging
import numpy as np
import onnxruntime as ort
import os
from typing import TypedDict, Tuple, Optional

logger = logging.getLogger(__name__)

class VADResult(TypedDict):
    is_speech: bool
    confidence: float
    energy_db: float
    
class VoiceActivityDetector:
    """
    Wraps Silero VAD (ONNX runtime) with buffering, energy calculation,
    and a speech_start/speech_end state machine.
    """
    def __init__(self, 
                 threshold: float = 0.5,
                 consecutive_frames_for_start: int = 3,
                 silence_duration_ms: int = 550,
                 frame_duration_ms: int = 32):  # Silero uses 512 samples at 16kHz = 32ms
        
        self.threshold = threshold
        
        # Determine ONNX model path from silero_vad package
        import silero_vad
        model_path = os.path.join(os.path.dirname(silero_vad.__file__), "data", "silero_vad.onnx")
        
        # Use CPUExecutionProvider
        self.session = ort.InferenceSession(model_path, providers=['CPUExecutionProvider'])
        
        self.state = np.zeros((2, 1, 128), dtype=np.float32)
        
        self.buffer = bytearray()
        self.frame_size_bytes = 512 * 2  # 512 samples of int16 (16kHz)
        
        # State machine
        self.consecutive_frames_for_start = consecutive_frames_for_start
        self.frames_for_end = int(silence_duration_ms / frame_duration_ms)
        
        self.positive_count = 0
        self.negative_count = 0
        self.is_speaking = False

    def reset_state(self):
        self.state = np.zeros((2, 1, 128), dtype=np.float32)
        self.buffer.clear()
        self.positive_count = 0
        self.negative_count = 0
        self.is_speaking = False

    def process_frame(self, pcm_frame: bytes) -> Tuple[Optional[VADResult], Optional[str]]:
        """
        Takes raw 16kHz int16 PCM bytes.
        Returns:
            - A VADResult (if a full 512-sample frame was processed, else None)
            - A state change string ('speech_start', 'speech_end', or None)
        """
        self.buffer.extend(pcm_frame)
        
        # We only process if we have a full frame (512 samples = 1024 bytes)
        if len(self.buffer) < self.frame_size_bytes:
            return None, None
            
        # Extract one frame
        frame_bytes = self.buffer[:self.frame_size_bytes]
        del self.buffer[:self.frame_size_bytes]
        
        # Calculate energy
        audio_array = np.frombuffer(frame_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        rms = np.sqrt(np.mean(audio_array**2))
        energy_db = 20 * np.log10(rms + 1e-10)
        
        # VAD inference
        inputs = {
            "input": audio_array.reshape(1, -1),
            "state": self.state,
            "sr": np.array(16000, dtype=np.int64)
        }
        
        out, self.state = self.session.run(None, inputs)
        confidence = float(out[0][0])
        is_speech = confidence >= self.threshold
        
        result: VADResult = {
            "is_speech": is_speech,
            "confidence": confidence,
            "energy_db": float(energy_db)
        }
        
        event = self._update_state(is_speech)
        return result, event

    def _update_state(self, is_speech: bool) -> Optional[str]:
        if is_speech:
            self.positive_count += 1
            self.negative_count = 0
            if not self.is_speaking and self.positive_count >= self.consecutive_frames_for_start:
                self.is_speaking = True
                return "speech_start"
        else:
            self.negative_count += 1
            self.positive_count = 0
            if self.is_speaking and self.negative_count >= self.frames_for_end:
                self.is_speaking = False
                return "speech_end"
                
        return None
