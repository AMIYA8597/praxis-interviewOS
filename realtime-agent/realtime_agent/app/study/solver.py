import uuid
import logging
from typing import Dict, List, Optional
from realtime_agent.app.study.models import ScreenshotType, HintLadder, ClassificationResult, SolverResult, StudyItem
from praxis_ai_gateway.prompt_builder import PromptBuilder

logger = logging.getLogger(__name__)

# Global mock DB
_SOLVER_DB: List[SolverResult] = []
_STUDY_DB: List[StudyItem] = []

async def classify_screenshot(extracted_text: str, gateway_router, routing_ctx) -> ScreenshotType:
    """
    Task 2: Screenshot Classification.
    Determines which specialized solver prompt gets used.
    """
    builder = PromptBuilder()
    builder.add_system("Classify the provided extracted screenshot text/content into one of the following types: coding, sql, system_design_diagram, ml_chart, math, general_question, unknown.")
    builder.add_task("Classify this extracted text.")
    builder.add_untrusted("extracted_content", "ocr_pipeline", extracted_text)
    builder.add_output_schema(ClassificationResult)
    
    try:
        call_result = await gateway_router.route(
            "fast_classify",
            routing_ctx,
            "generate_structured",
            messages=[m.model_dump(exclude_none=True) for m in builder.build()],
            schema=ClassificationResult
        )
        return call_result.result.screenshot_type
    except Exception as e:
        logger.error(f"Failed to classify screenshot: {e}")
        return ScreenshotType.unknown

async def generate_hint_ladder(extracted_text: str, screenshot_type: ScreenshotType, gateway_router, routing_ctx) -> HintLadder:
    """
    Task 3 & 4: The Hint-Ladder Structure and Per-Type Prompts.
    """
    prompt_file = "prompts/solving/coding_v1.md"
    if screenshot_type == ScreenshotType.sql:
        prompt_file = "prompts/solving/sql_v1.md"
    elif screenshot_type == ScreenshotType.system_design_diagram:
        prompt_file = "prompts/solving/system_design_v1.md"
    elif screenshot_type == ScreenshotType.ml_chart:
        prompt_file = "prompts/solving/ml_v1.md"
    # Fallback to coding for general
    
    with open(prompt_file, "r") as f:
        sys_prompt = f.read()
        
    builder = PromptBuilder()
    builder.add_system(sys_prompt)
    builder.add_untrusted("screenshot_content", "ocr_pipeline", extracted_text)
    builder.add_output_schema(HintLadder)
    
    try:
        call_result = await gateway_router.route(
            "deep_reasoning",
            routing_ctx,
            "generate_structured",
            messages=[m.model_dump(exclude_none=True) for m in builder.build()],
            schema=HintLadder
        )
        return call_result.result
    except Exception as e:
        logger.error(f"Failed to generate hint ladder: {e}")
        return HintLadder(clarify="Error", approach="Error", solution="Error")

async def solve_screenshot(extracted_text: str, gateway_router, routing_ctx) -> SolverResult:
    """
    Coordinates classification and hint ladder generation.
    """
    screenshot_type = await classify_screenshot(extracted_text, gateway_router, routing_ctx)
    hints = await generate_hint_ladder(extracted_text, screenshot_type, gateway_router, routing_ctx)
    
    solver_result = SolverResult(
        id=str(uuid.uuid4()),
        screenshot_type=screenshot_type,
        hints=hints
    )
    _SOLVER_DB.append(solver_result)
    return solver_result

def create_study_item_from_solve(solver_result_id: str) -> StudyItem:
    """
    Task 6: Save to Study Plan Integration.
    """
    solver_result = next((r for r in _SOLVER_DB if r.id == solver_result_id), None)
    if not solver_result:
        raise ValueError(f"No solver result found for id {solver_result_id}")
        
    # Extract the core concept from the level 1 (clarify) hint.
    # We will just use the first sentence or so.
    concept = solver_result.hints.clarify.split(".")[0]
    
    item = StudyItem(
        id=str(uuid.uuid4()),
        source="screenshot_solve",
        solver_result_id=solver_result_id,
        concept=concept
    )
    _STUDY_DB.append(item)
    return item
