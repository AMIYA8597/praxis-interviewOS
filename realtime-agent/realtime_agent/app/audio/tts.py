import logging
import asyncio
from typing import AsyncGenerator

logger = logging.getLogger(__name__)

class PiperTTSAdapter:
    """
    Local Piper TTS via ONNX.
    Supports streaming synthesis and a hard cancel() hook for barge-in.
    """
    def __init__(self, voice="en_US-lessac-medium"):
        self.voice = voice
        self.is_canceled = False
        logger.info(f"Initialized Piper TTS ({voice})")

    async def stream_synthesize(self, text_stream: AsyncGenerator[str, None], cancellation_token: str) -> AsyncGenerator[bytes, None]:
        """
        Consumes streaming text from the LLM, synthesizes to PCM, and yields audio chunks.
        """
        self.is_canceled = False
        buffer = ""
        
        async for text_chunk in text_stream:
            if self.is_canceled:
                logger.warning(f"TTS Synthesis aborted for token: {cancellation_token}")
                break
                
            buffer += text_chunk
            # Simple sentence boundary detection for synthesis chunks
            if any(punct in buffer for punct in ['. ', '? ', '! ']):
                # Synthesize chunk (Stub)
                # pcm_chunk = await self._synthesize_onnx(buffer)
                pcm_chunk = b'\x00' * 1024 # Dummy 16kHz PCM data
                yield pcm_chunk
                buffer = ""
                await asyncio.sleep(0.01)
                
        if buffer and not self.is_canceled:
            yield b'\x00' * 1024

    def cancel(self):
        self.is_canceled = True
        logger.info("Piper TTS hard cancel invoked.")

class CloudTTSAdapter:
    def __init__(self):
        logger.info("Initialized Cloud TTS Fallback")
        self.is_canceled = False
        
    async def stream_synthesize(self, *args, **kwargs):
        yield b''
        
    def cancel(self):
        self.is_canceled = True
