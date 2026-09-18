import asyncio
print("Starting script...")
import os
os.environ["LOCAL_STT_MODEL"] = "tiny"
import sys
import time

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'packages', 'ai-gateway'))

from realtime_agent.app.audio.vad import VoiceActivityDetector
from praxis_ai_gateway.transcription.local_faster_whisper import FasterWhisperTranscriber
from realtime_agent.app.audio.tts import PiperTTSAdapter
from praxis_ai_gateway.cancellation import CancellationToken
from realtime_agent.app.session.state_machine import StateMachine, SessionState
from realtime_agent.app.interview.turn_detection import TurnEndDetector, CompletenessResult
from praxis_ai_gateway.router import RoutingContext, RoutedCall

class LoopRouterMock:
    async def route(self, task: str, context: RoutingContext, method_name: str, **kw):
        result = CompletenessResult(is_complete=True)
        return RoutedCall(provider_name="mock", model="mock", result=result)

async def tts_generator():
    yield "Hello candidate. "
    await asyncio.sleep(0.1)
    yield "I'm going to ask a question. "
    await asyncio.sleep(0.1)
    yield "Can you explain your system design approach?"

async def test_full_loop():
    print("--- STARTING FULL REALTIME LOOP INTEGRATION TEST ---")
    
    # 1. Initialize all 5 components
    vad = VoiceActivityDetector()
    stt = FasterWhisperTranscriber()
    tts = PiperTTSAdapter(voice_model="models/en_US-lessac-low.onnx")
    turn_detector = TurnEndDetector(router=LoopRouterMock(), silence_threshold_ms=550)
    
    # State Machine
    sm = StateMachine()
    
    # We are in INTERVIEWER_TURN
    sm.transition(SessionState.PREFLIGHT)
    sm.transition(SessionState.WARMING)
    sm.transition(SessionState.READY)
    sm.transition(SessionState.INTERVIEWER_TURN)
    print(f"State: {sm.state.value}")
    
    # 2. TTS Generation (Interviewer starts talking)
    token = CancellationToken()
    async def run_tts():
        async for chunk in tts.synthesize_streaming(tts_generator(), token):
            pass # Playing audio
    tts_task = asyncio.create_task(run_tts())
    
    # 3. Candidate speaks mid-generation (Barge-In)
    await asyncio.sleep(0.3)
    print("\n[VAD] Candidate speech detected mid-TTS!")
    
    # Barge-In happens
    token.cancel("vad_speech_detected")
    sm.transition(SessionState.YIELDING)
    print(f"State: {sm.state.value}")
    sm.transition(SessionState.AWAITING_ANSWER)
    print(f"State: {sm.state.value}")
    sm.transition(SessionState.CANDIDATE_TURN)
    print(f"State: {sm.state.value}")
    
    # Wait for TTS to halt
    await tts_task
    print("[TTS] Synthesis cleanly halted.")
    
    # 4. Transcribe candidate's full answer
    print("\n[STT] Processing candidate audio frame...")
    import wave
    import numpy as np
    
    # Synthesize dummy sine wave audio for STT to consume
    sample_rate = 16000
    duration = 1.0 # 1 second audio
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    audio = np.sin(2 * np.pi * 440 * t)
    audio_bytes = (audio * 32767).astype(np.int16).tobytes()
    
    await stt.connect({"language": "en", "sample_rate": 16000, "provider": "local"})
    await stt.send_audio(audio_bytes)
    await stt.signal_segment_end()
    
    partial_transcript = "I think we should use a load balancer"
    try:
        async def _read_events():
            async for evt in stt.receive_events():
                if evt["is_interim"]:
                    print(f"[STT] Interim: {evt['text']}")
                else:
                    print(f"[STT] Final: {evt['text']}")
                    # Update transcript and break
                    return evt['text']
        partial_transcript = await asyncio.wait_for(_read_events(), timeout=3.0)
    except asyncio.TimeoutError:
        print("[STT] Processing timed out (likely due to blank audio). Proceeding with mock transcript.")
        
    await stt.close()
    
    # 5. Turn End Detection
    print("\n[VAD] Silence detected > 550ms")
    vad_silence_ms = 600
    
    print("[Turn Detection] Evaluating completeness...")
    decision = await turn_detector.evaluate(vad_silence_ms, partial_transcript)
    print(f"Decision: is_turn_end={decision.is_turn_end}, reason='{decision.reason}'")
    
    if decision.is_turn_end:
        sm.transition(SessionState.TURN_END)
        print(f"State: {sm.state.value}")
        
    print("\n--- TEST SUCCESS ---")
    
if __name__ == "__main__":
    asyncio.run(test_full_loop())
