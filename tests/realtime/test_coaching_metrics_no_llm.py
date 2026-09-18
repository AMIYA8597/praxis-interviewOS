import asyncio
import os
import sys
import time

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'packages', 'ai-gateway'))

import pytest
from realtime_agent.app.coaching.accumulator import CoachingMetricsAccumulator
from realtime_agent.app.protocol import Envelope

# Monkey-patch the gateway BEFORE importing it so it fails instantly if called.
from praxis_ai_gateway.router import GatewayRouter

original_route = GatewayRouter.route

def exploding_route(*args, **kwargs):
    raise AssertionError("GatewayRouter.route was called during coaching computation! LLM breach detected!")

GatewayRouter.route = exploding_route

async def run_metrics_test():
    emitted_events = []
    def mock_enqueue(envelope: Envelope, critical: bool = False):
        if envelope.type == "coaching.metrics":
            emitted_events.append(envelope)
            
    accumulator = CoachingMetricsAccumulator("test-session", mock_enqueue)
    
    print("--- Starting 10-Second Simulated Turn ---")
    accumulator.start_turn()
    
    # Simulate a candidate speaking
    transcript = ""
    words = ["So", "um", "I", "think", "the", "architecture", "is", "basically", "like", "a", "microservice", "pattern"]
    
    for i in range(10):
        await asyncio.sleep(1.0)
        
        # Simulate VAD gaps
        if i % 3 == 0:
            accumulator.register_vad_event("speech_end")
            await asyncio.sleep(0.5)
            accumulator.register_vad_event("speech_start")
            
        # Add a word
        if i < len(words):
            transcript += words[i] + " "
            accumulator.update_text(transcript)
            
    accumulator.end_turn()
    
    print(f"Total coaching events emitted: {len(emitted_events)}")
    assert len(emitted_events) > 30, "Should emit ~40 events over 10 seconds (250ms cadence)"
    
    # Check final payload
    final_payload = emitted_events[-1].payload
    print(f"Final Payload: {final_payload}")
    
    assert final_payload["fillers"]["total"] > 0, "Failed to detect fillers"
    assert final_payload["hedges"] > 0, "Failed to detect hedges"
    assert final_payload["wpm"] > 0, "WPM should be calculated"
    assert final_payload["pauses"]["count"] > 0, "Pauses should be detected"
    
    print("SUCCESS: Coaching metrics computed entirely locally. Gateway was never called.")

if __name__ == "__main__":
    asyncio.run(run_metrics_test())
