import logging
from typing import Optional, Tuple, Literal
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class OcrResult(BaseModel):
    text: str
    confidence: float
    is_diagram_heuristic: bool

# Stub for local OCR engine (e.g., Tesseract or PaddleOCR)
def run_local_ocr(image_bytes: bytes) -> OcrResult:
    """
    Mock local OCR engine (Tesseract 5 or PaddleOCR).
    """
    # Test fixture routing
    if b"mock_diagram" in image_bytes:
        return OcrResult(text="Garbled... [] --", confidence=0.2, is_diagram_heuristic=True)
    elif b"mock_coding" in image_bytes:
        return OcrResult(
            text="def two_sum(nums, target):\n    seen = {}\n    for i, n in enumerate(nums):\n        if target - n in seen:\n            return [seen[target - n], i]",
            confidence=0.95,
            is_diagram_heuristic=False
        )
    elif b"mock_sql" in image_bytes:
        return OcrResult(
            text="CREATE TABLE employees (id INT, salary INT);\nSELECT * FROM employees ORDER BY salary DESC LIMIT 1;",
            confidence=0.92,
            is_diagram_heuristic=False
        )
    
    return OcrResult(text="", confidence=0.0, is_diagram_heuristic=True)

class HybridPipelineResponse(BaseModel):
    extracted_text: str
    used_vision_escalation: bool
    vision_image_bytes: Optional[bytes] = None

async def process_screenshot_hybrid(image_bytes: bytes, gateway_router, routing_ctx) -> HybridPipelineResponse:
    """
    Task 1: OCR-first Hybrid Pipeline.
    Runs local OCR. If high confidence and looks like code/prose, use OCR only.
    If low confidence OR clearly a diagram, escalate to vision alias.
    """
    ocr_result = run_local_ocr(image_bytes)
    
    # Heuristic for "clean code/prose"
    lines = ocr_result.text.strip().split('\n')
    looks_clean = len(lines) > 0 and len([l for l in lines if len(l.strip()) > 5]) >= (len(lines) * 0.3)
    
    if ocr_result.confidence > 0.8 and looks_clean and not ocr_result.is_diagram_heuristic:
        logger.info("OCR confidence high. Using OCR text only.")
        return HybridPipelineResponse(
            extracted_text=ocr_result.text,
            used_vision_escalation=False
        )
    
    logger.info("OCR confidence low or diagram detected. Escalating to vision model.")
    # Escalate to vision model
    # (Mocking the vision escalation call)
    try:
        class VisionExtraction(BaseModel):
            description: str
            
        call_result = await gateway_router.route(
            "vision",
            routing_ctx,
            "generate_structured",
            messages=[
                {"role": "system", "content": "Extract and describe all text and structure from this image."},
                {"role": "user", "content": [{"type": "image", "image": image_bytes}]} # Multimodal payload
            ],
            schema=VisionExtraction
        )
        return HybridPipelineResponse(
            extracted_text=call_result.result.description,
            used_vision_escalation=True,
            vision_image_bytes=image_bytes
        )
    except Exception as e:
        logger.error(f"Vision escalation failed: {e}")
        return HybridPipelineResponse(
            extracted_text=ocr_result.text, # Fallback to garbled OCR
            used_vision_escalation=True,
            vision_image_bytes=image_bytes
        )
