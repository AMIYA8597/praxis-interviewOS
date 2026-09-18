import asyncio
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from realtime_agent.app.coaching.accumulator import CoachingMetricsAccumulator
from realtime_agent.app.protocol import Envelope

async def slow_reasoning_generation():
    """Mock a 1-second reasoning path generation call."""
    print("[Reasoning] AI is thinking...")
    await asyncio.sleep(1.0)
    print("[Reasoning] AI finished thinking.")
    return "This is the generated response."

async def run_concurrent_test():
    emitted_events = []
    def mock_enqueue(envelope: Envelope, critical: bool = False):
        if envelope.type == "coaching.metrics":
            emitted_events.append(envelope)
            print(f"[Coaching] Emitted metrics update: {envelope.payload['wpm']} WPM")
            
    accumulator = CoachingMetricsAccumulator("test-session", mock_enqueue)
    accumulator.start_turn()
    accumulator.update_text("Hello um actually")
    
    # Run the slow reasoning concurrently with the accumulator
    generation_task = asyncio.create_task(slow_reasoning_generation())
    
    # Wait for reasoning to finish
    await generation_task
    
    accumulator.end_turn()
    
    print(f"Total coaching updates emitted BEFORE reasoning finished: {len(emitted_events)}")
    assert len(emitted_events) >= 3, "HUD must update multiple times while AI is thinking"
    
if __name__ == "__main__":
    asyncio.run(run_concurrent_test())
