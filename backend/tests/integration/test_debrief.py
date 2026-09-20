import pytest
from unittest.mock import AsyncMock, MagicMock
from backend.app.services.debrief import generate_session_debrief, SessionDebrief
from praxis_ai_gateway.router import RoutedCall
import uuid

@pytest.mark.asyncio
async def test_generate_session_debrief_varying_outputs():
    # 1. Mock DB Session
    mock_db = AsyncMock()
    
    # We will simulate db.execute returning different scalars based on session_id
    async def mock_execute(stmt):
        stmt_str = str(stmt).lower()
        res = MagicMock()
        
        # Determine session ID from stmt somehow, or we can just mock based on calls
        # We will just alternate the return values
        if not hasattr(mock_execute, "call_count"):
            mock_execute.call_count = 0
            
        mock_execute.call_count += 1
        
        # We call execute twice per session: metrics, then scores.
        # Call 1: metrics 1
        # Call 2: scores 1
        # Call 3: metrics 2
        # Call 4: scores 2
        
        class MockMetric:
            def __init__(self, wpm, filler):
                self.wpm = wpm
                self.filler_count = filler
                
        class MockScore:
            def __init__(self, relevance, id_str):
                self.relevance = relevance
                self.id = uuid.UUID(id_str)

        if mock_execute.call_count == 1:
            res.scalars().all.return_value = [MockMetric(150, 5), MockMetric(140, 2)]
        elif mock_execute.call_count == 2:
            res.scalars().all.return_value = [MockScore(0.9, "00000000-0000-0000-0000-000000000001")]
        elif mock_execute.call_count == 3:
            res.scalars().all.return_value = [MockMetric(110, 20), MockMetric(100, 25)]
        elif mock_execute.call_count == 4:
            res.scalars().all.return_value = [MockScore(0.4, "00000000-0000-0000-0000-000000000002")]
            
        return res
        
    mock_db.execute.side_effect = mock_execute
    
    # 2. Mock Gateway Router
    mock_gateway = AsyncMock()
    
    async def mock_route(alias, ctx, mode, messages, schema, **kw):
        assert alias == "deep_reasoning"
        prompt = messages[0].content
        
        if "Avg WPM: 145" in prompt:
            # Session 1 fake response
            debrief = SessionDebrief(
                headline_metrics={"average_wpm": 145.0, "average_filler_rate": 3.5, "average_score": 0.9},
                strengths=["Great pacing.", "Highly relevant answers."],
                weaknesses=["Slightly verbose at times."],
                flagged_claims=[],
                jd_coverage={}
            )
        else:
            # Session 2 fake response
            debrief = SessionDebrief(
                headline_metrics={"average_wpm": 105.0, "average_filler_rate": 22.5, "average_score": 0.4},
                strengths=["Good effort."],
                weaknesses=["Too many filler words.", "Low relevance."],
                flagged_claims=[],
                jd_coverage={}
            )
            
        class MockRoutedCall:
            def __init__(self, res):
                self.result = res
                
        return MockRoutedCall(debrief)
        
    mock_gateway.route.side_effect = mock_route
    
    # 3. Call the function twice
    session_id_1 = str(uuid.uuid4())
    session_id_2 = str(uuid.uuid4())
    
    output_1 = await generate_session_debrief(session_id_1, mock_db, mock_gateway)
    output_2 = await generate_session_debrief(session_id_2, mock_db, mock_gateway)
    
    print("\nSummary 1:", output_1["summary"])
    print("\nSummary 2:", output_2["summary"])
    
    # 4. Assertions
    fabricated_string = "You demonstrated strong architectural knowledge, but your STAR structuring was inconsistent"
    
    assert fabricated_string not in output_1["summary"]
    assert fabricated_string not in output_2["summary"]
    
    assert output_1["summary"] != output_2["summary"]
    assert "Great pacing" in output_1["summary"]
    assert "Too many filler words" in output_2["summary"]
