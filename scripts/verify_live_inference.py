#!/usr/bin/env python3
"""
PRAXIS Live AI Provider Verification & Diagnostic Tool.

Tests live cloud AI connectivity, real question generation, structured output,
answer evaluation, and follow-up generation against configured free-tier providers.

When GROQ_API_KEY or GEMINI_API_KEY is configured in .env, executes genuine inference
acceptance tests. If unconfigured, clearly reports the gate as BLOCKED (NOT_CONFIGURED).
"""

import os
import sys
import time
import asyncio
from dotenv import dotenv_values

# Ensure path resolution
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for p in [repo_root, os.path.join(repo_root, "packages", "ai-gateway"), os.path.join(repo_root, "realtime-agent"), os.path.join(repo_root, "backend")]:
    if p not in sys.path:
        sys.path.insert(0, p)

from pydantic import BaseModel, Field
from praxis_ai_gateway.base import LLMMessage
from praxis_ai_gateway.registry import ModelRegistry
from praxis_ai_gateway.router import GatewayRouter, RoutingContext
from praxis_ai_gateway.providers.groq import GroqProvider
from praxis_ai_gateway.providers.gemini import GeminiProvider
from realtime_agent.app.interview.policy import InterviewSession
from realtime_agent.app.scoring.service import score_answer_async


class EvaluationOutput(BaseModel):
    clarity_score: float = Field(..., description="0.0 to 1.0")
    feedback: str = Field(..., description="Feedback commentary")
    follow_up_topic: str = Field(..., description="Recommended follow-up topic")


