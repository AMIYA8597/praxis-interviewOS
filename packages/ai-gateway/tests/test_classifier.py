import pytest
from unittest.mock import MagicMock, AsyncMock
from praxis_ai_gateway.classification import FastClassifier

@pytest.mark.asyncio
async def test_fast_classifier_false_question_filter():
    mock_router = MagicMock()
    # We shouldn't even call route if the fast path works
    mock_router.route = AsyncMock()
    
    classifier = FastClassifier(router=mock_router)
    
    result = await classifier.classify("Okay, great.")
    
    assert result.is_question is False
    assert result.question_type == "other"
    # Ensure router was NOT called
    mock_router.route.assert_not_called()
