import torch
import numpy as np
from collections import deque
from silero_vad import load_silero_vad
import sounddevice as sd
from datetime import datetime, timezone
import logging
import asyncio
import itertools

logger = logging.getLogger(__name__)

class SileroVADEngine:
    """
    Real-time Voice Activity Detection using Silero VAD.
    
    Runs at 16kHz, processes 512-sample chunks (~32ms frames).
    Outputs: (is_speech: bool, confidence: float, frame_time: float)
    """
    
    def __init__(
        self,
        sample_rate: int = 16000,
        chunk_size: int = 512,
        silence_threshold: float = 0.5,
        speech_threshold: float = 0.6,
        min_speech_duration_ms: int = 100,
        min_silence_duration_ms: int = 300,
    ):
        """
        Initialize Silero VAD.
        
        Args:
            sample_rate: Audio sample rate (16kHz for optimal Silero performance)
            chunk_size: Samples per frame (512 = 32ms at 16kHz)
            silence_threshold: Probability below which frame is marked silence
            speech_threshold: Probability above which frame is marked speech
            min_speech_duration_ms: Min consecutive speech before state change
            min_silence_duration_ms: Min consecutive silence before state change
        """
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.silence_threshold = silence_threshold
        self.speech_threshold = speech_threshold
        self.min_speech_frames = max(1, min_speech_duration_ms // (1000 * chunk_size / sample_rate))
        self.min_silence_frames = max(1, min_silence_duration_ms // (1000 * chunk_size / sample_rate))
        
        # Load model
        self.model = load_silero_vad(onnx=True)
        
        # State tracking
        self.is_speech = False
        self.speech_frame_count = 0
        self.silence_frame_count = 0
        self.last_state_change = datetime.now(timezone.utc)
        
        logger.info(f"Silero VAD initialized (sample_rate={sample_rate}, chunk_size={chunk_size})")
    
    def process_chunk(self, audio_chunk: np.ndarray) -> dict:
        """
        Process a single audio chunk and return VAD decision.
        """
        if len(audio_chunk) != self.chunk_size:
            raise ValueError(f"Expected chunk_size={self.chunk_size}, got {len(audio_chunk)}")
        
        audio_chunk = torch.FloatTensor(audio_chunk).unsqueeze(0)
        
        # Get confidence score from model (0.0 = silence, 1.0 = speech)
        with torch.no_grad():
            confidence = self.model(audio_chunk, self.sample_rate).item()
        
        # Update state machine
        if confidence > self.speech_threshold:
            self.speech_frame_count += 1
            self.silence_frame_count = 0
            
            if not self.is_speech and self.speech_frame_count >= self.min_speech_frames:
                self.is_speech = True
                self.last_state_change = datetime.now(timezone.utc)
                state_changed = True
            else:
                state_changed = False
                
        elif confidence < self.silence_threshold:
            self.silence_frame_count += 1
            self.speech_frame_count = 0
            
            if self.is_speech and self.silence_frame_count >= self.min_silence_frames:
                self.is_speech = False
                self.last_state_change = datetime.now(timezone.utc)
                state_changed = True
            else:
                state_changed = False
        else:
            # Confidence in ambiguous zone: no state change
            state_changed = False
        
        # Calculate durations
        elapsed = (datetime.now(timezone.utc) - self.last_state_change).total_seconds() * 1000
        if self.is_speech:
            speech_duration_ms = elapsed
            silence_duration_ms = 0.0
        else:
            speech_duration_ms = 0.0
            silence_duration_ms = elapsed
        
        return {
            "is_speech": self.is_speech,
            "confidence": float(confidence),
            "timestamp": datetime.now(timezone.utc).timestamp(),
            "state_changed": state_changed,
            "speech_duration_ms": speech_duration_ms,
            "silence_duration_ms": silence_duration_ms,
        }
    
    def reset(self):
        """Reset state for a new session."""
        self.is_speech = False
        self.speech_frame_count = 0
        self.silence_frame_count = 0
        self.last_state_change = datetime.now(timezone.utc)
        logger.info("VAD state reset")

class VADBuffer:
    """Thread-safe circular buffer for VAD output."""
    
    def __init__(self, max_size: int = 1000):
        self.buffer = deque(maxlen=max_size)
        self.lock = asyncio.Lock()
    
    async def push(self, vad_result: dict):
        async with self.lock:
            self.buffer.append(vad_result)
    
    async def get_recent(self, n: int = 10) -> list:
        async with self.lock:
            return list(itertools.islice(self.buffer, max(0, len(self.buffer) - n), len(self.buffer)))
