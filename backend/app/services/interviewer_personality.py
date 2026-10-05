"""
Phase 61 — Interviewer Personality.

Personality ONLY changes communication style/tone in prompts.
The scoring rubric is CONSTANT regardless of personality.
Real interview pressure comes from question difficulty (Phase 60), not from
hiding the rubric or making scoring inconsistent.
"""
from typing import Literal

PersonalityType = Literal[
    "neutral", "technical", "strict", "faang_style", "supportive", "pressure_test"
]

_PERSONALITY_SYSTEM_ADDITIONS: dict[str, str] = {
    "neutral": "",
    "technical": (
        "\nCommunication style: technical and precise. Ask follow-up questions that probe "
        "implementation depth: 'How would you handle X at 10x scale?', 'What's the time complexity?', "
        "'Walk me through the edge cases.' Do NOT soften questions."
    ),
    "strict": (
        "\nCommunication style: terse and evaluative. If the answer is incomplete, say so directly: "
        "'That's missing the key constraint — try again.' Maintain a high bar. No encouragement "
        "for partial answers. Ask follow-ups that expose gaps."
    ),
    "faang_style": (
        "\nCommunication style: FAANG-style loop format. Ask one question, probe with 'Why?', "
        "'What are the trade-offs?', 'Can you do better?'. Focus on correctness, scalability, "
        "and communication. Signal when moving to next topic with 'Let's go to the next area.'"
    ),
    "supportive": (
        "\nCommunication style: collaborative and encouraging. Acknowledge correct parts before "
        "probing gaps. Use phrases like 'Good start — can you extend that to cover...'. "
        "Give gentle hints when the candidate is stuck for > 60 seconds."
    ),
    "pressure_test": (
        "\nCommunication style: high-pressure. Interrupt with 'Actually — we only have 5 minutes.' "
        "Push back on correct answers with 'Are you sure? I've seen this fail in production.' "
        "This tests composure, not correctness — the rubric still scores correctness fairly."
    ),
}

_PERSONALITY_DESCRIPTIONS: dict[str, str] = {
    "neutral": "Balanced, professional interviewer. No special style pressure.",
    "technical": "Deep technical probe. Expects implementation-level depth on every answer.",
    "strict": "High-bar evaluator. Explicitly calls out incomplete answers. No partial credit framing.",
    "faang_style": "FAANG loop format: structured probing, trade-off focus, explicit topic transitions.",
    "supportive": "Collaborative style with hints after 60s. Good for early practice.",
    "pressure_test": "Simulates composure testing. Pushes back even on correct answers.",
}


def get_personality_system_prompt_addition(personality: PersonalityType) -> str:
    """Returns the system prompt addition for this personality. Empty string for neutral."""
    return _PERSONALITY_SYSTEM_ADDITIONS.get(personality, "")


def get_personality_description(personality: PersonalityType) -> str:
    return _PERSONALITY_DESCRIPTIONS.get(personality, "")


def get_available_personalities() -> list[dict]:
    return [
        {"personality": p, "description": d}
        for p, d in _PERSONALITY_DESCRIPTIONS.items()
    ]
