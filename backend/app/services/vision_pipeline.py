"""
Screenshot analysis pipeline — OCR-first with VLM escalation.

This module is a backend-layer wrapper around the canonical implementation in
packages/ai-gateway/praxis_ai_gateway/vision/ocr_pipeline.py.
It exists for backward compatibility with any direct callers within the backend package.
The primary call path is: study.py → praxis_ai_gateway.vision.ocr_pipeline.
"""
import io
import logging
from typing import Dict

logger = logging.getLogger(__name__)


def _run_local_ocr(image_bytes: bytes) -> str:
    """Run Tesseract OCR on image bytes. Returns extracted text or empty string."""
    try:
        import pytesseract
        from PIL import Image

        img = Image.open(io.BytesIO(image_bytes))
        text = pytesseract.image_to_string(img).strip()
        return text
    except Exception as exc:
        logger.warning("local_ocr_failed: %s", exc)
        return ""


async def analyze_screenshot(
    image_bytes: bytes,
    gateway_router,
    routing_ctx,
) -> Dict:
    """
    Hybrid pipeline: Tesseract OCR first; escalate to VLM when OCR confidence is
    low, text is absent, or structural elements (diagrams) are detected.

    Returns {"classification": str, "problem_statement": str}.
    Classifications: coding | sql | system_design | ml_chart | general_question | unknown
    """
    logger.info("analyze_screenshot: %d bytes", len(image_bytes))

    ocr_text = _run_local_ocr(image_bytes)

    # Route based on OCR content
    if not ocr_text:
        # No text extracted — likely a diagram; delegate to VLM
        return await _classify_via_vlm(image_bytes, gateway_router, routing_ctx, fallback_ocr="")

    text_upper = ocr_text.upper()

    if "def " in ocr_text or "class " in ocr_text or "=>" in ocr_text or "func " in ocr_text:
        return {"classification": "coding", "problem_statement": ocr_text}

    if "SELECT " in text_upper and "FROM " in text_upper:
        return {"classification": "sql", "problem_statement": ocr_text}

    # Short text without code markers may be diagram labels — escalate to VLM
    if len(ocr_text.split()) < 15:
        return await _classify_via_vlm(image_bytes, gateway_router, routing_ctx, fallback_ocr=ocr_text)

    return {"classification": "general_question", "problem_statement": ocr_text}


async def _classify_via_vlm(
    image_bytes: bytes,
    gateway_router,
    routing_ctx,
    *,
    fallback_ocr: str,
) -> Dict:
    """Escalate to gateway vision model. Falls back to system_design if unavailable."""
    if gateway_router is None:
        return {"classification": "system_design", "problem_statement": fallback_ocr}

    from pydantic import BaseModel
    from praxis_ai_gateway.prompt_builder import PromptBuilder

    class _VisionResult(BaseModel):
        classification: str
        problem_statement: str

    builder = PromptBuilder()
    builder.add_system(
        "Analyze this technical interview screenshot. "
        "Classify it as exactly one of: coding, sql, system_design, ml_chart, general_question. "
        "Extract the complete problem statement text."
    )
    builder.add_output_schema(_VisionResult)

    try:
        result = await gateway_router.route(
            "vision",
            routing_ctx,
            "generate_structured",
            messages=[
                {
                    "role": "user",
                    "content": [{"type": "image", "image": image_bytes}],
                }
            ],
            schema=_VisionResult,
        )
        return {
            "classification": result.result.classification,
            "problem_statement": result.result.problem_statement,
        }
    except Exception as exc:
        logger.warning("vlm_escalation_failed: %s", exc)
        return {"classification": "system_design", "problem_statement": fallback_ocr}
