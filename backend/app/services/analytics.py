from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.repositories import sessions as repo


async def dashboard(db: AsyncSession, candidate_id: str) -> dict:
    stats = await repo.analytics_for_candidate(db, candidate_id)
    structure = stats["average_structure"]
    return {
        "interviews_completed": stats["completed_sessions"],
        "total_sessions": stats["total_sessions"],
        "average_pace_wpm": round(stats["average_wpm"], 1),
        # filler_rate is stored as a 0..1 fraction
        "filler_word_density": round(stats["average_filler_rate"] * 100, 1),
        "average_score": round(stats["average_score"], 2),
        # Mean rubric `structure` dimension (0..1) as a percentage; None until scored.
        "star_consistency": round(structure * 100, 1) if structure is not None else None,
    }


async def reports(db: AsyncSession, candidate_id: str, limit: int) -> dict:
    return {"reports": await repo.session_score_history(db, candidate_id, limit)}
