"""
Phase 62 — Real System Design Interview Engine.

Implements a 24-step structured flow with specific challenge questions at each phase.
The interviewer progresses through phases: requirements → clarification → high-level
design → deep-dive → scalability challenges → data modeling → API design →
failure scenarios → optimization → wrap-up.

Phase 63 (Diagram Intelligence) is integrated here: spoken reasoning is analyzed
for diagram contradictions.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Ordered phases with challenge prompt templates
SD_PHASES = [
    {
        "phase": "requirements_gathering",
        "questions": [
            "Before we start designing, what are the key functional requirements? Who are the users?",
            "What scale are we targeting — requests per second, data volume, geographic distribution?",
            "What are the non-functional requirements: latency SLAs, consistency vs availability trade-offs?",
        ],
        "challenge": "What would change in your design if the scale was 10x what you estimated?",
    },
    {
        "phase": "clarification",
        "questions": [
            "Are there any assumptions you're making that we should validate?",
            "What's out of scope for this design?",
        ],
        "challenge": "What's the most critical assumption — if it were wrong, what would break first?",
    },
    {
        "phase": "high_level_design",
        "questions": [
            "Walk me through your high-level architecture. What are the main components?",
            "How do clients interact with your system? What's the request path?",
        ],
        "challenge": "Where is the single point of failure in your current design?",
    },
    {
        "phase": "deep_dive_component",
        "questions": [
            "Let's dive deeper into [COMPONENT]. How does it work internally?",
            "What data does [COMPONENT] store and what's its access pattern?",
            "How does [COMPONENT] handle failures?",
        ],
        "challenge": "If [COMPONENT] goes down during peak traffic, what happens? Walk me through the failure mode.",
    },
    {
        "phase": "scalability_challenge",
        "questions": [
            "Your design handles the estimated scale. Now 10x traffic hits unexpectedly — what breaks first?",
            "How do you scale the database layer?",
        ],
        "challenge": "What's your partitioning strategy? How do you handle hot partitions?",
    },
    {
        "phase": "data_modeling",
        "questions": [
            "Walk me through your data model. What are the primary entities and their relationships?",
            "Why did you choose this data store? What trade-offs did you consider?",
            "How do you handle data consistency across services?",
        ],
        "challenge": "How would this model change if you needed to support multi-tenancy?",
    },
    {
        "phase": "api_design",
        "questions": [
            "Walk me through the key API endpoints. What request/response schemas?",
            "How do you handle authentication and authorization?",
            "How do you version your API?",
        ],
        "challenge": "A client sends malformed data — how does your API respond? What's your validation strategy?",
    },
    {
        "phase": "failure_scenarios",
        "questions": [
            "The message queue fills up — what happens?",
            "Network partition between services — how does your system behave?",
            "Database primary goes down — what's your recovery path?",
        ],
        "challenge": "How long does it take for your system to fully recover from a database failover?",
    },
    {
        "phase": "optimization",
        "questions": [
            "What would you optimize first if you had 2 weeks?",
            "Where are the bottlenecks in your read path? Write path?",
        ],
        "challenge": "If p99 latency suddenly doubles, what's your debugging process?",
    },
    {
        "phase": "wrap_up",
        "questions": [
            "Looking back, what's the weakest part of your design?",
            "What would you do differently if you had 3 months to build this?",
        ],
        "challenge": None,
    },
]

_PHASE_ORDER = [p["phase"] for p in SD_PHASES]


def _get_phase_config(phase: str) -> Optional[dict]:
    for p in SD_PHASES:
        if p["phase"] == phase:
            return p
    return None


def _next_phase(current_phase: str) -> Optional[str]:
    idx = _PHASE_ORDER.index(current_phase) if current_phase in _PHASE_ORDER else -1
    if idx >= 0 and idx < len(_PHASE_ORDER) - 1:
        return _PHASE_ORDER[idx + 1]
    return None


async def get_or_create_sd_state(db: AsyncSession, session_id: str) -> dict:
    row = await db.execute(text("""
        SELECT current_phase, phases_completed, challenge_count
        FROM system_design_session_state WHERE session_id = :sid
    """), {"sid": session_id})
    existing = row.fetchone()

    if not existing:
        await db.execute(text("""
            INSERT INTO system_design_session_state (session_id)
            VALUES (:sid)
        """), {"sid": session_id})
        await db.commit()
        return {
            "session_id": session_id,
            "current_phase": "requirements_gathering",
            "phases_completed": [],
            "challenge_count": 0,
        }

    return {
        "session_id": session_id,
        "current_phase": existing[0],
        "phases_completed": list(existing[1] or []),
        "challenge_count": existing[2],
    }


async def advance_sd_phase(db: AsyncSession, session_id: str) -> dict:
    state = await get_or_create_sd_state(db, session_id)
    current = state["current_phase"]
    completed = state["phases_completed"]

    if current not in completed:
        completed.append(current)

    next_phase = _next_phase(current)
    if not next_phase:
        next_phase = current  # already at wrap_up

    now = datetime.now(timezone.utc)
    await db.execute(text("""
        UPDATE system_design_session_state
        SET current_phase = :phase, phases_completed = :completed, last_updated_at = :now
        WHERE session_id = :sid
    """), {
        "phase": next_phase,
        "completed": completed,
        "now": now,
        "sid": session_id,
    })
    await db.commit()

    phase_config = _get_phase_config(next_phase)
    return {
        "session_id": session_id,
        "current_phase": next_phase,
        "phases_completed": completed,
        "suggested_questions": phase_config["questions"] if phase_config else [],
        "challenge_prompt": phase_config["challenge"] if phase_config else None,
    }


def analyze_diagram_contradictions(
    spoken_reasoning: str,
    diagram_components: list[str],
) -> list[dict]:
    """
    Phase 63 — Diagram Intelligence (rule-based).

    Checks if the candidate's spoken reasoning mentions components that contradict
    or are absent from the stated diagram components.

    Returns list of potential contradictions with their evidence.
    Real contradiction detection requires LLM; this provides the signal structure.
    """
    contradictions = []
    spoken_lower = spoken_reasoning.lower()

    for component in diagram_components:
        comp_lower = component.lower()
        if comp_lower not in spoken_lower:
            # Component mentioned in diagram but not explained verbally
            contradictions.append({
                "type": "unexplained_component",
                "component": component,
                "evidence": f"'{component}' appears in diagram but was not mentioned in spoken explanation.",
                "severity": "low",
            })

    # Check for contradictions: candidate says "no caching" but diagram has Redis
    cache_keywords = ["redis", "memcached", "cache", "caching"]
    no_cache_keywords = ["no cache", "no caching", "without cache", "no redis"]

    for nkw in no_cache_keywords:
        if nkw in spoken_lower:
            for ckw in cache_keywords:
                if any(ckw in c.lower() for c in diagram_components):
                    contradictions.append({
                        "type": "verbal_diagram_contradiction",
                        "component": ckw,
                        "evidence": f"Candidate said '{nkw}' but diagram includes a caching component.",
                        "severity": "high",
                    })

    return contradictions
