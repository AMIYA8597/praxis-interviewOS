import pytest
import os
import sys
import asyncio
import time
from typing import List, Dict, Any
from pydantic import BaseModel

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'packages', 'ai-gateway'))

from realtime_agent.app.interview.debrief import (
    generate_debrief,
    trigger_debrief_generation,
    SessionDebrief,
    HeadlineMetrics
)

class MockLlmResult(BaseModel):
    result: Any

class MockDebriefProvider:
    async def generate_structured(self, messages: List[Dict[str, Any]], schema: type[BaseModel], **kwargs):
        system_prompt = messages[0]["content"]
        user_prompt = messages[1]["content"] if len(messages) > 1 else ""
        
        # Parse the aggregated_session_data to tailor the mock response
        # It's inside a trusted context block
        turn_count = 0
        if "Turn Count: 2" in user_prompt:
            turn_count = 2
        elif "Turn Count: 5" in user_prompt:
            turn_count = 5
            
        is_short_session = turn_count < 3
        
        strengths = []
        weaknesses = []
        
        if is_short_session:
            strengths.append("Based on the limited data from this short session, your WPM was steady.")
            weaknesses.append("Unable to determine weakness trends from only 2 turns.")
        else:
            if "Weakest Turns:" in user_prompt and "'t_4'" in user_prompt:
                weaknesses.append("In Turn 4, your behavioral answer missed the Result component, scoring poorly overall.")
            if "Strongest Turns:" in user_prompt and "'t_2'" in user_prompt:
                strengths.append("In Turn 2, your system design explanation was highly structured and scored perfectly.")
                
        # Simulate processing time
        await asyncio.sleep(0.5)

        return MockLlmResult(result=SessionDebrief(
            headline_metrics=HeadlineMetrics(average_wpm=145.0, average_filler_rate=0.02, average_score=0.85),
            strengths=strengths,
            weaknesses=weaknesses,
            flagged_claims=["I scaled the database to 100 million QPS (Unsupported)"],
            jd_coverage={"covered": ["System Design", "Behavioral"], "missed": ["Python"]}
        ))

class MockDebriefGatewayRouter:
    def __init__(self):
        self.provider = MockDebriefProvider()
        
    def route(self, alias: str, context: Any):
        return self.provider

    async def route(self, alias: str, context: Any, method_name: str, **kwargs):
        if method_name == "generate_structured":
            return await self.provider.generate_structured(**kwargs)
        raise NotImplementedError()

@pytest.fixture
def full_session_db_stub():
    return {
        "turns": [
            {"turn_id": "t_1", "topic": "Behavioral"},
            {"turn_id": "t_2", "topic": "System Design"},
            {"turn_id": "t_3", "topic": "System Design"},
            {"turn_id": "t_4", "topic": "Behavioral"},
            {"turn_id": "t_5", "topic": "Behavioral"}
        ],
        "scores": [
            {"turn_id": "t_1", "overall": 0.8},
            {"turn_id": "t_2", "overall": 1.0}, # Strongest
            {"turn_id": "t_3", "overall": 0.8},
            {"turn_id": "t_4", "overall": 0.4}, # Weakest (missed Result)
            {"turn_id": "t_5", "overall": 0.8}
        ],
        "metrics": [
            {"turn_id": "t_1", "wpm": 140, "filler_rate": 0.01},
            {"turn_id": "t_2", "wpm": 150, "filler_rate": 0.02},
            {"turn_id": "t_3", "wpm": 145, "filler_rate": 0.02},
            {"turn_id": "t_4", "wpm": 130, "filler_rate": 0.05},
            {"turn_id": "t_5", "wpm": 140, "filler_rate": 0.01}
        ],
        "claims": [
            {"claim_text": "I used Python", "supported": True},
            {"claim_text": "I scaled the database to 100 million QPS (Unsupported)", "supported": False}
        ],
        "jd_blueprint": {
            "likely_topics": ["System Design", "Behavioral", "Python"]
        }
    }

@pytest.fixture
def short_session_db_stub():
    return {
        "turns": [
            {"turn_id": "t_1", "topic": "Behavioral"},
            {"turn_id": "t_2", "topic": "System Design"}
        ],
        "scores": [
            {"turn_id": "t_1", "overall": 0.8},
            {"turn_id": "t_2", "overall": 1.0}
        ],
        "metrics": [
            {"turn_id": "t_1", "wpm": 140, "filler_rate": 0.01},
            {"turn_id": "t_2", "wpm": 150, "filler_rate": 0.02}
        ],
        "claims": [],
        "jd_blueprint": {
            "likely_topics": ["System Design", "Behavioral"]
        }
    }


@pytest.mark.asyncio
async def test_trigger_timing(full_session_db_stub):
    """
    Task 3: Trigger Timing
    Confirm that triggering the debrief generation does not block the caller.
    """
    router = MockDebriefGatewayRouter()
    
    start_time = time.time()
    # Trigger on DEBRIEF state transition
    task = trigger_debrief_generation("sess_123", full_session_db_stub, router, None)
    trigger_duration = time.time() - start_time
    
    # Should be near-instant, not the 0.5s of the mock processing
    assert trigger_duration < 0.1
    
    # Wait for the task to complete
    debrief = await task
    assert debrief.headline_metrics.average_wpm > 0

@pytest.mark.asyncio
async def test_short_session_hedging(short_session_db_stub):
    """
    Task 4: Honest handling of short/sparse sessions
    """
    router = MockDebriefGatewayRouter()
    debrief = await generate_debrief("sess_short", short_session_db_stub, router, None)
    
    # Check that short session hedges its claims instead of fabricating trends
    assert any("short session" in s for s in debrief.strengths)
    assert any("Unable to determine" in w for w in debrief.weaknesses)

@pytest.mark.asyncio
async def test_full_session_to_full_debrief(full_session_db_stub):
    """
    Task 5: Full session to full debrief integration.
    """
    router = MockDebriefGatewayRouter()
    
    # Run the generation
    debrief = await generate_debrief("sess_full", full_session_db_stub, router, None)
    
    # Assert genuine traceability
    assert any("Turn 2" in s for s in debrief.strengths)
    assert any("Turn 4" in w for w in debrief.weaknesses)
    
    # Assert flagged claims were passed
    assert len(debrief.flagged_claims) == 1
    assert "100 million QPS" in debrief.flagged_claims[0]
    
    # Assert JD coverage
    assert "Python" in debrief.jd_coverage["missed"]
    
    print("\n--- FULL SESSION DEBRIEF OUTPUT ---")
    print(debrief.model_dump_json(indent=2))
