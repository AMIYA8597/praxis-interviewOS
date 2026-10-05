import asyncio
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'packages', 'ai-gateway'))

from realtime_agent.app.coaching.accumulator import CoachingMetricsAccumulator
from realtime_agent.app.protocol import Envelope
from praxis_ai_gateway.router import GatewayRouter

async def run_metrics_test():
    # Patch only for the duration of this test, then restore so other tests
    # collected in the same process are not affected.
    original_route = GatewayRouter.route

    def exploding_route(*args, **kwargs):
        raise AssertionError("GatewayRouter.route was called during coaching computation! LLM breach detected!")

    GatewayRouter.route = exploding_route
    try:
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
    finally:
        GatewayRouter.route = original_route

if __name__ == "__main__":
    asyncio.run(run_metrics_test())
