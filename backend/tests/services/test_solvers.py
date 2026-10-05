"""
Tests for vision_pipeline.py (OCR + VLM escalation) and solvers.py (hint ladder).
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.app.services.vision_pipeline import analyze_screenshot
from backend.app.services.solvers import generate_hint_ladder


# ── vision_pipeline tests ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_vision_pipeline_coding_detected_via_ocr():
    """OCR that returns Python code is classified as coding without VLM."""
    with patch("backend.app.services.vision_pipeline._run_local_ocr", return_value="def reverse(lst):\n    return lst[::-1]"):
        result = await analyze_screenshot(b"fake_image", None, None)
    assert result["classification"] == "coding"
    assert "reverse" in result["problem_statement"]


@pytest.mark.asyncio
async def test_vision_pipeline_sql_detected_via_ocr():
    """OCR that returns SQL is classified as sql without VLM."""
    with patch("backend.app.services.vision_pipeline._run_local_ocr", return_value="SELECT id FROM users ORDER BY created_at DESC"):
        result = await analyze_screenshot(b"fake_image", None, None)
    assert result["classification"] == "sql"


@pytest.mark.asyncio
async def test_vision_pipeline_handles_empty_ocr_no_gateway():
    """When OCR returns empty text and no gateway is provided, falls back to system_design."""
    with patch("backend.app.services.vision_pipeline._run_local_ocr", return_value=""):
        result = await analyze_screenshot(b"fake_image", None, None)
    assert result["classification"] == "system_design"


@pytest.mark.asyncio
async def test_vision_pipeline_escalates_to_vlm_on_empty_ocr():
    """When OCR returns empty text, the pipeline calls the VLM gateway."""
    mock_vlm_result = MagicMock()
    mock_vlm_result.result.classification = "system_design"
    mock_vlm_result.result.problem_statement = "Design a URL shortener."

    mock_gateway = AsyncMock()
    mock_gateway.route = AsyncMock(return_value=mock_vlm_result)

    with patch("backend.app.services.vision_pipeline._run_local_ocr", return_value=""):
        result = await analyze_screenshot(b"fake_image", mock_gateway, None)

    assert result["classification"] == "system_design"
    assert result["problem_statement"] == "Design a URL shortener."
    mock_gateway.route.assert_called_once()


@pytest.mark.asyncio
async def test_vision_pipeline_vlm_failure_falls_back():
    """If the VLM call raises, the pipeline still returns a valid response."""
    mock_gateway = AsyncMock()
    mock_gateway.route = AsyncMock(side_effect=RuntimeError("provider unavailable"))

    with patch("backend.app.services.vision_pipeline._run_local_ocr", return_value=""):
        result = await analyze_screenshot(b"fake_image", mock_gateway, None)

    assert result["classification"] == "system_design"
    assert isinstance(result["problem_statement"], str)


# ── solvers tests ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_hint_ladder_no_gateway_returns_fallback():
    """Without a gateway, generate_hint_ladder returns domain-generic guidance."""
    result = await generate_hint_ladder("coding", "Two Sum problem", None, None)
    assert "level_1_clarify" in result
    assert "level_2_approach" in result
    assert "level_3_solution" in result
    assert len(result["level_1_clarify"]) > 10


@pytest.mark.asyncio
async def test_hint_ladder_uses_gateway_when_available():
    """With a gateway, generate_hint_ladder calls route() and returns LLM output."""
    mock_hints = MagicMock()
    mock_hints.result.level_1_clarify = "Clarify: find two numbers that sum to target."
    mock_hints.result.level_2_approach = "Approach: use a hash map."
    mock_hints.result.level_3_solution = "Solution: seen = {}; ..."

    mock_gateway = AsyncMock()
    mock_gateway.route = AsyncMock(return_value=mock_hints)

    result = await generate_hint_ladder("coding", "Two Sum", mock_gateway, None)

    assert result["level_1_clarify"] == "Clarify: find two numbers that sum to target."
    assert result["level_2_approach"] == "Approach: use a hash map."
    mock_gateway.route.assert_called_once()


@pytest.mark.asyncio
async def test_hint_ladder_gateway_failure_returns_fallback():
    """If the LLM call fails, generate_hint_ladder returns domain fallback."""
    mock_gateway = AsyncMock()
    mock_gateway.route = AsyncMock(side_effect=RuntimeError("model unavailable"))

    result = await generate_hint_ladder("sql", "Find the second highest salary", mock_gateway, None)

    assert "level_1_clarify" in result
    assert "sql" in result["level_1_clarify"].lower() or len(result["level_1_clarify"]) > 10


@pytest.mark.asyncio
async def test_hint_ladder_empty_problem_returns_fallback():
    """Empty problem statement skips the LLM and returns fallback immediately."""
    mock_gateway = AsyncMock()
    result = await generate_hint_ladder("coding", "", mock_gateway, None)
    mock_gateway.route.assert_not_called()
    assert "level_1_clarify" in result
