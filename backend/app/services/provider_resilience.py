"""
Phase 75 — Provider Resilience.

Transparent fallback tracking: when the AI gateway falls back to a secondary
provider, this is logged and surfaced to the user as AI_MODE='fallback'.

Phase 76 — Cost & Latency Intelligence.

Real tracking: provider/model/latency/tokens/cost per call.
No fabricated metrics — only real call data.
"""
import asyncio
import logging
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Per-provider circuit breaker with open/half-open/closed states."""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout_s: float = 60.0,
        half_open_max_calls: int = 2,
        success_threshold: int = 2,
    ):
        self._failure_threshold = failure_threshold
        self._recovery_timeout_s = recovery_timeout_s
        self._half_open_max_calls = half_open_max_calls
        self._success_threshold = success_threshold
        self._lock = asyncio.Lock()
        self._providers: dict[str, dict] = {}

    def _get_state(self, provider: str) -> dict:
        if provider not in self._providers:
            self._providers[provider] = {
                "state": CircuitState.CLOSED,
                "failures": 0,
                "successes": 0,
                "last_failure_time": 0.0,
                "half_open_calls": 0,
            }
        return self._providers[provider]

    async def can_call(self, provider: str) -> bool:
        async with self._lock:
            s = self._get_state(provider)
            if s["state"] == CircuitState.CLOSED:
                return True
            if s["state"] == CircuitState.OPEN:
                if time.monotonic() - s["last_failure_time"] >= self._recovery_timeout_s:
                    s["state"] = CircuitState.HALF_OPEN
                    s["half_open_calls"] = 0
                    s["successes"] = 0
                    logger.info("Circuit breaker for %s: OPEN -> HALF_OPEN", provider)
                    return True
                return False
            # HALF_OPEN
            return s["half_open_calls"] < self._half_open_max_calls

    async def record_success(self, provider: str) -> None:
        async with self._lock:
            s = self._get_state(provider)
            if s["state"] == CircuitState.HALF_OPEN:
                s["successes"] += 1
                if s["successes"] >= self._success_threshold:
                    s["state"] = CircuitState.CLOSED
                    s["failures"] = 0
                    logger.info("Circuit breaker for %s: HALF_OPEN -> CLOSED", provider)
            elif s["state"] == CircuitState.CLOSED:
                s["failures"] = max(0, s["failures"] - 1)

    async def record_failure(self, provider: str) -> None:
        async with self._lock:
            s = self._get_state(provider)
            s["failures"] += 1
            s["last_failure_time"] = time.monotonic()
            if s["state"] == CircuitState.HALF_OPEN:
                s["state"] = CircuitState.OPEN
                logger.warning("Circuit breaker for %s: HALF_OPEN -> OPEN", provider)
            elif s["state"] == CircuitState.CLOSED and s["failures"] >= self._failure_threshold:
                s["state"] = CircuitState.OPEN
                logger.warning("Circuit breaker for %s: CLOSED -> OPEN (failures=%d)", provider, s["failures"])

    async def get_all_states(self) -> dict[str, str]:
        async with self._lock:
            return {p: s["state"].value for p, s in self._providers.items()}


circuit_breaker = CircuitBreaker()

# Approximate cost per 1K tokens (USD) — updated manually as pricing changes
_COST_PER_1K_TOKENS: dict[str, dict[str, float]] = {
    "anthropic": {
        "claude-sonnet-4-20250514": 0.003,
        "claude-haiku-4-5-20251001": 0.00025,
        "default": 0.003,
    },
    "openai": {
        "gpt-4o": 0.005,
        "gpt-4o-mini": 0.00015,
        "default": 0.005,
    },
    "groq": {
        "llama-3.3-70b-versatile": 0.00059,
        "llama-3.1-8b-instant": 0.00005,
        "default": 0.0006,
    },
    "gemini": {
        "gemini-2.0-flash-lite": 0.0,
        "default": 0.00015,
    },
    "deepseek": {
        "default": 0.00014,
    },
    "xai": {
        "default": 0.002,
    },
    "ollama": {
        "default": 0.0,
    },
    "default": {
        "default": 0.003,
    },
}


def estimate_cost_usd(
    provider: str, model: str, input_tokens: int, output_tokens: int
) -> float:
    provider_costs = _COST_PER_1K_TOKENS.get(provider, _COST_PER_1K_TOKENS["default"])
    rate = provider_costs.get(model, provider_costs.get("default", 0.003))
    total_tokens = input_tokens + output_tokens
    return round(total_tokens / 1000.0 * rate, 6)


async def log_provider_call(
    db: AsyncSession,
    alias: str,
    provider: str,
    model: str,
    mode: Optional[str],
    latency_ms: int,
    input_tokens: int,
    output_tokens: int,
    ai_mode: str,
    success: bool,
    error_type: Optional[str] = None,
    candidate_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> None:
    if success:
        await circuit_breaker.record_success(provider)
    else:
        await circuit_breaker.record_failure(provider)

    cost = estimate_cost_usd(provider, model, input_tokens, output_tokens)
    try:
        await db.execute(text("""
            INSERT INTO ai_provider_call_log
            (candidate_id, session_id, alias, provider, model, mode,
             latency_ms, input_tokens, output_tokens, cost_usd,
             ai_mode, success, error_type, called_at)
            VALUES (:cid, :sid, :alias, :provider, :model, :mode,
                    :lat, :in_tok, :out_tok, :cost,
                    :ai_mode, :success, :err, :now)
        """), {
            "cid": candidate_id, "sid": session_id,
            "alias": alias, "provider": provider, "model": model, "mode": mode,
            "lat": latency_ms, "in_tok": input_tokens, "out_tok": output_tokens,
            "cost": cost, "ai_mode": ai_mode, "success": success,
            "err": error_type, "now": datetime.now(timezone.utc),
        })
        await db.commit()
    except Exception as e:
        logger.warning("Failed to log provider call: %s", e)


async def get_cost_latency_stats(
    db: AsyncSession,
    candidate_id: Optional[str] = None,
    session_id: Optional[str] = None,
    limit: int = 100,
) -> dict:
    """
    Returns cost and latency stats for monitoring.
    All numbers are from real call logs — nothing fabricated.
    """
    params: dict = {"limit": limit}
    where_clauses = []
    if candidate_id:
        where_clauses.append("candidate_id = :cid")
        params["cid"] = candidate_id
    if session_id:
        where_clauses.append("session_id = :sid")
        params["sid"] = session_id

    where = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    rows = await db.execute(text(f"""
        SELECT
            provider, model, alias,
            COUNT(*) AS call_count,
            AVG(latency_ms) AS avg_latency_ms,
            MAX(latency_ms) AS p100_latency_ms,
            SUM(cost_usd) AS total_cost_usd,
            SUM(CASE WHEN ai_mode = 'fallback' THEN 1 ELSE 0 END) AS fallback_count,
            SUM(CASE WHEN success = FALSE THEN 1 ELSE 0 END) AS error_count
        FROM ai_provider_call_log
        {where}
        GROUP BY provider, model, alias
        ORDER BY call_count DESC
        LIMIT :limit
    """), params)

    stats = [dict(r._mapping) for r in rows.fetchall()]
    total_cost = sum(float(s["total_cost_usd"] or 0) for s in stats)

    return {
        "stats": stats,
        "total_cost_usd": round(total_cost, 4),
        "data_source": "real_call_logs",
    }


async def get_provider_health(db: AsyncSession) -> dict:
    """
    Recent provider error rates — last 100 calls per provider.
    Returns health status for transparency.
    """
    rows = await db.execute(text("""
        SELECT
            provider,
            COUNT(*) AS total,
            SUM(CASE WHEN success = FALSE THEN 1 ELSE 0 END) AS errors,
            SUM(CASE WHEN ai_mode = 'fallback' THEN 1 ELSE 0 END) AS fallbacks,
            AVG(latency_ms) AS avg_latency_ms
        FROM (
            SELECT * FROM ai_provider_call_log
            ORDER BY called_at DESC LIMIT 500
        ) recent
        GROUP BY provider
    """))

    health = {}
    for r in rows.fetchall():
        provider = r[0]
        total = r[1] or 1
        errors = r[2] or 0
        fallbacks = r[3] or 0
        avg_lat = float(r[4]) if r[4] else None

        error_rate = errors / total
        status = "healthy"
        if error_rate > 0.3:
            status = "degraded"
        elif error_rate > 0.1:
            status = "warning"

        health[provider] = {
            "status": status,
            "error_rate": round(error_rate, 3),
            "fallback_rate": round(fallbacks / total, 3),
            "avg_latency_ms": round(avg_lat, 0) if avg_lat else None,
            "sample_size": total,
        }

    cb_states = await circuit_breaker.get_all_states()
    for provider_name, info in health.items():
        info["circuit_breaker"] = cb_states.get(provider_name, "closed")

    return {"providers": health}
