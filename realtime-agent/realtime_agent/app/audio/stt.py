import logging
from typing import Protocol, AsyncIterator, Dict

logger = logging.getLogger(__name__)

class RealtimeTranscriber(Protocol):
    async def connect(self): ...
    async def send_audio(self, pcm_data: bytes): ...
    async def receive_events(self) -> AsyncIterator[Dict]: ...
    async def close(self): ...

class FasterWhisperAdapter:
    def __init__(self, model_size="small.en"):
        self.model_size = model_size
        logger.info(f"Initialized faster-whisper local STT ({model_size})")

    async def connect(self):
        # Stub: Load CTranslate2 model into memory
        pass

    async def send_audio(self, pcm_data: bytes):
        # Append to rolling window buffer
        pass

    async def receive_events(self) -> AsyncIterator[Dict]:
        # Yield partial/final transcripts
        yield {
            "id": "trans_123",
            "session_id": "sess_1",
            "speaker": "candidate",
            "text": "This is a local faster-whisper partial transcript.",
            "is_interim": True,
            "start_ms": 0,
            "end_ms": 200,
            "confidence": 0.95,
            "language": "en"
        }

    async def close(self):
        pass

class GroqWhisperAdapter:
    def __init__(self):
        logger.info("Initialized Groq Whisper cloud fallback.")

    async def connect(self): pass
    async def send_audio(self, pcm_data: bytes): pass
    async def receive_events(self) -> AsyncIterator[Dict]:
        yield {}
    async def close(self): pass
