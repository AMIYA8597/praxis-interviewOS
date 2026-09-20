import pytest
from unittest.mock import AsyncMock, patch
from realtime_agent.app.scoring.service import calculate_grounding_score, score_answer_async
from praxis_ai_gateway.base import LLMResponse
from praxis_ai_gateway.router import RoutedCall

from realtime_agent.app.scoring.service import calculate_grounding_score, score_answer_async, verify_claim

@pytest.mark.asyncio
async def test_calculate_grounding_score():
    mock_router = AsyncMock()
    
    # Return "YES" for verify_claim
    mock_response = LLMResponse(text="YES, it is supported.", latency_ms=100, model="test", provider="test")
    mock_router.route.return_value = RoutedCall(provider_name="test", model="test", result=mock_response)
    
    # Test verify_claim directly
    is_supported = await verify_claim("test claim", "test context", mock_router, None)
    assert is_supported is True
    
    with patch("realtime_agent.app.scoring.service.extract_claims", return_value=["claim 1"]):
        score = await calculate_grounding_score("answer", "context", mock_router, None)
        assert score == 1.0

@pytest.mark.asyncio
async def test_score_answer_async():
    mock_router = AsyncMock()
    
    class FakeLlmScoringResult:
        relevance = 0.8
        correctness = 0.9
        structure = 0.7
        specificity = 0.8
        conciseness = 0.9
        star_completeness = None
        rationale = "good"
        
    mock_router.route.return_value = RoutedCall(
        provider_name="test",
        model="test",
        result=FakeLlmScoringResult()
    )
    
    with patch("realtime_agent.app.scoring.service.calculate_grounding_score", return_value=1.0):
        result = await score_answer_async("question", "answer", False, "context", mock_router, None)
        
        # correctness(0.3)*0.9 + relevance(0.2)*0.8 + specificity(0.2)*0.8 + structure(0.1)*0.7 + grounding(0.1)*1.0 + conciseness(0.1)*0.9
        # = 0.27 + 0.16 + 0.16 + 0.07 + 0.10 + 0.09 = 0.85
        assert abs(result.overall - 0.85) < 0.01
        assert result.grounding == 1.0
