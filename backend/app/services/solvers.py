"""
Hint ladder generator — produces graduated 3-level hints for coding/SQL/system-design
problems extracted from screenshots.

This module is a backend-layer wrapper. The primary call path is:
  study.py → realtime_agent.app.study.solver.generate_hint_ladder

The function here is used directly when callers stay within the backend package.
"""
import logging
from typing import Dict

logger = logging.getLogger(__name__)

_DOMAIN_GUIDANCE = {
    "coding": (
        "Focus on algorithm choice, time/space complexity, edge cases, "
        "and language-specific idioms."
    ),
    "sql": (
        "Focus on query structure, JOIN semantics, aggregation, window functions, "
        "and index usage."
    ),
    "system_design": (
        "Focus on component boundaries, data flow, scalability levers, "
        "consistency vs. availability trade-offs, and failure modes."
    ),
    "ml_chart": (
        "Focus on model interpretation, metric selection, overfitting/underfitting "
        "signals, and bias/variance trade-offs."
    ),
}

_GENERIC_FALLBACK = {
    "level_1_clarify": (
        "Read the problem statement carefully. Identify: inputs, outputs, constraints, "
        "and any edge cases before attempting a solution."
    ),
    "level_2_approach": (
        "Choose the appropriate pattern or data structure. Think through the time and "
        "space complexity before writing any code."
    ),
    "level_3_solution": (
        "Implement step by step. Start with a correct brute-force solution, then "
        "optimize. Verify against the given examples and at least two edge cases."
    ),
}


async def generate_hint_ladder(
    classification: str,
    problem_statement: str,
    gateway_router,
    routing_ctx,
) -> Dict:
    """
    Generate a 3-level hint ladder via the AI gateway.

    Level 1 — Clarify: what the problem asks, constraints, edge cases (NO solution).
    Level 2 — Approach: strategy and data structures (NO implementation code).
    Level 3 — Solution: complete implementation with complexity analysis.

    Falls back to domain-generic guidance if the gateway is unavailable.
    """
    if not problem_statement.strip() or gateway_router is None:
        return _domain_fallback(classification)

    from pydantic import BaseModel
    from praxis_ai_gateway.prompt_builder import PromptBuilder

    class HintLadder(BaseModel):
        level_1_clarify: str
        level_2_approach: str
        level_3_solution: str

    guidance = _DOMAIN_GUIDANCE.get(classification, "Focus on the core technical concepts.")

    builder = PromptBuilder()
    builder.add_system(
        f"Generate a 3-level hint ladder for the following technical interview problem "
        f"(type: {classification}). {guidance}\n\n"
        "Level 1 (clarify): explain what the problem asks, list constraints and edge cases. "
        "Do NOT reveal the approach or solution.\n"
        "Level 2 (approach): describe the strategy and data structures. "
        "Do NOT show implementation code.\n"
        "Level 3 (solution): provide the complete solution with complexity analysis."
    )
    builder.add_untrusted("problem_statement", "ocr_pipeline", problem_statement[:4000])
    builder.add_output_schema(HintLadder)

    try:
        call_result = await gateway_router.route(
            "reasoning",
            routing_ctx,
            "generate_structured",
            messages=[m.model_dump(exclude_none=True) for m in builder.build()],
            schema=HintLadder,
        )
        r: HintLadder = call_result.result
        return {
            "level_1_clarify": r.level_1_clarify,
            "level_2_approach": r.level_2_approach,
            "level_3_solution": r.level_3_solution,
        }
    except Exception as exc:
        logger.warning("hint_ladder_llm_failed: %s", exc)
        return _domain_fallback(classification)


def _domain_fallback(classification: str) -> Dict:
    guidance = _DOMAIN_GUIDANCE.get(classification, "")
    return {
        "level_1_clarify": (
            f"Read the problem statement carefully. {guidance} "
            "Identify inputs, outputs, constraints, and edge cases."
        ),
        "level_2_approach": (
            f"Choose the appropriate pattern for this {classification} problem. "
            "Consider time and space complexity before writing anything."
        ),
        "level_3_solution": (
            "Implement step by step, starting with a correct solution before optimizing. "
            "Test against the examples and edge cases."
        ),
    }
