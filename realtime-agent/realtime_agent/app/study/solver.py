import uuid
import logging
from typing import Dict, List, Optional
from realtime_agent.app.study.models import ScreenshotType, HintLadder, ClassificationResult, SolverResult, StudyItem
from praxis_ai_gateway.prompt_builder import PromptBuilder

logger = logging.getLogger(__name__)



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

async def solve_screenshot(extracted_text: str, screenshot_task_id: str, gateway_router, routing_ctx) -> dict:
    """
    Coordinates classification and hint ladder generation, saves to DB.
    """
    screenshot_type = await classify_screenshot(extracted_text, gateway_router, routing_ctx)
    hints = await generate_hint_ladder(extracted_text, screenshot_type, gateway_router, routing_ctx)
    
    import json
    from sqlalchemy import text
    query = text("""
        INSERT INTO solver_results (screenshot_task_id, screenshot_type, hints)
        VALUES (:tid, :stype, :hints)
        RETURNING id
    """)
    res = await gateway_router.db.execute(query, {
        "tid": screenshot_task_id,
        "stype": screenshot_type.value if hasattr(screenshot_type, "value") else str(screenshot_type),
        "hints": json.dumps(hints.model_dump())
    })
    await gateway_router.db.commit()
    inserted_id = res.scalar()
    
    return {
        "id": str(inserted_id),
        "screenshot_type": screenshot_type,
        "hints": hints
    }

async def create_study_item_from_solve(solver_result_id: str, candidate_id: str, db) -> dict:
    """
    Task 6: Save to Study Plan Integration.
    """
    from sqlalchemy import text
    import json
    
    # Get solver result
    query = text("SELECT hints FROM solver_results WHERE id = :id")
    res = await db.execute(query, {"id": solver_result_id})
    row = res.fetchone()
    if not row:
        raise ValueError(f"No solver result found for id {solver_result_id}")
        
    hints_dict = row[0]
    if isinstance(hints_dict, str):
        hints_dict = json.loads(hints_dict)
        
    concept = hints_dict.get("clarify", "Unknown").split(".")[0]
    
    # Save to study items
    insert_q = text("""
        INSERT INTO study_items (candidate_id, topic, source, prompt, solver_result_id)
        VALUES (:cid, :topic, 'screenshot_solve', :prompt, :sid)
        RETURNING id
    """)
    res_ins = await db.execute(insert_q, {
        "cid": candidate_id,
        "topic": concept,
        "prompt": hints_dict.get("approach", ""),
        "sid": solver_result_id
    })
    await db.commit()
    item_id = res_ins.scalar()
    
    return {
        "id": str(item_id),
        "source": "screenshot_solve",
        "solver_result_id": solver_result_id,
        "concept": concept
    }
