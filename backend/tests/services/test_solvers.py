import pytest
from unittest.mock import AsyncMock, patch
from backend.app.services.vision_pipeline import analyze_screenshot

@pytest.mark.asyncio
async def test_vision_pipeline_handles_none_ocr():
    mock_router = AsyncMock()
    
    with patch("backend.app.services.vision_pipeline._run_local_ocr", return_value=None):
        result = await analyze_screenshot(b"fake", mock_router, None)
        assert result["classification"] == "system_design"
        assert result["problem_statement"] != ""
