import asyncio
import numpy as np
import os
import uuid
import uuid
import time
from typing import AsyncIterator
from concurrent.futures import ThreadPoolExecutor

from faster_whisper import WhisperModel

from .protocol import RealtimeTranscriber, TranscriptEvent, TranscriptionConfig

# Global thread pool for CPU-bound transcription
_executor = ThreadPoolExecutor(max_workers=2)

# Global model instance
_model = None
_MODEL_SIZE = os.environ.get("LOCAL_STT_MODEL", "small")
# NOTE: We use "small" (multilingual) instead of "small.en" to support Hinglish/code-switching 
# as explicitly tested in Phase 3.5, trading a tiny bit of latency/English-accuracy for language flexibility.

def _get_model() -> WhisperModel:
    global _model
    if _model is None:
        import logging
        logging.getLogger(__name__).info(f"Loading faster-whisper model '{_MODEL_SIZE}' on CPU (FP32)...")
        _model = WhisperModel(_MODEL_SIZE, device="cpu", compute_type="float32")
    return _model

class FasterWhisperTranscriber(RealtimeTranscriber):
    def __init__(self):
        self.buffer = bytearray()
        self.config = None
        self.queue = asyncio.Queue()
        self.session_start = time.perf_counter()

    async def connect(self, config: TranscriptionConfig) -> None:
        self.config = config
        # Trigger model load in background if not loaded
        asyncio.get_running_loop().run_in_executor(_executor, _get_model)

    async def send_audio(self, pcm_chunk: bytes) -> None:
        self.buffer.extend(pcm_chunk)

    async def signal_segment_end(self) -> None:
        if len(self.buffer) == 0:
            return
            
        audio_data = bytes(self.buffer)
        self.buffer.clear()
        
        # Schedule transcription in threadpool
        loop = asyncio.get_running_loop()
        loop.create_task(self._transcribe_segment(audio_data))

    async def _transcribe_segment(self, audio_data: bytes):
        try:
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(_executor, self._run_faster_whisper, audio_data)
            if result:
                await self.queue.put(result)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"faster-whisper error: {e}")

    def _run_faster_whisper(self, pcm_data: bytes) -> TranscriptEvent:
        model = _get_model()
        # Convert bytes to normalized float32 for faster-whisper (expects -1.0 to 1.0)
        audio_array = np.frombuffer(pcm_data, dtype=np.int16).astype(np.float32) / 32768.0
        
        # We emit only a final per-segment transcript.
        # LIMITATION NOTE: faster-whisper's stream/VAD approach is primarily designed for 
        # generating complete segments. True token-by-token streaming partials are not natively 
        # supported efficiently in the current python API without custom chunking hacks that degrade quality.
        # Thus, we deliberately use VAD to segment and return high-quality finals.
        
        segments, info = model.transcribe(
            audio_array,
            beam_size=5,
            language=self.config.get("language") if self.config else None,
            condition_on_previous_text=False
        )
        
        text = " ".join([seg.text for seg in segments]).strip()
        
        if not text:
            return None
            
        return {
            "id": str(uuid.uuid4()),
            "is_interim": False,
            "text": text,
            "start_ms": 0.0, # Relative to this segment
            "end_ms": len(pcm_data) / 2 / 16000 * 1000,
            "confidence": info.language_probability,
            "language": info.language,
            "source": f"faster-whisper-{_MODEL_SIZE}"
        }

    async def receive_events(self) -> AsyncIterator[TranscriptEvent]:
        while True:
            event = await self.queue.get()
            if event is None: # Sentinel for close
                break
            yield event

    async def close(self) -> None:
        await self.queue.put(None)
