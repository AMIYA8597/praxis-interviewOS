import time
import asyncio
import random
from typing import Optional, Callable, Any
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from praxis_ai_gateway.errors import (
    ProviderAuthError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderServerError
)

class GatewayExhaustedError(Exception):
    pass

class CircuitBreaker:
    def __init__(
        self,
        redis: Redis,
        db: AsyncSession,
        provider_name: str,
        capability: str,
        max_failures: int = 5,
        cooldown_seconds: int = 30
    ):
        self.redis = redis
        self.db = db
        self.provider_name = provider_name
        self.capability = capability
        self.max_failures = max_failures
        self.cooldown_seconds = cooldown_seconds
        
        self._key_failures = f"cb:failures:{provider_name}:{capability}"
        self._key_state = f"cb:state:{provider_name}:{capability}"
        
    async def get_state(self) -> str:
        state = await self.redis.get(self._key_state)
        return state.decode("utf-8") if state else "CLOSED"
        
    async def record_failure(self):
        failures = await self.redis.incr(self._key_failures)
        if failures >= self.max_failures:
            current_state = await self.get_state()
            if current_state != "OPEN":
                await self._transition_to("OPEN")
                
    async def record_success(self):
        current_state = await self.get_state()
        if current_state in ("HALF_OPEN", "OPEN"):
            await self._transition_to("CLOSED")
        await self.redis.delete(self._key_failures)
        
    async def _transition_to(self, new_state: str):
        # Redis
        if new_state == "OPEN":
            # Set state to OPEN with an expiry (cooldown). Once expired, it becomes HALF_OPEN conceptually,
            # but we can represent HALF_OPEN by checking if state key exists and failures > 0.
            # Actually, let's explicitly manage it.
            await self.redis.set(self._key_state, "OPEN", ex=self.cooldown_seconds)
        elif new_state == "CLOSED":
            await self.redis.set(self._key_state, "CLOSED")
            await self.redis.delete(self._key_failures)
            
        # Postgres (provider_health)
        query = text("""
            INSERT INTO provider_health (provider_name, status, details)
            VALUES (:provider, :status, :details)
        """)
        await self.db.execute(query, {
            "provider": self.provider_name,
            "status": "degraded" if new_state == "OPEN" else "healthy",
            "details": f"Circuit breaker transitioned to {new_state} for {self.capability}"
        })
        await self.db.commit()

    async def can_execute(self) -> bool:
        state = await self.get_state()
        if state == "CLOSED":
            return True
        elif state == "OPEN":
            return False
        else:
            # If state key expired but failures exist, we are HALF_OPEN
            # We set state to HALF_OPEN to allow exactly ONE probe through.
            # We use SETNX to ensure only one worker probes.
            is_half_open = await self.redis.set(self._key_state, "HALF_OPEN", nx=True, ex=self.cooldown_seconds)
            return bool(is_half_open)

async def with_retries(
    func: Callable,
    breaker: CircuitBreaker,
    cancellation_token: Any = None,
    max_retries: int = 2,
    base_delay_ms: int = 200
):
    if not await breaker.can_execute():
        raise GatewayExhaustedError(f"Circuit breaker OPEN for {breaker.provider_name}")
        
    attempts = 0
    while attempts <= max_retries:
        if cancellation_token and cancellation_token.is_cancelled():
            raise asyncio.CancelledError(cancellation_token.reason)
            
        try:
            result = await func()
            await breaker.record_success()
            return result
        except ProviderAuthError as e:
            # Never retry auth
            await breaker.record_failure()
            raise GatewayExhaustedError(f"Auth error: {e}") from e
        except (ProviderRateLimitError, ProviderTimeoutError, ProviderServerError) as e:
            attempts += 1
            await breaker.record_failure()
            if attempts > max_retries:
                raise GatewayExhaustedError(f"Retries exhausted: {e}") from e
            
            # Exponential backoff with jitter
            delay = (base_delay_ms * (2 ** (attempts - 1))) + random.randint(0, 50)
            
            # Async sleep allowing cancellation
            sleep_task = asyncio.create_task(asyncio.sleep(delay / 1000.0))
            if hasattr(cancellation_token, "wait_cancelled"):
                cancel_task = asyncio.create_task(cancellation_token.wait_cancelled())
                done, pending = await asyncio.wait([sleep_task, cancel_task], return_when=asyncio.FIRST_COMPLETED)
                for p in pending: p.cancel()
                if cancel_task in done:
                    raise asyncio.CancelledError()
            else:
                await sleep_task
        except asyncio.CancelledError:
            raise
        except Exception as e:
            # Unknown error, don't retry, but record failure
            await breaker.record_failure()
            raise GatewayExhaustedError(f"Unknown error: {e}") from e
