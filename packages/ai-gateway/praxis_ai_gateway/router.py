from typing import Optional, Dict, Any
from pydantic import BaseModel
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import asyncio
import logging
import time

from praxis_ai_gateway.base import LLMProvider, ProviderCapabilities
from praxis_ai_gateway.registry import ModelRegistry
from praxis_ai_gateway.resilience import CircuitBreaker, with_retries
from praxis_ai_gateway.budget import BudgetGuard
from praxis_ai_gateway.persistence import as_uuid_str, resolve_db, safe_write

logger = logging.getLogger("praxis.ai_gateway")

class RoutingContext(BaseModel):
    user_id: str
    session_id: Optional[str] = None
    local_only: bool = False
    zero_spend_mode: bool = False
    latency_budget_ms: Optional[int] = None
    preferred_provider: Optional[str] = None

class RoutedCall(BaseModel):
    provider_name: str
    model: str
    result: Any

class AllProvidersUnavailableError(Exception):
    pass

class GatewayRouter:
    def __init__(
        self,
        registry: ModelRegistry,
        providers: Dict[str, LLMProvider],
        redis: Redis,
        db: Optional[AsyncSession] = None,
        session_factory: Any = None,
    ):
        self.registry = registry
        self.providers = providers
        self.redis = redis
        # `db` may be a request-scoped session; long-lived routers should pass
        # `session_factory` instead so telemetry uses short-lived sessions.
        self.db = resolve_db(db, session_factory)
        self.budget_guard = BudgetGuard(redis, self.db)

    async def route(self, task: str, context: RoutingContext, method_name: str, *args, cancellation_token: Any = None, **kw) -> RoutedCall:
        if method_name == "generate_structured":
            method_name = "structured"
        elif method_name == "generate_stream":
            method_name = "stream"
            
        if "messages" in kw:
            from praxis_ai_gateway.base import LLMMessage
            kw["messages"] = [
                LLMMessage(**m) if isinstance(m, dict) else m 
                for m in kw["messages"]
            ]
            
        req_caps_dict = {}
        if context.zero_spend_mode:
            req_caps_dict["is_free_tier"] = True
            
        req_caps = ProviderCapabilities(**{
            "streaming": False, "structured_output": False, "vision": False, 
            "embeddings": False, "realtime_audio": False, "max_context_tokens": 0, 
            "is_local": False, "is_free_tier": False,
            **req_caps_dict
        })
        
        candidates = self.registry.filter_candidates(
            task=task,
            providers=self.providers,
            required_capabilities=req_caps,
            local_only=context.local_only
        )
        
        if context.preferred_provider:
            candidates = sorted(candidates, key=lambda c: c[0].name != context.preferred_provider)
            
        if not candidates:
            raise AllProvidersUnavailableError("No configured providers match the context requirements.")

        if method_name == "stream":
            return RoutedCall(
                provider_name="router_stream",
                model="multiplexed",
                result=self._stream_with_fallback(task, candidates, context, args, kw, cancellation_token)
            )

        # Non-streaming path
        failure_reasons = {}
        last_provider = None
        for provider, config in candidates:
            model_id = config["model"]
            if not provider.capabilities().is_free_tier:
                est_cost = (1000 / 1000 * config.get("cost_per_1k_input", 0.0)) + (1000 / 1000 * config.get("cost_per_1k_output", 0.0))
                await self.budget_guard.check_consent(context.user_id)
                await self.budget_guard.check_and_reserve(context.user_id, context.session_id, est_cost)
            
            breaker = CircuitBreaker(self.redis, self.db, provider.name, method_name)
            if not await breaker.can_execute():
                failure_reasons[provider.name] = "Circuit breaker OPEN"
                continue
                
            async def _call():
                return await getattr(provider, method_name)(*args, cancellation_token=cancellation_token, model=model_id, **kw)
                
            from opentelemetry import trace
            tracer = trace.get_tracer(__name__)
            started = time.perf_counter()
            try:
                with tracer.start_as_current_span("router_attempt") as span:
                    span.set_attribute("provider", provider.name)
                    span.set_attribute("model", model_id)
                    span.set_attribute("method", method_name)
                    if last_provider:
                        span.set_attribute("fell_back_from", last_provider)
                        span.set_attribute("fallback_reason", failure_reasons.get(last_provider, "Unknown"))
                    result = await with_retries(_call, breaker, cancellation_token)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                latency_ms = round((time.perf_counter() - started) * 1000, 1)
                failure_reasons[provider.name] = str(e)
                logger.warning("ai_call_failed", extra={
                    "task": task, "provider": provider.name, "model": model_id, "method": method_name,
                    "latency_ms": latency_ms, "error_type": type(e).__name__,
                })
                last_provider = provider.name
                continue

            latency_ms = round((time.perf_counter() - started) * 1000, 1)
            # Telemetry is best-effort and must never turn a success into a failure.
            try:
                if last_provider:
                    await self._log_fallback(task, last_provider, provider.name, model_id, failure_reasons.get(last_provider, "Unknown"))
                await self._log_usage(
                    user_id=context.user_id,
                    session_id=context.session_id,
                    provider_name=provider.name,
                    model_id=model_id,
                    capability=method_name,
                    result=result,
                    config=config,
                    is_free=provider.capabilities().is_free_tier,
                    latency_ms=latency_ms,
                    fell_back_from=last_provider,
                    task=task,
                )
            except Exception as e:
                logger.warning("ai_usage_logging_failed", extra={"error_type": type(e).__name__})
            return RoutedCall(provider_name=provider.name, model=model_id, result=result)

        err_msg = "All providers unavailable:\n" + "\n".join([f"- {p}: {r}" for p, r in failure_reasons.items()])
        raise AllProvidersUnavailableError(err_msg)

    async def _stream_with_fallback(self, task, candidates, context, args, kw, cancellation_token):
        failure_reasons = {}
        last_provider = None
        
        for provider, config in candidates:
            model_id = config["model"]
            if not provider.capabilities().is_free_tier:
                est_cost = (1000 / 1000 * config.get("cost_per_1k_input", 0.0)) + (1000 / 1000 * config.get("cost_per_1k_output", 0.0))
                await self.budget_guard.check_consent(context.user_id)
                await self.budget_guard.check_and_reserve(context.user_id, context.session_id, est_cost)
                
            breaker = CircuitBreaker(self.redis, self.db, provider.name, "stream")
            if not await breaker.can_execute():
                failure_reasons[provider.name] = "Circuit breaker OPEN"
                continue
                
            from opentelemetry import trace
            tracer = trace.get_tracer(__name__)
            span = tracer.start_span("router_attempt")
            span.set_attribute("provider", provider.name)
            span.set_attribute("method", "stream")
            
            try:
                if last_provider:
                    await self._log_fallback(task, last_provider, provider.name, model_id, failure_reasons.get(last_provider, "Unknown"))
                
                gen = provider.stream(*args, cancellation_token=cancellation_token, model=model_id, **kw)
                
                # Check for mid-stream failure
                completed_successfully = False
                async for chunk in gen:
                    yield chunk
                    if chunk.is_final:
                        completed_successfully = True
                        
                if not completed_successfully and not (cancellation_token and cancellation_token.is_cancelled()):
                    # It exited without yielding is_final! That's a truncated stream.
                    raise RuntimeError(f"Stream from {provider.name} terminated prematurely without is_final=True")
                    
                await breaker.record_success()
                span.end()
                return # Done successfully!
                
            except Exception as e:
                if isinstance(e, asyncio.CancelledError):
                    span.end()
                    raise
                await breaker.record_failure()
                span.set_attribute("error", str(e))
                span.end()
                failure_reasons[provider.name] = str(e)
                last_provider = provider.name
                
                # Fallback to next provider!
                continue
                
        raise AllProvidersUnavailableError(f"All providers failed streaming: {failure_reasons}")
        
    async def _log_fallback(self, task: str, fell_back_from: str, fell_back_to: str, model: str, reason: str):
        logger.info("ai_fallback", extra={
            "task": task, "fell_back_from": fell_back_from, "provider": fell_back_to, "model": model,
            "reason": (reason or "")[:200],
        })

    async def _log_usage(self, user_id, session_id, provider_name, model_id, capability, result, config, is_free,
                         latency_ms: float = 0.0, fell_back_from: Optional[str] = None, task: Optional[str] = None):
        in_tok = getattr(result, "input_tokens", 0) or 0
        out_tok = getattr(result, "output_tokens", 0) or 0

        est_cost = 0.0
        if not is_free:
            c_in = config.get("cost_per_1k_input", 0.0)
            c_out = config.get("cost_per_1k_output", 0.0)
            est_cost = (in_tok / 1000 * c_in) + (out_tok / 1000 * c_out)

        logger.info("ai_call", extra={
            "task": task, "provider": provider_name, "model": model_id, "method": capability,
            "latency_ms": latency_ms, "input_tokens": in_tok, "output_tokens": out_tok,
            "estimated_cost_usd": round(est_cost, 6), "fell_back_from": fell_back_from,
        })

        profile_id = as_uuid_str(user_id)
        if profile_id is not None:
            query = text("""
                INSERT INTO usage_events (profile_id, session_id, provider, model, capability, input_tokens,
                                          output_tokens, estimated_cost_usd, was_free_tier, latency_ms,
                                          fell_back_from, request_count)
                VALUES (CAST(:uid AS uuid), CAST(:sid AS uuid), :prov, :mod, :cap, :in_tok, :out_tok, :cost,
                        :free, :latency, :fell_back_from, 1)
            """)
            await safe_write(self.db, query, {
                "uid": profile_id,
                "sid": as_uuid_str(session_id),
                "prov": provider_name,
                "mod": model_id,
                "cap": capability,
                "in_tok": in_tok,
                "out_tok": out_tok,
                "cost": est_cost,
                "free": is_free,
                "latency": int(latency_ms),
                "fell_back_from": fell_back_from,
            }, what="usage_events")

        if not is_free and est_cost > 0:
            await self.budget_guard.commit_spend(user_id, session_id, est_cost)