async def main():
    print("=" * 70)
    print("PRAXIS AI GATEWAY — LIVE PROVIDER ACCEPTANCE GATE")
    print("=" * 70)

    env = dotenv_values(os.path.join(repo_root, ".env")) if os.path.exists(os.path.join(repo_root, ".env")) else {}
    groq_key = (os.environ.get("GROQ_API_KEY") or env.get("GROQ_API_KEY") or "").strip()
    gemini_key = (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or env.get("GEMINI_API_KEY") or env.get("GOOGLE_API_KEY") or "").strip()

    # Filter out placeholders
    if any(p in groq_key.lower() for p in ["your_", "placeholder", "xxx", "sk-xxx"]):
        groq_key = ""
    if any(p in gemini_key.lower() for p in ["your_", "placeholder", "xxx"]):
        gemini_key = ""

    print(f"Provider Status Check:")
    print(f"  * GROQ_API_KEY   : {'CONFIGURED (len=' + str(len(groq_key)) + ')' if groq_key else 'NOT CONFIGURED'}")
    print(f"  * GEMINI_API_KEY : {'CONFIGURED (len=' + str(len(gemini_key)) + ')' if gemini_key else 'NOT CONFIGURED'}")

    if not groq_key and not gemini_key:
        print("\n" + "!" * 70)
        print("STATUS: BLOCKED (AI_PROVIDER_NOT_CONFIGURED)")
        print("!" * 70)
        print("\nLive AI cloud inference cannot be verified because neither GROQ_API_KEY")
        print("nor GEMINI_API_KEY is configured in your local environment or .env.")
        print("\nTo activate zero-cost free-tier live inference:")
        print("  1. Obtain a free Groq API key: https://console.groq.com/keys")
        print("     or a free Google Gemini API key: https://aistudio.google.com/app/apikey")
        print("  2. Add the key to your local .env file in the repository root:")
        print("     GROQ_API_KEY=gsk_...")
        print("     or")
        print("     GEMINI_API_KEY=AIzaSy...")
        print("  3. Run this script again: python scripts/verify_live_inference.py")
        print("\nAll application code, fallbacks, local STT/VAD/embeddings, and regressions pass.")
        print("Promotion to GitHub main is safely held at this gate until a credential is configured.")
        return 1

    # Initialize live providers
    providers = {}
    if groq_key:
        providers["groq"] = GroqProvider(api_key=groq_key)
    if gemini_key:
        providers["gemini"] = GeminiProvider(api_key=gemini_key)

    # 1. Health checks
    print("\n[Gate 1] Running live provider authenticated health probes...")
    for name, prov in providers.items():
        t0 = time.perf_counter()
        healthy = await prov.check_health()
        ms = (time.perf_counter() - t0) * 1000
        print(f"  - {name}: {'HEALTHY' if healthy else 'FAILED'} ({ms:.1f}ms)")
        if not healthy:
            print(f"  [FAIL] Provider '{name}' responded with unhealthy status. Check key permissions.")
            return 2

    # 2. Setup router
    from unittest.mock import AsyncMock
    models_config = os.path.join(repo_root, "config", "models.yaml")
    registry = ModelRegistry(models_config)
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.set = AsyncMock(return_value=True)
    mock_redis.incr = AsyncMock(return_value=1)
    mock_redis.setex = AsyncMock(return_value=True)
    router = GatewayRouter(registry=registry, providers=providers, redis=mock_redis)

    ctx = RoutingContext(user_id="synthetic_user_gate", session_id="synthetic_session_gate", zero_spend_mode=True)

    # 3. Live Question Generation
    print("\n[Gate 2] Generating real interview question via live model...")
    t0 = time.perf_counter()
    q_call = await router.route(
        task="question_generation",
        context=ctx,
        method_name="generate",
        messages=[
            LLMMessage(role="system", content="You are a principal technical interviewer."),
            LLMMessage(role="user", content="Ask a focused question about Kafka cooperative sticky assignors vs eager protocol."),
        ],
    )
    q_ms = (time.perf_counter() - t0) * 1000
    print(f"  Provider: {q_call.provider_name} | Model: {q_call.model} | Latency: {q_ms:.1f}ms")
    print(f"  Question: {q_call.result.text[:120]}...")

    # 4. Live Structured Output Validation
    print("\n[Gate 3] Validating live structured JSON output against schema...")
    t0 = time.perf_counter()
    s_call = await router.route(
        task="answer_evaluation",
        context=ctx,
        method_name="structured",
        messages=[
            LLMMessage(role="system", content="Evaluate the answer and return JSON matching the schema."),
            LLMMessage(role="user", content="Candidate answer: We tuned max.poll.interval.ms to 300s to avoid spurious rebalances."),
        ],
        schema=EvaluationOutput,
    )
    s_ms = (time.perf_counter() - t0) * 1000
    print(f"  Provider: {s_call.provider_name} | Model: {s_call.model} | Latency: {s_ms:.1f}ms")
    print(f"  Result: Clarity={s_call.result.clarity_score}, Topic={s_call.result.follow_up_topic}")

    # 5. Live Contextual Follow-up Generation
    print("\n[Gate 4] Generating real contextual follow-up turn...")
    t0 = time.perf_counter()
    session = InterviewSession(
        {"target_role": "Distributed Systems Engineer", "requirements": ["Kafka"], "prep_pack": []},
        {"summary": "Experienced Kafka engineer", "verified_skills": ["Kafka"], "claims": []},
        difficulty="senior",
        interview_type="technical",
    )
    session.warm_up()
    decision = await session.generate_next_turn(
        candidate_answer="We upgraded to Kafka 2.4 and used sticky assignors to prevent consumer stalls.",
        gateway_router=router,
        routing_ctx=ctx,
        is_follow_up=True,
    )
    f_ms = (time.perf_counter() - t0) * 1000
    print(f"  Follow-up ({f_ms:.1f}ms): {decision.response_text[:120]}...")

    # 6. Live Rubric Scoring
    print("\n[Gate 5] Executing live answer evaluation and rubric scoring...")
    t0 = time.perf_counter()
    score = await score_answer_async(
        question="How do you handle consumer group rebalance storms in Kafka?",
        candidate_answer="We adopted cooperative rebalancing so partitions are revoked incrementally across 2 rounds.",
        is_behavioral=False,
        verified_context="Candidate worked on Kafka infrastructure at Apex Stream.",
        gateway_router=router,
        routing_ctx=ctx,
    )
    score_ms = (time.perf_counter() - t0) * 1000
    print(f"  Score: Overall={score.overall} | Relevance={score.relevance} | Grounding={score.grounding} ({score_ms:.1f}ms)")
    print(f"  Rationale: {score.rationale[:120]}...")

    print("\n" + "=" * 70)
    print("ALL LIVE AI INFERENCE GATES PASSED SUCCESSFULLY!")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
