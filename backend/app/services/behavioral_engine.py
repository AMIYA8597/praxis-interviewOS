"""
Phase 65 — Behavioral + Resume Defense Engine.

STAR evaluation with per-component scoring + resume claim deep-dive.
Integrates with scoring service (Phase 53 rubric) and grounding service.

Resume defense: pick a specific resume claim and ask the candidate to
justify it with evidence. Uses verified_context from the job blueprint.
"""
import logging
import re

logger = logging.getLogger(__name__)

# STAR component detection patterns
_SITUATION_PATTERNS = [
    r"\b(at|when|while|during|in) (my|our|the) (previous|last|current|former)\b",
    r"\b(we|i|our team) (were|was|had to|needed to)\b",
    r"\bsituation\b",
    r"\bcontext\b",
]

_TASK_PATTERNS = [
    r"\b(my|the) (task|responsibility|goal|objective) was\b",
    r"\bi (was|were) (responsible|tasked) (for|with)\b",
    r"\btask\b",
]

_ACTION_PATTERNS = [
    r"\bi (decided|chose|implemented|built|wrote|created|led|managed|coordinated|deployed)\b",
    r"\baction\b",
    r"\bsteps? (i|we) took\b",
    r"\bso i\b",
    r"\bfirst.*then.*finally\b",
]

_RESULT_PATTERNS = [
    r"\bas a result\b",
    r"\bthis (led to|resulted in|reduced|improved|increased|saved)\b",
    r"\b(reduced|improved|increased|saved|achieved|delivered|shipped)\b.*\b(\d+|percent|%)\b",
    r"\bresult\b",
    r"\boutcome\b",
]


def detect_star_components(answer: str) -> dict:
    """
    Rule-based STAR detection from answer text.
    Returns {situation, task, action, result} booleans + evidence.
    """
    answer_lower = answer.lower()
    results = {}

    for component, patterns in [
        ("situation", _SITUATION_PATTERNS),
        ("task", _TASK_PATTERNS),
        ("action", _ACTION_PATTERNS),
        ("result", _RESULT_PATTERNS),
    ]:
        matched = any(re.search(p, answer_lower) for p in patterns)
        results[component] = {"present": matched}

    # Check for quantified result (stronger signal)
    has_quantified_result = bool(
        re.search(r"\b\d+\s*(%|percent|ms|seconds?|hours?|days?|users?|requests?|x)\b", answer_lower)
    )
    results["result"]["quantified"] = has_quantified_result

    completeness = sum(1 for c in ["situation", "task", "action", "result"] if results[c]["present"])
    results["completeness_score"] = completeness / 4.0
    results["all_present"] = completeness == 4

    return results


def generate_star_feedback(star_result: dict, answer: str) -> str:
    """
    Generate specific, evidence-based STAR feedback.
    No generic platitudes — points to what's actually missing.
    """
    parts = []
    missing = [c for c in ["situation", "task", "action", "result"] if not star_result[c]["present"]]

    if not missing:
        if star_result["result"].get("quantified"):
            parts.append("Complete STAR structure with quantified result — strong answer.")
        else:
            parts.append("Complete STAR structure present. Consider adding a specific metric to the result.")
    else:
        parts.append(f"Missing STAR components: {', '.join(missing).upper()}.")

        if "situation" in missing:
            parts.append("Add context: where were you working, what was the state of the system/team?")
        if "task" in missing:
            parts.append("Be explicit about YOUR responsibility: 'My task was to...'")
        if "action" in missing:
            parts.append("Describe specific actions YOU took — not what the team did in general.")
        if "result" in missing:
            parts.append("Always end with a measurable outcome: reduced X by Y%, shipped by date, etc.")

    return " ".join(parts)


def generate_resume_defense_question(resume_claim: str, context: str = "") -> str:
    """
    Generate a specific probe question for a resume claim.
    """
    claim_lower = resume_claim.lower()

    # Identify the type of claim and generate a targeted challenge
    if any(kw in claim_lower for kw in ["led", "managed", "owned", "responsible"]):
        return (
            f"You mentioned '{resume_claim}'. Describe a specific decision you made "
            "in that role that you could not have made without that level of ownership. "
            "What was the outcome?"
        )

    if any(kw in claim_lower for kw in ["built", "developed", "implemented", "designed"]):
        return (
            f"You mentioned '{resume_claim}'. Walk me through the hardest technical "
            "challenge you hit while building this. How did you resolve it?"
        )

    if any(kw in claim_lower for kw in ["improved", "reduced", "increased", "saved", "%"]):
        return (
            f"You mentioned '{resume_claim}'. How did you measure that result? "
            "What was the baseline before you started?"
        )

    return (
        f"Tell me more about: '{resume_claim}'. "
        "Give me a specific example that demonstrates this — what was the context, "
        "what did you personally do, and what was the measurable outcome?"
    )
