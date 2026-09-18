import asyncio
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'packages', 'ai-gateway'))

from realtime_agent.app.interview.turn_detection import TurnEndDetector, CompletenessResult
from praxis_ai_gateway.router import RoutingContext, RoutedCall

class MockRouter:
    async def route(self, task: str, context: RoutingContext, method_name: str, **kw):
        messages = kw.get("messages", [])
        content = messages[0]["content"]
        
        # Extract transcript portion
        try:
            transcript = content.split("<transcript>")[1].split("</transcript>")[0].strip()
        except IndexError:
            transcript = content
            
        if "how would you" in transcript.lower():
            result = CompletenessResult(is_complete=False)
        else:
            result = CompletenessResult(is_complete=True)
            
        return RoutedCall(provider_name="mock", model="mock", result=result)

async def test_genuine_mid_sentence():
    detector = TurnEndDetector(router=MockRouter(), silence_threshold_ms=550)
    
    print("--- 1. Testing genuine mid-sentence pause ---")
    decision = await detector.evaluate(600, "How would you ")
    print(decision)
    assert decision.is_turn_end is False
    assert decision.reason == "mid_sentence_pause"
    
    print("--- 2. Testing complete sentence ---")
    decision = await detector.evaluate(600, "I think we should use a load balancer.")
    print(decision)
    assert decision.is_turn_end is True
    assert decision.reason == "silence_and_semantically_complete"
    
    print("SUCCESS")
    
if __name__ == "__main__":
    asyncio.run(test_genuine_mid_sentence())
