import pytest
import asyncio
import uuid
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

import pytest_asyncio

# We will patch the scoring functions to return deterministic results
@pytest.fixture
def patch_scoring(monkeypatch):
    async def mock_score_answer(*args, **kwargs):
        return AnswerScore(
            relevance=0.8,
            correctness=0.9,
            structure=0.7,
            grounding=1.0,
            specificity=0.8,
            conciseness=0.9,
            star_completeness={"situation": True, "task": True, "action": True, "result": True},
            overall=0.85,
            rationale="Deterministic mock rationale",
            rubric_version="v1"
        )
        
    async def mock_process_claims(answer_text, question_context, session_id, turn_id, candidate_id, gateway_router, routing_ctx):
        claim = SessionClaim(
            session_id=session_id,
            claim_text="I used Python extensively.",
            supported=True,
            source_chunk_id=None,
            source_project_id=None,
            source_excerpt=None,
            contradiction_of_claim_id=None
        )
        # Simulate the DB insert that process_candidate_answer_claims normally does
        query = text("""
            INSERT INTO session_claims (id, session_id, turn_id, claim_text, supported)
            VALUES (:id, :session_id, :turn_id, :claim_text, :supported)
        """)
        await gateway_router.db.execute(query, {
            "id": str(uuid.uuid4()),
            "session_id": session_id,
            "turn_id": turn_id,
            "claim_text": claim.claim_text,
            "supported": claim.supported
        })
        await gateway_router.db.commit()
        return [claim]
        
    monkeypatch.setattr("realtime_agent.app.session.orchestrator.score_answer_async", mock_score_answer)
    monkeypatch.setattr("realtime_agent.app.session.orchestrator.process_candidate_answer_claims", mock_process_claims)

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
async def test_on_candidate_turn_end(patch_scoring, test_db):
    # 1. Setup Session Manager with real db
    session_id = str(uuid.uuid4())
    candidate_id = str(uuid.uuid4())
    
    # We must first create the InterviewSession in DB because of foreign keys
    query = text("INSERT INTO practice_sessions (id, candidate_id) VALUES (:id, :cid)")
    await test_db.execute(query, {"id": session_id, "cid": candidate_id})
    await test_db.commit()
    
    mock_sm = MagicMock(spec=SessionManager)
    mock_sm.session_id = session_id
    mock_sm.db = test_db
    mock_sm.transition = AsyncMock()

    # 2. Setup InterviewSession
    mock_policy = MagicMock(spec=InterviewSession)
    mock_policy.candidate_profile = {"id": candidate_id}
    # Pretend there are remaining prep pack items
    mock_policy.current_question_idx = 0
    mock_policy.prep_pack = ["Question 1", "Question 2"]
    
    mock_memory = MagicMock()
    mock_memory.turns = []
    mock_memory.turn_count_threshold = 6
    mock_memory.compress = AsyncMock()
    mock_policy.memory = mock_memory

    # 3. Setup Gateway
    mock_gateway = MagicMock()
    # Mocking db on gateway for claims internal
    mock_gateway.db = test_db 

    # 4. Instantiate Orchestrator
    orchestrator = SessionOrchestrator(
        session=mock_policy,
        generation_manager=MagicMock(),
        session_manager=mock_sm,
        gateway=mock_gateway,
        routing_ctx=MagicMock(),
        tts=MagicMock(),
        enqueue_event=MagicMock()
    )
    orchestrator.last_interviewer_question = "What is Python?"
    orchestrator.begin_interviewer_turn = AsyncMock()
    orchestrator.end_session_and_debrief = AsyncMock()
    
    # 5. Execute Method
    await orchestrator.on_candidate_turn_end(final_text="I used Python extensively.")
    
    # 6. Assertions
    # Transitions
    mock_sm.transition.assert_any_call(SessionState.TURN_END)
    mock_sm.transition.assert_any_call(SessionState.SCORING)
    mock_sm.transition.assert_any_call(SessionState.PLANNING_NEXT)
    mock_sm.transition.assert_any_call(SessionState.READY)
    
    # Next step branch
    orchestrator.begin_interviewer_turn.assert_called_once()
    orchestrator.end_session_and_debrief.assert_not_called()
    
    # Check DB persistence
    turn_res = await test_db.execute(text("SELECT id, text_content FROM session_turns WHERE session_id = :sid"), {"sid": session_id})
    turn_row = turn_res.fetchone()
    assert turn_row is not None, "session_turns row was not created"
    
    turn_id = turn_row[0]
    
    score_res = await test_db.execute(text("SELECT overall, rationale FROM turn_scores WHERE turn_id = :tid"), {"tid": turn_id})
    score_row = score_res.fetchone()
    assert score_row is not None, "turn_scores row was not created"
    assert round(score_row[0], 2) == 0.85
    assert score_row[1] == "Deterministic mock rationale"
    
    # Check Claims persistence
    claims_res = await test_db.execute(text("SELECT claim_text, supported FROM session_claims WHERE turn_id = :tid"), {"tid": turn_id})
    claims_row = claims_res.fetchone()
    assert claims_row is not None, "session_claims row was not created"
    assert claims_row[0] == "I used Python extensively."
    assert claims_row[1] == True
    
    print("\nTest passed. DB row evidence:")
    print(f"session_turns: ID={turn_id}, Text={turn_row[1]}")
    print(f"turn_scores: Overall={score_row[0]}, Rationale={score_row[1]}")
    print(f"session_claims: Claim='{claims_row[0]}', Supported={claims_row[1]}")
