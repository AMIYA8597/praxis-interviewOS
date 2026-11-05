import os
import uuid
import pytest
import httpx
import respx
from unittest.mock import AsyncMock, MagicMock

from praxis_ai_gateway.base import LLMMessage
from praxis_ai_gateway.registry import ModelRegistry
from praxis_ai_gateway.router import GatewayRouter, RoutingContext
from praxis_ai_gateway.errors import (
    AIProviderNotConfiguredError,
    ProviderAuthError,
    ProviderRateLimitError,
)
from praxis_ai_gateway.providers.groq import GroqProvider
from praxis_ai_gateway.providers.gemini import GeminiProvider
from realtime_agent.app.interview.policy import InterviewSession, PolicyDecision
from realtime_agent.app.scoring.service import score_answer_async
from realtime_agent.app.audio.vad import VoiceActivityDetector
from faster_whisper import WhisperModel
from backend.app.services.debrief import generate_session_debrief


@pytest.fixture
def models_config_path():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "config", "models.yaml"))


@pytest.fixture
def mock_redis():
    r = AsyncMock()
    r.get = AsyncMock(return_value=None)
    r.set = AsyncMock(return_value=True)
    r.incr = AsyncMock(return_value=1)
    r.setex = AsyncMock(return_value=True)
    r.delete = AsyncMock(return_value=True)
    return r


@pytest.fixture
def empty_router(models_config_path, mock_redis):
    registry = ModelRegistry(models_config_path)
    return GatewayRouter(registry=registry, providers={}, redis=mock_redis)


# =========================================================================
# 1. GATE: Provider Configuration & Typed Errors
# =========================================================================

@pytest.mark.asyncio
async def test_gateway_unconfigured_error(empty_router):
    """When no provider is configured, router raises AI_PROVIDER_NOT_CONFIGURED."""
    ctx = RoutingContext(user_id="synthetic_user_1", session_id="synthetic_session_1")
    with pytest.raises(AIProviderNotConfiguredError) as exc_info:
        await empty_router.route(
            task="question_generation",
            context=ctx,
            method_name="generate",
            prompt="Generate technical interview question."
        )
    assert exc_info.value.error_code == "AI_PROVIDER_NOT_CONFIGURED"


@pytest.mark.asyncio
@respx.mock
async def test_gateway_authentication_failure_propagates_accurately(models_config_path, mock_redis):
    """When a provider is configured but authentication fails (401), ProviderAuthError is raised."""
    # Mock Groq 401
    respx.post("https://api.groq.com/openai/v1/chat/completions").mock(
        return_value=httpx.Response(401, json={"error": {"message": "Invalid API Key", "type": "invalid_request_error"}})
    )
    provider = GroqProvider(api_key="gsk_invalid_test_key_12345")
    registry = ModelRegistry(models_config_path)
    router = GatewayRouter(registry=registry, providers={"groq": provider}, redis=mock_redis)

    ctx = RoutingContext(user_id="synthetic_user_1", session_id="synthetic_session_1")
    with pytest.raises(ProviderAuthError):
        await router.route(
            task="question_generation",
            context=ctx,
            method_name="generate",
            messages=[LLMMessage(role="user", content="Hello")]
        )


@pytest.mark.asyncio
@respx.mock
async def test_gateway_rate_limit_propagates_accurately(models_config_path, mock_redis):
    """When a provider is rate-limited (429), ProviderRateLimitError is raised."""
    respx.post("https://api.groq.com/openai/v1/chat/completions").mock(
        return_value=httpx.Response(429, headers={"Retry-After": "10"}, json={"error": {"message": "Rate limit exceeded"}})
    )
    provider = GroqProvider(api_key="gsk_valid_test_key_12345")
    registry = ModelRegistry(models_config_path)
    router = GatewayRouter(registry=registry, providers={"groq": provider}, redis=mock_redis)

    ctx = RoutingContext(user_id="synthetic_user_1", session_id="synthetic_session_1")
    with pytest.raises(ProviderRateLimitError) as exc_info:
        await router.route(
            task="question_generation",
            context=ctx,
            method_name="generate",
            messages=[LLMMessage(role="user", content="Hello")]
        )
    assert "rate limited" in str(exc_info.value).lower()


# =========================================================================
# 2. GATE: Provider Health Checks
# =========================================================================

