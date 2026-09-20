import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

async def analyze_screenshot(image_bytes: bytes, gateway_router, routing_ctx) -> Dict:
    """
    Hybrid Pipeline: Attempts local OCR first. Escalates to VLM only if 
    confidence is low or structural diagrams are detected.
    """
    logger.info(f"Analyzing {len(image_bytes)} bytes screenshot payload.")
    
    # 1. Attempt Local OCR (Stub: PyTesseract / PaddleOCR)
    ocr_text = _run_local_ocr(image_bytes)
    
    classification = "unknown"
    problem_statement = ""
    
    # 2. Heuristic fast-pass to avoid VLM cost
    if not ocr_text:
        pass
    elif "def " in ocr_text or "class " in ocr_text:
        classification = "coding"
        problem_statement = ocr_text
    elif "SELECT " in ocr_text.upper() and "FROM " in ocr_text.upper():
        classification = "sql"
        problem_statement = ocr_text
    else:
        # 3. Escalate to VLM (Gateway 'vision' alias)
        logger.info("OCR heuristics failed or detected diagram. Escalating to Vision LLM.")
        
        # provider = gateway_router.route("vision", routing_ctx)
        # response = await provider.structured([{"role": "user", "content": "Extract and classify this problem."}], VisionSchema)
        
        # Stub VLM response
        classification = "system_design"
        problem_statement = "Design a distributed rate limiter. Diagram shows API Gateway pointing to Redis."
        
    return {
        "classification": classification,
        "problem_statement": problem_statement
    }

def _run_local_ocr(image_bytes: bytes) -> str:
    """Stubs out a local pytesseract call."""
    return "def reverse_linked_list(head):"
