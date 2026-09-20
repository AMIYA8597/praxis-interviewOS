from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from backend.app.dependencies import get_current_candidate, get_db_session

router = APIRouter(tags=["analytics"])

@router.get("/analytics/dashboard")
async def get_dashboard(
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session)
):
    query = text("""
        SELECT 
            COUNT(DISTINCT st.session_id) as total_sessions,
            AVG(CAST(st.metrics->>'wpm' AS FLOAT)) as average_wpm,
            AVG(CAST(st.metrics->>'filler_rate' AS FLOAT)) as average_filler_rate,
            AVG(st.score) as average_score
        FROM session_turns st
        JOIN practice_sessions ps ON st.session_id = ps.id
        WHERE ps.candidate_id = :cid AND st.role = 'candidate'
    """)
    res = await db.execute(query, {"cid": candidate["id"]})
    row = res.fetchone()
    
    return {
        "interviews_completed": row.total_sessions or 0,
        "average_pace_wpm": round(row.average_wpm or 0, 1),
        "filler_word_density": round((row.average_filler_rate or 0) * 100, 1),
        "average_score": round(row.average_score or 0, 1),
        "star_consistency": 68.0 # Mocked for now since schema doesn't fully support STAR breakdown yet
    }

@router.get("/analytics/reports")
async def get_reports(
    candidate: dict = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db_session)
):
    # Could fetch historical sessions over time
    return {"reports": []}
