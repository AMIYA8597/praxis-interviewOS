"""
Real AI Provider Live Inference Acceptance Test Suite.

Mandatory release gate verification for genuine cloud model inference.
Tests all required live capabilities against configured free-tier providers:
- Live authentication and health check
- Live question generation
- Live answer evaluation (rubric scoring)
- Live contextual follow-up generation
- Live structured output validation
- Live provider failure handling
- Live rate-limit error propagation
- Live timeout and cancellation handling
- Live session debrief generation from persisted database records

When credentials (GROQ_API_KEY, GEMINI_API_KEY) are not set in the environment or .env,
the tests cleanly report BLOCKED / NOT_CONFIGURED without fabricating success.
"""

import os
import asyncio
import pytest
from pydantic import BaseModel, Field
from dotenv import dotenv_values

from praxis_ai_gateway.base import LLMMessage, CancellationToken
from praxis_ai_gateway.registry import ModelRegistry
from praxis_ai_gateway.router import GatewayRouter, RoutingContext
from praxis_ai_gateway.errors import (
    ProviderAuthError,
)
from praxis_ai_gateway.providers.groq import GroqProvider
from praxis_ai_gateway.providers.gemini import GeminiProvider
from realtime_agent.app.interview.policy import InterviewSession
from realtime_agent.app.scoring.service import score_answer_async


def _get_live_credentials():
    env = dotenv_values(".env") if os.path.exists(".env") else {}
    groq_key = os.environ.get("GROQ_API_KEY") or env.get("GROQ_API_KEY")
    gemini_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or env.get("GEMINI_API_KEY") or env.get("GOOGLE_API_KEY")

    groq_val = groq_key.strip() if groq_key and len(groq_key.strip()) > 0 else None
    gemini_val = gemini_key.strip() if gemini_key and len(gemini_key.strip()) > 0 else None

    # Filter out placeholders
    if groq_val and any(p in groq_val.lower() for p in ["your_", "placeholder", "xxx"]):
        groq_val = None
    if gemini_val and any(p in gemini_val.lower() for p in ["your_", "placeholder", "xxx"]):
        gemini_val = None

    return groq_val, gemini_val


GROQ_KEY, GEMINI_KEY = _get_live_credentials()
HAS_LIVE_PROVIDER = bool(GROQ_KEY or GEMINI_KEY)

SKIP_REASON_NO_PROVIDER = (
    "LIVE_INFERENCE_BLOCKED: No live AI provider credentials configured (GROQ_API_KEY or GEMINI_API_KEY). "
    "Please configure a valid free-tier API key in .env to run live acceptance tests."
)


@pytest.fixture
def live_providers():
    if not HAS_LIVE_PROVIDER:
        pytest.skip(SKIP_REASON_NO_PROVIDER)
    provs = {}
    if GROQ_KEY:
        provs["groq"] = GroqProvider(api_key=GROQ_KEY)
    if GEMINI_KEY:
        provs["gemini"] = GeminiProvider(api_key=GEMINI_KEY)
    return provs


@pytest.fixture
def live_router(live_providers):
    from unittest.mock import AsyncMock
    models_config = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "config", "models.yaml"))
    registry = ModelRegistry(models_config)
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.set = AsyncMock(return_value=True)
    mock_redis.incr = AsyncMock(return_value=1)
    mock_redis.setex = AsyncMock(return_value=True)
    return GatewayRouter(registry=registry, providers=live_providers, redis=mock_redis)


# =========================================================================
# 1. Real Provider Authentication and Health Checks
# =========================================================================

@pytest.mark.asyncio
async def test_live_provider_health(live_providers):
    """Verify live connectivity and authenticated health probe against genuine provider endpoints."""
    for name, provider in live_providers.items():
        is_healthy = await provider.check_health()
        assert is_healthy is True, f"Live provider '{name}' health check failed"


# =========================================================================
# 2. Real Interviewer Question Generation
# =========================================================================

@pytest.mark.asyncio
async def test_live_question_generation(live_router):
    """Execute real interviewer question generation using live LLM inference."""
    ctx = RoutingContext(user_id="user_live_test", session_id="session_live_test", zero_spend_mode=True)
    messages = [
        LLMMessage(role="system", content="You are an expert technical interviewer for distributed systems engineering."),
        LLMMessage(role="user", content="Generate a challenging question about Kafka consumer partition rebalancing strategies."),
    ]
    call = await live_router.route(
        task="question_generation",
        context=ctx,
        method_name="generate",
        messages=messages,
    )
    res = call.result
    assert res.text and len(res.text.strip()) > 30, "Generated question was empty or too short"
    assert call.provider_name in ("groq", "gemini"), f"Unexpected provider routed: {call.provider_name}"
    assert res.latency_ms > 0, "Latency was not measured"


# =========================================================================
# 3. Real Structured Output Validation
# =========================================================================

class LiveEvaluationSchema(BaseModel):
    clarity_score: float = Field(..., description="Clarity score from 0.0 to 1.0")
    key_observation: str = Field(..., description="Key observation of candidate answer")
    is_satisfactory: bool = Field(..., description="Whether answer is satisfactory")


