import pytest
import asyncio
import time
from unittest.mock import AsyncMock, patch
from praxis_ai_gateway.cancellation import CancellationToken
from praxis_ai_gateway.providers.openai import OpenAIProvider
from praxis_ai_gateway.resilience import CircuitBreaker, with_retries, GatewayExhaustedError
from praxis_ai_gateway.errors import ProviderRateLimitError

@pytest.mark.asyncio
async def test_task1_cancellation_token_forwarding():
    # Task 3: Regression test for Task 1
    # Verify the inner `_generate` receives the real token
    
    provider = OpenAIProvider(api_key="test-key")
    token = CancellationToken()
    token.cancel("Test cancellation")
    
    # We patch the inner _generate to intercept the call
    inner_mock = AsyncMock()
    # We must simulate what the real _generate would do, e.g. check the token (if it did)
    # but the test requirements say "asserts the INNER _generate implementation actually observed is_cancelled() == True when checked"
    # So we'll have the mock do exactly that.
    async def mock_generate(*args, **kw):
        inner_token = kw.get("cancellation_token")
        assert inner_token is not None, "Token was not forwarded!"
        assert inner_token.is_cancelled() is True, "Token was not cancelled!"
        return "Success"
        
    provider._generate = mock_generate
    
    # Run the outer method
    # It might raise asyncio.CancelledError because with_cancellation raises it,
    # but the inner call happens first.
    try:
        await provider.generate(messages=[], cancellation_token=token)
    except asyncio.CancelledError:
        pass
    
    # If the inner mock's assertions passed, the test passes.

@pytest.mark.asyncio
async def test_task2_early_exit_on_backoff():
    # Task 4: Regression test for Task 2
    # Verify that `with_retries` exits BEFORE the full backoff duration when cancelled.
    
    breaker = AsyncMock(spec=CircuitBreaker)
    breaker.can_execute.return_value = True
    breaker.record_failure = AsyncMock()
    breaker.record_success = AsyncMock()
    
    token = CancellationToken()
    
    async def always_rate_limit():
        raise ProviderRateLimitError("Rate limited!")
        
    start_time = time.perf_counter()
    
    # Start the retries as a background task
    # We use a huge base delay to ensure it would normally take 10s
    retry_task = asyncio.create_task(
        with_retries(always_rate_limit, breaker, cancellation_token=token, max_retries=1, base_delay_ms=10000)
    )
    
    # Let it fail once and enter the 10s sleep
    await asyncio.sleep(0.1)
    
    # Cancel it during the sleep
    token.cancel("Test early exit")
    
    try:
        await retry_task
    except asyncio.CancelledError:
        pass
    except GatewayExhaustedError:
        pass
        
    elapsed = time.perf_counter() - start_time
    
    # It should exit almost immediately after 0.1s, well under the 10s sleep
    assert elapsed < 5.0, f"Retry loop did not exit early! Elapsed: {elapsed}s"
