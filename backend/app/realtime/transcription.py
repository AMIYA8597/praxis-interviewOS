import asyncio
import uuid
import time

class MockTranscriber:
    """
    A simple mock transcription service for local testing without large ML models.
    Echoes back audio activity as text.
    """
    def __init__(self, callback):
        self.callback = callback
        self.is_running = False
        self.chunk_count = 0

    async def connect(self):
        self.is_running = True

    async def send_audio(self, audio_bytes: bytes):
        if not self.is_running:
            return
        
        # Simulate processing time
        await asyncio.sleep(0.1)
        
        # Emit a partial transcript based on data length (just as a mock)
        if len(audio_bytes) > 0:
            self.chunk_count += 1
            mock_text = "Processing audio chunk..."
            
            is_final = self.chunk_count % 15 == 0
            event_type = "transcript.final" if is_final else "transcript.partial"
            if is_final:
                mock_text = "So I decided to use a Redis cache to optimize the slow database queries, which reduced latency by 80%."

            event = {
                "version": "1",
                "type": event_type,
                "session_id": "mock_session",
                "timestamp": str(time.time()),
                "payload": {
                    "text": mock_text,
                    "confidence": 0.8
                }
            }
            await self.callback(event)

    async def close(self):
        self.is_running = False