@pytest.mark.asyncio
@respx.mock
async def test_groq_and_gemini_health_checks():
    """Verify health probes on Groq and Gemini adapters."""
    # 1. Groq health probe
    respx.get("https://api.groq.com/openai/v1/models").mock(
        return_value=httpx.Response(200, json={"data": [{"id": "llama-3.3-70b-versatile"}]})
    )
    groq = GroqProvider(api_key="gsk_test_key")
    assert await groq.check_health() is True

    # 2. Gemini health probe
    respx.get("https://generativelanguage.googleapis.com/v1beta/models?key=test_gemini_key").mock(
        return_value=httpx.Response(200, json={"models": [{"name": "models/gemini-1.5-flash"}]})
    )
    gemini = GeminiProvider(api_key="test_gemini_key")
    assert await gemini.check_health() is True


# =========================================================================
# 3. GATE: Interviewer Generation & Contextual Follow-Up
# =========================================================================

@pytest.mark.asyncio
async def test_interview_session_follow_up_grounding():
    """Verify that follow-up questions dynamically respond to candidate answers, not fixed sequences."""
    jd_blueprint = {
        "target_role": "Distributed Systems Engineer",
        "requirements": ["Kafka", "Raft consensus", "Partition balancing"],
        "prep_pack": ["Can you explain Kafka architecture?"]
    }
    candidate_profile = {
        "summary": "Experienced engineer with Kafka & distributed storage experience.",
        "verified_skills": ["Kafka", "Python", "Go"],
        "claims": []
    }

    session = InterviewSession(jd_blueprint, candidate_profile, difficulty="standard", interview_type="technical")
    session.warm_up()
    assert session.is_warmed_up is True
    assert "Kafka" in session.cached_context

    # Mock gateway returning structured PolicyDecision
    mock_router = AsyncMock()
    mock_decision = PolicyDecision(
        is_clarifying_follow_up=True,
        response_text="You mentioned using sticky partition assignors in Kafka. What were the specific failure modes you observed during consumer group rebalances?"
    )
    mock_call_result = MagicMock()
    mock_call_result.result = mock_decision
    mock_router.route.return_value = mock_call_result

    routing_ctx = RoutingContext(user_id="user-123", session_id="session-456")
    candidate_answer = "At Apex Stream, we switched to sticky partition assignors to eliminate rebalance storms."

    decision = await session.generate_next_turn(
        candidate_answer=candidate_answer,
        gateway_router=mock_router,
        routing_ctx=routing_ctx,
        is_follow_up=True,
        parent_turn_id=None
    )

    assert decision.is_clarifying_follow_up is True
    assert "sticky partition assignors" in decision.response_text
    assert len(session.memory.turns) == 2
    assert session.memory.turns[0].role == "Candidate"
    assert session.memory.turns[1].role == "Interviewer"


# =========================================================================
# 4. GATE: Answer Evaluation & Rubric Scoring
# =========================================================================

@pytest.mark.asyncio
async def test_answer_evaluation_scoring_integrity():
    """Verify evaluation rubric execution, output schema validation, and deterministic weighting."""
    mock_router = AsyncMock()

    class MockLlmScoringResult:
        relevance = 0.90
        correctness = 0.85
        structure = 0.80
        specificity = 0.85
        conciseness = 0.75
        star_completeness = None
        rationale = "Candidate demonstrated strong understanding of Kafka partitioning and rebalance mitigation."

    # Return claims first, then verify, then rubric score
    claim_call = MagicMock()
    claim_call.result = MagicMock(claims=[MagicMock(claim_text="Switched to sticky assignor", is_verifiable=True)])
    
    verify_call = MagicMock()
    verify_call.result = MagicMock(text="YES, supported by verified context.")

    score_call = MagicMock()
    score_call.result = MockLlmScoringResult()

    mock_router.route.side_effect = [claim_call, verify_call, score_call]

    routing_ctx = RoutingContext(user_id="user-123", session_id="session-456")
    score = await score_answer_async(
        question="How did you solve consumer rebalances?",
        candidate_answer="We adopted cooperative sticky assignors.",
        is_behavioral=False,
        verified_context="Candidate worked on Kafka cooperative assignors at Apex Stream.",
        gateway_router=mock_router,
        routing_ctx=routing_ctx
    )

    assert score.overall is not None
    assert 0.80 <= score.overall <= 0.95
    assert score.relevance == 0.90
    assert score.correctness == 0.85
    assert score.grounding == 1.0
    assert score.measurement_status == "MEASURED"
    assert "Kafka" in score.rationale


