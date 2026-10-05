"""
Phase 60 — Adaptive Interview Difficulty.

Difficulty is adjusted algorithmically from real answer signals:
- correctness score from turn_scores
- depth (specificity + structure as proxy)
- latency (answer length as proxy — not response time, which isn't tracked)

This is NOT a static setting — it tracks performance within the session and
adjusts the next question's difficulty level accordingly.

Algorithm: variant of performance-based IRT difficulty adjustment.
  - correct + deep → increase difficulty by STEP_UP
  - correct + shallow → maintain
  - incorrect → decrease by STEP_DOWN (floor = MIN_LEVEL)
  Two consecutive correct-deep → larger jump (DOUBLE_STEP_UP)
"""
import logging
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

MIN_LEVEL = 0.10
MAX_LEVEL = 0.95
STEP_UP = 0.08
STEP_DOWN = 0.12
DOUBLE_STEP_UP = 0.15
DEPTH_THRESHOLD = 0.65  # specificity + structure avg must exceed to count as "deep"


def _next_difficulty(
    current: float,
    correctness: float,
    depth: float,
    correct_streak: int,
    incorrect_streak: int,
) -> tuple[float, int, int]:
    """
    Returns (new_level, new_correct_streak, new_incorrect_streak).
    """
    is_correct = correctness >= 0.60
    is_deep = depth >= DEPTH_THRESHOLD

    if is_correct and is_deep:
        new_streak = correct_streak + 1
        step = DOUBLE_STEP_UP if new_streak >= 2 else STEP_UP
        new_level = min(MAX_LEVEL, current + step)
        return new_level, new_streak, 0
    elif is_correct:
        return current, correct_streak + 1, 0
    else:
        new_level = max(MIN_LEVEL, current - STEP_DOWN)
        return new_level, 0, incorrect_streak + 1


async def record_turn_and_adjust(
    db: AsyncSession,
    session_id: str,
    correctness: float,
    specificity: float,
    structure: float,
) -> dict:
    """
    Called after each scored turn to update adaptive difficulty state.
    Returns updated state including next question's target difficulty.
    """
    depth = (specificity + structure) / 2.0

    # Fetch current state
    row = await db.execute(text("""
        SELECT current_level, questions_asked, correct_streak, incorrect_streak
        FROM session_difficulty_state
        WHERE session_id = :sid
    """), {"sid": session_id})
    existing = row.fetchone()

    now = datetime.now(timezone.utc)

    if existing:
        current_level = float(existing[0])
        questions_asked = existing[1]
        correct_streak = existing[2]
        incorrect_streak = existing[3]
    else:
        current_level = 0.5
        questions_asked = 0
        correct_streak = 0
        incorrect_streak = 0

    new_level, new_correct_streak, new_incorrect_streak = _next_difficulty(
        current_level, correctness, depth, correct_streak, incorrect_streak
    )
    new_questions = questions_asked + 1

    if existing:
        await db.execute(text("""
            UPDATE session_difficulty_state SET
                current_level = :level,
                questions_asked = :q,
                correct_streak = :cs,
                incorrect_streak = :is,
                last_updated_at = :now
            WHERE session_id = :sid
        """), {
            "level": new_level, "q": new_questions,
            "cs": new_correct_streak, "is": new_incorrect_streak,
            "now": now, "sid": session_id,
        })
    else:
        await db.execute(text("""
            INSERT INTO session_difficulty_state
            (session_id, current_level, questions_asked, correct_streak, incorrect_streak, last_updated_at)
            VALUES (:sid, :level, :q, :cs, :is, :now)
        """), {
            "sid": session_id, "level": new_level, "q": new_questions,
            "cs": new_correct_streak, "is": new_incorrect_streak, "now": now,
        })

    await db.commit()

    return {
        "session_id": session_id,
        "previous_level": round(current_level, 3),
        "new_level": round(new_level, 3),
        "questions_asked": new_questions,
        "correct_streak": new_correct_streak,
        "incorrect_streak": new_incorrect_streak,
        "difficulty_label": _level_label(new_level),
    }


def _level_label(level: float) -> str:
    if level < 0.35:
        return "easy"
    if level < 0.55:
        return "medium"
    if level < 0.75:
        return "hard"
    return "very_hard"


async def get_session_difficulty(db: AsyncSession, session_id: str) -> dict:
    row = await db.execute(text("""
        SELECT current_level, questions_asked, correct_streak, incorrect_streak, last_updated_at
        FROM session_difficulty_state WHERE session_id = :sid
    """), {"sid": session_id})
    r = row.fetchone()
    if not r:
        return {"session_id": session_id, "current_level": 0.5, "difficulty_label": "medium", "questions_asked": 0}
    return {
        "session_id": session_id,
        "current_level": float(r[0]),
        "difficulty_label": _level_label(float(r[0])),
        "questions_asked": r[1],
        "correct_streak": r[2],
        "incorrect_streak": r[3],
        "last_updated_at": str(r[4]),
    }
