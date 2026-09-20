import pytest
import pytest_asyncio
import asyncio
import uuid
import json
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from unittest.mock import AsyncMock, MagicMock

from backend.app.db.models import Base
from realtime_agent.app.session.orchestrator import SessionOrchestrator
from realtime_agent.app.session.manager import SessionManager
from realtime_agent.app.session.state_machine import SessionState
from realtime_agent.app.interview.policy import InterviewSession
from realtime_agent.app.scoring.models import AnswerScore
from realtime_agent.app.scoring.claims import SessionClaim
from realtime_agent.app.interview.debrief import SessionDebrief, HeadlineMetrics
from praxis_ai_gateway.router import GatewayRouter, RoutingContext

from httpx import AsyncClient, ASGITransport
from backend.app.main import app
from backend.app.dependencies import get_db_session
from backend.app.api.auth import get_current_candidate

@pytest.fixture
def patch_gateway(monkeypatch):
    async def mock_route(alias, ctx, mode, messages, schema, **kw):
        # We simulate the LLM returning a proper debrief
        return MagicMock(result=SessionDebrief(
            headline_metrics=HeadlineMetrics(average_wpm=120.0, average_filler_rate=0.5, average_score=0.9),
            strengths=["Strong problem-solving.", "Good use of Python."],
            weaknesses=["A bit brief on the design."],
            flagged_claims=["I invented Python."],
            jd_coverage={"covered": ["Algorithms"], "missed": ["System Design"]}
        ))
    monkeypatch.setattr("praxis_ai_gateway.router.GatewayRouter.route", mock_route)

@pytest_asyncio.fixture
async def test_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    
    async with async_session() as session:
        yield session
        
    await engine.dispose()

@pytest.mark.asyncio
async def test_end_session_and_debrief(patch_gateway, test_db):
    session_id = str(uuid.uuid4())
    candidate_id = str(uuid.uuid4())
    
    # 1. Seed the Database
    # Insert candidate for FKs (if needed, though sqlite might not enforce FKs by default, but it's safe)
    # We will just insert directly
    query = text("INSERT INTO candidate_profiles (id, user_id, name) VALUES (:cid, :uid, 'Test User')")
    await test_db.execute(query, {"cid": candidate_id, "uid": str(uuid.uuid4())})

    query = text("INSERT INTO practice_sessions (id, candidate_id) VALUES (:id, :cid)")
    await test_db.execute(query, {"id": session_id, "cid": candidate_id})
    
    turn_id = str(uuid.uuid4())
    query = text("INSERT INTO session_turns (id, session_id, turn_index, speaker, text_content) VALUES (:id, :sid, 1, 'candidate', 'I used Python')")
    await test_db.execute(query, {"id": turn_id, "sid": session_id})
    
    query = text("INSERT INTO turn_scores (id, turn_id, overall, rationale) VALUES (:id, :tid, 0.9, 'Good')")
    await test_db.execute(query, {"id": str(uuid.uuid4()), "tid": turn_id})
    
    query = text("INSERT INTO session_claims (id, session_id, turn_id, claim_text, supported) VALUES (:id, :sid, :tid, 'I used Python', true)")
    await test_db.execute(query, {"id": str(uuid.uuid4()), "sid": session_id, "tid": turn_id})
    
    await test_db.commit()

    # 2. Setup Orchestrator
    mock_sm = MagicMock(spec=SessionManager)
    mock_sm.session_id = session_id
    mock_sm.db = test_db
    mock_sm.transition = AsyncMock()
    
    mock_gateway = MagicMock(spec=GatewayRouter)
    mock_gateway.route = AsyncMock(return_value=MagicMock(result=SessionDebrief(
        headline_metrics=HeadlineMetrics(average_wpm=120.0, average_filler_rate=0.5, average_score=0.9),
        strengths=["Strong problem-solving.", "Good use of Python."],
        weaknesses=["A bit brief on the design."],
        flagged_claims=["I invented Python."],
        jd_coverage={"covered": ["Algorithms"], "missed": ["System Design"]}
    )))

    orchestrator = SessionOrchestrator(
        session=MagicMock(spec=InterviewSession),
        generation_manager=MagicMock(),
        session_manager=mock_sm,
        gateway=mock_gateway,
        routing_ctx=MagicMock(spec=RoutingContext),
        tts=MagicMock(),
        enqueue_event=MagicMock()
    )
    
    # 3. Call method
    await orchestrator.end_session_and_debrief()
    
    # 4. Assert transitions
    mock_sm.transition.assert_any_call(SessionState.DEBRIEF)
    mock_sm.transition.assert_any_call(SessionState.STOPPED)
    
    # 5. Check DB persistence (test-database row evidence)
    res = await test_db.execute(text("SELECT * FROM session_debriefs WHERE session_id = :sid"), {"sid": session_id})
    row = res.fetchone()
    assert row is not None, "session_debriefs row was not created!"
    
    row_dict = dict(row._mapping)
    print("\n[DB Evidence] session_debriefs row created:")
    for k, v in row_dict.items():
        print(f"  {k}: {v}")
        
    assert "Strong problem-solving." in json.dumps(row_dict["strengths"])
    
    # 6. Test the API endpoint
    
    # Override dependencies
    async def override_get_db():
        yield test_db
        
    def override_candidate():
        return {"id": candidate_id}
        
    app.dependency_overrides[get_db_session] = override_get_db
    app.dependency_overrides[get_current_candidate] = override_candidate
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/v1/sessions/{session_id}/debrief")
        
    assert response.status_code == 200
    api_body = response.json()
    
    print("\n[API Evidence] GET /api/v1/sessions/{id}/debrief response:")
    print(json.dumps(api_body, indent=2))
    
    assert "strengths" in api_body
    assert "Strong problem-solving." in api_body["strengths"]
    assert "A bit brief on the design." in api_body["weaknesses"]
    assert "0.9" in str(api_body["headline_metrics"])
