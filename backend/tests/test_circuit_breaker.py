import pytest
import pytest_asyncio
from backend.app.services.provider_resilience import CircuitBreaker, CircuitState


@pytest_asyncio.fixture
async def cb():
    return CircuitBreaker(failure_threshold=3, recovery_timeout_s=0.1, success_threshold=2)


@pytest.mark.asyncio
async def test_starts_closed(cb):
    assert await cb.can_call("test") is True
    states = await cb.get_all_states()
    assert states.get("test") == "closed"


@pytest.mark.asyncio
async def test_opens_after_threshold(cb):
    for _ in range(3):
        await cb.record_failure("test")
    assert await cb.can_call("test") is False
    states = await cb.get_all_states()
    assert states["test"] == "open"


@pytest.mark.asyncio
async def test_half_open_after_timeout(cb):
    for _ in range(3):
        await cb.record_failure("test")
    assert await cb.can_call("test") is False

    import asyncio
    await asyncio.sleep(0.15)

    assert await cb.can_call("test") is True
    states = await cb.get_all_states()
    assert states["test"] == "half_open"


@pytest.mark.asyncio
async def test_closes_after_success_threshold(cb):
    for _ in range(3):
        await cb.record_failure("test")

    import asyncio
    await asyncio.sleep(0.15)
    await cb.can_call("test")  # triggers HALF_OPEN

    await cb.record_success("test")
    await cb.record_success("test")
    states = await cb.get_all_states()
    assert states["test"] == "closed"


@pytest.mark.asyncio
async def test_reopens_on_half_open_failure(cb):
    for _ in range(3):
        await cb.record_failure("test")

    import asyncio
    await asyncio.sleep(0.15)
    await cb.can_call("test")  # triggers HALF_OPEN

    await cb.record_failure("test")
    states = await cb.get_all_states()
    assert states["test"] == "open"


@pytest.mark.asyncio
async def test_independent_providers(cb):
    for _ in range(3):
        await cb.record_failure("groq")
    assert await cb.can_call("groq") is False
    assert await cb.can_call("openai") is True
