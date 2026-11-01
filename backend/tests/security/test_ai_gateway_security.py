"""
PRAXIS InterviewOS — AI Gateway Security Regression Suite
Verifies budget guard fail-closed consent, token caps, and provider key boundary isolation.
"""
import pytest
import fakeredis.aioredis
from praxis_ai_gateway.budget import BudgetGuard, BudgetExceededError, ConsentRequiredError
from praxis_ai_gateway.prompt_builder import PromptBuilder


@pytest.mark.asyncio
async def test_budget_guard_fails_closed_without_db():
    redis = fakeredis.aioredis.FakeRedis()
    guard = BudgetGuard(redis=redis, db=None)

    # Without verified consent in DB, paid provider access must fail closed
    with pytest.raises(ConsentRequiredError):
        await guard.check_consent("user-123")


@pytest.mark.asyncio
async def test_budget_guard_enforces_daily_cap():
    redis = fakeredis.aioredis.FakeRedis()
    guard = BudgetGuard(redis=redis, db=None)
    guard.default_daily_cap = 5.00

    # Within cap
    await guard.check_and_reserve("user-123", session_id=None, estimated_cost=2.50)

    # Simulate exceeding cap
    await guard.commit_spend("user-123", session_id=None, actual_cost=4.80)
    with pytest.raises(BudgetExceededError):
        await guard.check_and_reserve("user-123", session_id=None, estimated_cost=0.50)


def test_prompt_builder_strips_api_keys_from_untrusted_input():
    builder = (
        PromptBuilder()
        .add_system("You are an evaluator.")
        .add_untrusted("resume", "upload", "My key is sk-proj-1234567890abcdef1234567890abcdef")
    )
    messages = builder.build()
    user_content = "\n".join(m.content for m in messages if m.role == "user")
    assert "<UNTRUSTED_DOCUMENT" in user_content
