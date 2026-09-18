import asyncio
import os
import uuid
import time
import httpx
from typing import AsyncIterator

from .protocol import RealtimeTranscriber, TranscriptEvent, TranscriptionConfig

class GroqCloudTranscriber(RealtimeTranscriber):
    def __init__(self):
        self.buffer = bytearray()
        self.config = None
        self.queue = asyncio.Queue()
        self.api_key = os.environ.get("GROQ_API_KEY")

    async def connect(self, config: TranscriptionConfig) -> None:
        self.config = config
        if not self.api_key:
            import logging
            logging.getLogger(__name__).warning("GROQ_API_KEY not set. Cloud STT will fail if invoked.")

    async def send_audio(self, pcm_chunk: bytes) -> None:
        self.buffer.extend(pcm_chunk)

    async def signal_segment_end(self) -> None:
        if len(self.buffer) == 0:
            return
            
        audio_data = bytes(self.buffer)
        self.buffer.clear()
        
        # Schedule transcription
        loop = asyncio.get_running_loop()
        loop.create_task(self._transcribe_segment(audio_data))

    async def _transcribe_segment(self, audio_data: bytes):
        try:
            import wave
            import io
            
            # Convert raw 16kHz PCM to WAV in memory
            wav_io = io.BytesIO()
            with wave.open(wav_io, 'wb') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(16000)
                wav_file.writeframes(audio_data)
            wav_bytes = wav_io.getvalue()
            
            async with httpx.AsyncClient() as client:
                files = {
                    'file': ('audio.wav', wav_bytes, 'audio/wav')
                }
                data = {
                    'model': 'whisper-large-v3',
                    'response_format': 'verbose_json'
                }
                if self.config and self.config.get("language"):
                    data["language"] = self.config["language"]
                
                response = await client.post(
                    "https://api.groq.com/openai/v1/audio/transcriptions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    files=files,
                    data=data,
                    timeout=10.0
                )
                
                response.raise_for_status()
                res_json = response.json()
                
                text = res_json.get("text", "").strip()
                if not text:
                    return
                    
                event: TranscriptEvent = {
                    "id": str(uuid.uuid4()),
                    "is_interim": False,
                    "text": text,
                    "start_ms": 0.0,
                    "end_ms": len(audio_data) / 2 / 16000 * 1000,
                    "confidence": 1.0, # Groq doesn't return segment-level confidence by default in basic view, but we can set 1.0 or extract it if needed
                    "language": res_json.get("language", self.config.get("language", "en")),
                    "source": "groq-whisper-large-v3"
                }
                await self.queue.put(event)
                
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Groq Whisper error: {e}")

    async def receive_events(self) -> AsyncIterator[TranscriptEvent]:
        while True:
            event = await self.queue.get()
            if event is None: # Sentinel
                break
            yield event

    async def close(self) -> None:
        await self.queue.put(None)
