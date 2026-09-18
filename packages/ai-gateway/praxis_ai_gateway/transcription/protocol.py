from typing import Protocol, AsyncIterator, TypedDict, Optional

class TranscriptionConfig(TypedDict):
    language: str
    prompt: Optional[str]

class TranscriptEvent(TypedDict):
    id: str
    is_interim: bool
    text: str
    start_ms: float
    end_ms: float
    confidence: float
    language: str
    source: str

class RealtimeTranscriber(Protocol):
    async def connect(self, config: TranscriptionConfig) -> None:
        ...
        
    async def send_audio(self, pcm_chunk: bytes) -> None:
        ...
        
    async def signal_segment_end(self) -> None:
        """Called on VAD speech_end to trigger transcription of the accumulated segment."""
        ...
        
    async def receive_events(self) -> AsyncIterator[TranscriptEvent]:
        ...
        
    async def close(self) -> None:
        ...