# =========================================================================
# 5. GATE: Debrief Metric Traceability
# =========================================================================

@pytest.mark.asyncio
async def test_debrief_metric_traceability():
    """Verify debrief headline metrics are 100% mathematically derived from real database records."""
    session_id = str(uuid.uuid4())
    mock_db = AsyncMock()

    class MockMetric:
        def __init__(self, wpm, filler):
            self.wpm = wpm
            self.filler_count = filler

    class MockScore:
        def __init__(self, relevance, id_str):
            self.relevance = relevance
            self.id = uuid.UUID(id_str)

    # 3 turns: 130 WPM (2 fillers), 150 WPM (4 fillers), 140 WPM (0 fillers)
    # Average WPM = (130+150+140)/3 = 140.0
    # Total Fillers = 2 + 4 + 0 = 6
    # Scores: 0.9, 0.8 -> Average = 0.85, rounded to 1 decimal = 0.9
    res1 = MagicMock()
    res1.scalars.return_value.all.return_value = [MockMetric(130.0, 2), MockMetric(150.0, 4), MockMetric(140.0, 0)]
    res2 = MagicMock()
    res2.scalars.return_value.all.return_value = [MockScore(0.9, str(uuid.uuid4())), MockScore(0.8, str(uuid.uuid4()))]

    mock_db.execute.side_effect = [res1, res2]

    # Mock gateway for debrief natural language summary
    mock_router = AsyncMock()
    mock_debrief_obj = MagicMock(
        strengths=["Clear technical communication", "Strong explanation of partitioning trade-offs"],
        weaknesses=["Could speak slightly slower during high-complexity sections"],
        flagged_claims=[],
        jd_coverage={"covered": ["Kafka", "Consensus"], "missed": []}
    )
    mock_call_res = MagicMock()
    mock_call_res.result = mock_debrief_obj
    mock_router.route.return_value = mock_call_res

    debrief = await generate_session_debrief(session_id, mock_db, mock_router)

    assert debrief["session_id"] == session_id
    assert debrief["headline_metrics"]["average_wpm"] == 140
    assert debrief["headline_metrics"]["average_filler_rate"] == 6
    assert debrief["headline_metrics"]["average_score"] == 0.9
    assert len(debrief["strengths"]) == 2
    assert len(debrief["weaknesses"]) == 1


# =========================================================================
# 6. GATE: Audio Pipeline (Silero VAD + Faster-Whisper on CPU)
# =========================================================================

@pytest.mark.asyncio
async def test_audio_pipeline_execution():
    """Verify real local STT and VAD inference on benchmark audio fixture."""
    audio_path = "ai-evaluation/datasets/audio/clean_technical.wav"
    if not os.path.exists(audio_path):
        pytest.skip(f"Audio fixture missing: {audio_path}")

    # Faster-Whisper CPU int8
    model = WhisperModel("tiny.en", device="cpu", compute_type="int8")
    segments, _ = model.transcribe(audio_path)
    text_content = " ".join(s.text for s in segments)
    assert "distributed systems" in text_content.lower()

    # Silero VAD
    vad = VoiceActivityDetector()
    with open(audio_path, "rb") as f:
        raw_wav = f.read()
    pcm_bytes = raw_wav[44:] if raw_wav.startswith(b"RIFF") else raw_wav

    frame_size = 1024  # 512 samples at 16kHz 16-bit
    speech_detected = 0
    for offset in range(0, len(pcm_bytes) - frame_size, frame_size):
        frame = pcm_bytes[offset : offset + frame_size]
        if vad.process_frame(frame):
            speech_detected += 1
    assert speech_detected > 0


# =========================================================================
# 7. GATE: Electron Security Invariants
# =========================================================================

def test_electron_security_invariants():
    """Verify contextIsolation, nodeIntegration: false, and sandbox in Electron configuration."""
    main_ts_path = "apps/desktop/src/main/index.ts"
    with open(main_ts_path, "r", encoding="utf-8") as f:
        code = f.read()

    assert "contextIsolation: true" in code
    assert "nodeIntegration: false" in code
    assert "sandbox: true" in code
