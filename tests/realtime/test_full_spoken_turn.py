import asyncio
import os
import sys
import time
import logging

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'packages', 'ai-gateway'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from praxis_ai_gateway.cancellation import CancellationToken
from realtime_agent.app.audio.tts import PiperTTSAdapter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def text_generator():
    """Simulate streaming LLM output."""
    yield "Hello there! "
    await asyncio.sleep(0.1)
    yield "This is the interviewer speaking. "
    await asyncio.sleep(0.1)
    yield "I am going to ask you a very long and complicated question about your background. "
    await asyncio.sleep(0.1)
    yield "Could you explain the architecture of the distributed system you built?"

async def test_full_turn():
    tts = PiperTTSAdapter(voice_model="models/en_US-lessac-low.onnx")
    token = CancellationToken()
    
    # Wait for background model load
    await asyncio.sleep(1)
    
    print("--- Testing Full Spoken Turn (No Cancel) ---")
    
    total_audio_bytes = 0
    start_ts = time.perf_counter()
    async for chunk in tts.synthesize_streaming(text_generator(), token):
        total_audio_bytes += len(chunk)
        print(f"Received chunk of size {len(chunk)} bytes")
        
    duration = time.perf_counter() - start_ts
    print(f"Total audio produced: {total_audio_bytes} bytes in {duration:.2f}s")
    assert total_audio_bytes > 0, "No audio was generated"
    
    print("\n--- Testing Spoken Turn with Barge-in ---")
    token2 = CancellationToken()
    total_audio_bytes_canceled = 0
    start_ts = time.perf_counter()
    
    async def simulate_barge_in():
        await asyncio.sleep(0.3)
        print("\n>>> SIMULATING BARGE-IN (VAD DETECTED SPEECH) <<<")
        token2.cancel("vad_speech_detected")
        
    barge_in_task = asyncio.create_task(simulate_barge_in())
    
    cancel_latency_start = None
    
    async for chunk in tts.synthesize_streaming(text_generator(), token2):
        total_audio_bytes_canceled += len(chunk)
        print(f"Received chunk of size {len(chunk)} bytes")
        if token2.is_cancelled() and cancel_latency_start is None:
             cancel_latency_start = time.perf_counter()
             
    if cancel_latency_start is None:
        cancel_latency_start = time.perf_counter() # fallback
        
    stop_ts = time.perf_counter()
    latency_to_stop = (stop_ts - cancel_latency_start) * 1000
    
    print(f"Total audio produced before cancel: {total_audio_bytes_canceled} bytes")
    print(f"Server-side TTS synthesis halting latency after cancel signal: {latency_to_stop:.2f}ms")
    assert total_audio_bytes_canceled < total_audio_bytes, "Cancellation did not halt synthesis"

if __name__ == "__main__":
    asyncio.run(test_full_turn())