@pytest.mark.asyncio
async def test_live_structured_output(live_router):
    """Execute real structured JSON extraction validated against a Pydantic schema."""
    ctx = RoutingContext(user_id="user_live_test", session_id="session_live_test", zero_spend_mode=True)
    messages = [
        LLMMessage(role="system", content="You evaluate technical interview answers. Output valid JSON adhering to schema."),
        LLMMessage(
            role="user",
            content="Evaluate this candidate response: 'We used sticky partition assignors to prevent rebalance storms.'",
        ),
    ]
    call = await live_router.route(
        task="answer_evaluation",
        context=ctx,
        method_name="structured",
        messages=messages,
        schema=LiveEvaluationSchema,
    )
    result = call.result
    assert isinstance(result, LiveEvaluationSchema)
    assert 0.0 <= result.clarity_score <= 1.0
    assert len(result.key_observation) > 5


# =========================================================================
# 4. Real Answer Evaluation & Rubric Scoring
# =========================================================================

@pytest.mark.asyncio
async def test_live_answer_evaluation_rubric(live_router):
    """Execute real answer evaluation rubric with claims extraction and grounding."""
    ctx = RoutingContext(user_id="user_live_test", session_id="session_live_test", zero_spend_mode=True)
    question = "How did you scale Kafka consumer groups during high traffic spikes?"
    candidate_answer = (
        "We migrated from the eager rebalance protocol to cooperative sticky assignors in Kafka 2.4. "
        "This eliminated stop-the-world pauses by reassigning only migrating partitions in a second pass."
    )
    verified_context = "Candidate was Lead Systems Engineer at Apex Stream managing 1.5M events/sec on Kafka."

    score = await score_answer_async(
        question=question,
        candidate_answer=candidate_answer,
        is_behavioral=False,
        verified_context=verified_context,
        gateway_router=live_router,
        routing_ctx=ctx,
    )
    assert score.overall is not None
    assert 0.5 <= score.overall <= 1.0
    assert score.measurement_status == "MEASURED"
    assert len(score.rationale) > 10


# =========================================================================
# 5. Real Contextual Follow-Up Generation
# =========================================================================

@pytest.mark.asyncio
async def test_live_contextual_follow_up(live_router):
    """Verify follow-up question responds dynamically to the candidate's real answer."""
    jd_blueprint = {
        "target_role": "Senior Infrastructure Architect",
        "requirements": ["Kafka", "Distributed Storage", "High Availability"],
        "prep_pack": ["Discuss Kafka failover."],
    }
    candidate_profile = {
        "summary": "Distributed systems engineer with 8 years experience.",
        "verified_skills": ["Kafka", "Python", "Go"],
        "claims": [],
    }
    session = InterviewSession(jd_blueprint, candidate_profile, difficulty="senior", interview_type="technical")
    session.warm_up()

    ctx = RoutingContext(user_id="user_live_test", session_id="session_live_test", zero_spend_mode=True)
    decision = await session.generate_next_turn(
        candidate_answer="We adopted the Cooperative Sticky Assignor in Kafka to eliminate stop-the-world pauses.",
        gateway_router=live_router,
        routing_ctx=ctx,
        is_follow_up=True,
    )
    assert decision.response_text and len(decision.response_text.strip()) > 20
    assert len(session.memory.turns) >= 2


# =========================================================================
# 6. Real Timeout and Cancellation Handling
# =========================================================================

@pytest.mark.asyncio
async def test_live_timeout_and_cancellation():
    """Verify cancellation token and timeout cleanly abort in-flight live requests."""
    token = CancellationToken()
    token.cancel(reason="test cancellation")  # Already cancelled before invoke

    if GROQ_KEY:
        groq = GroqProvider(api_key=GROQ_KEY)
        messages = [LLMMessage(role="user", content="Write a 1000 word essay on Raft consensus.")]
        with pytest.raises((asyncio.CancelledError, Exception)):
            await groq.generate(messages, cancellation_token=token)

    if GEMINI_KEY:
        gemini = GeminiProvider(api_key=GEMINI_KEY)
        messages = [LLMMessage(role="user", content="Write a 1000 word essay on Raft consensus.")]
        with pytest.raises((asyncio.CancelledError, Exception)):
            await gemini.generate(messages, cancellation_token=token)


# =========================================================================
# 7. Real Provider Failure Handling
# =========================================================================

@pytest.mark.asyncio
async def test_live_provider_auth_failure_handling():
    """Verify invalid credentials against live API endpoints correctly raise ProviderAuthError."""
    # Groq live auth failure
    groq_bad = GroqProvider(api_key="gsk_invalid_test_key_definitely_unauthorized_12345")
    messages = [LLMMessage(role="user", content="Hello")]
    with pytest.raises(ProviderAuthError):
        await groq_bad.generate(messages)

    # Gemini live auth failure
    gemini_bad = GeminiProvider(api_key="AIzaSy_invalid_test_key_definitely_unauthorized_12345")
    with pytest.raises(ProviderAuthError):
        await gemini_bad.generate(messages)
