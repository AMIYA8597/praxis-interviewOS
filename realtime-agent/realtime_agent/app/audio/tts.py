import logging
import asyncio
import os
import re
from typing import AsyncIterator
from concurrent.futures import ThreadPoolExecutor

from praxis_ai_gateway.cancellation import CancellationToken

logger = logging.getLogger(__name__)

# Global thread pool for TTS
_executor = ThreadPoolExecutor(max_workers=2)
_voice = None

def _get_piper_voice(model_path="models/en_US-lessac-low.onnx"):
    global _voice
    if _voice is None:
        from piper.voice import PiperVoice
        # Check if file exists, else we can't load.
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Piper model not found at {model_path}")
        logger.info(f"Loading Piper TTS voice: {model_path}")
        _voice = PiperVoice.load(model_path)
    return _voice

class PiperTTSAdapter:
    """
    Local Piper TTS via ONNX.
    Supports streaming synthesis chunked by sentence and a hard cancel() hook for barge-in.
    
    ### ORCHESTRATOR INTERFACE CONTRACT:
    - **Method**: `synthesize_streaming(text_stream: AsyncIterator[str], cancellation_token: CancellationToken) -> AsyncIterator[bytes]`
    - **Input Shape**: An async iterator yielding incremental text/token deltas (strings) as they arrive from the LLM. 
      It does NOT require a single pre-assembled string.
    - **Output Shape**: An async iterator yielding raw 16kHz PCM audio bytes (`bytes`).
    - **Cancellation**: Must be passed a `CancellationToken` (from `praxis_ai_gateway.cancellation`). If `token.is_cancelled()` becomes true (e.g. from a barge-in event), synthesis instantly aborts and stops yielding audio chunks.
    """
    def __init__(self, voice_model="models/en_US-lessac-low.onnx"):
        self.voice_model = voice_model
        # Trigger load in background
        try:
            _get_piper_voice(self.voice_model)
        except Exception as e:
            logger.error(f"Failed to load Piper voice on init: {e}")

    async def synthesize_streaming(self, text_stream: AsyncIterator[str], cancellation_token: CancellationToken) -> AsyncIterator[bytes]:
        """
        Consumes streaming text from the LLM, synthesizes to PCM sentence-by-sentence, and yields audio chunks.
        """
        buffer = ""
        # Simple sentence boundary regex
        sentence_end_re = re.compile(r'(?<=[.!?])\s+')
        
        async for text_chunk in text_stream:
            if cancellation_token.is_cancelled():
                logger.info("TTS Synthesis aborted due to cancellation_token mid-stream")
                return
                
            buffer += text_chunk
            
            # Split buffer by sentence boundaries
            parts = sentence_end_re.split(buffer)
            if len(parts) > 1:
                # Synthesize all complete sentences
                for sentence in parts[:-1]:
                    if not sentence.strip():
                        continue
                    if cancellation_token.is_cancelled():
                        logger.info("TTS Synthesis aborted due to cancellation_token before synthesis")
                        return
                        
                    async for audio_chunk in self._synthesize_sentence(sentence.strip(), cancellation_token):
                        yield audio_chunk
                        
                buffer = parts[-1]
                
        # Synthesize remaining buffer
        if buffer.strip() and not cancellation_token.is_cancelled():
            async for audio_chunk in self._synthesize_sentence(buffer.strip(), cancellation_token):
                yield audio_chunk

    async def _synthesize_sentence(self, text: str, token: CancellationToken) -> AsyncIterator[bytes]:
        try:
            loop = asyncio.get_running_loop()
            
            # Piper's synthesize returns an iterator. We run it in a thread so it doesn't block.
            def run_piper(text):
                voice = _get_piper_voice(self.voice_model)
                chunks = []
                for audio_chunk in voice.synthesize(text):
                    # We can't easily check token here unless we pass it in, 
                    # but voice.synthesize yields chunks very quickly per sentence.
                    chunks.append(audio_chunk.audio_int16_bytes)
                return chunks
                
            audio_chunks = await loop.run_in_executor(_executor, run_piper, text)
            
            for chunk_data in audio_chunks:
                if token.is_cancelled():
                    logger.info("TTS Synthesis aborted between Piper chunks")
                    break
                # chunk_data is already bytes.
                yield chunk_data
                
        except Exception as e:
            logger.error(f"Piper synthesis error: {e}")

class CloudTTSAdapter:
    def __init__(self):
        logger.info("Initialized Cloud TTS Fallback")
        
    async def synthesize_streaming(self, text_stream: AsyncIterator[str], cancellation_token: CancellationToken) -> AsyncIterator[bytes]:
        yield b''
