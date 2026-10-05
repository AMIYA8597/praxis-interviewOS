"""
Phase 93 — Zero-Spend and Budget Safety.

Hard spending limits enforced before any billable AI call.
All limits configurable via environment / settings.
When a limit is exceeded: raises BudgetExceeded — never silently continues.
"""
import logging
from datetime import date
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class BudgetExceeded(Exception):
    """Raised when a budget limit is hit. Callers must surface this to the user."""

    def __init__(self, limit_type: str, limit_usd: float, current_usd: float):
        self.limit_type = limit_type
        self.limit_usd = limit_usd
        self.current_usd = current_usd
        super().__init__(
            f"BUDGET_EXCEEDED: {limit_type} limit ${limit_usd:.4f} reached "
            f"(current spend ${current_usd:.4f}). No further billable calls."
        )


# ── Limits (override via environment) ────────────────────────────────────────

def _get_daily_limit() -> float:
    import os
    return float(os.environ.get("PRAXIS_AI_DAILY_BUDGET_USD", "10.0"))


def _get_session_limit() -> float:
    import os
    return float(os.environ.get("PRAXIS_AI_SESSION_BUDGET_USD", "0.50"))


def _get_request_token_limit() -> int:
    import os
    return int(os.environ.get("PRAXIS_AI_REQUEST_MAX_TOKENS", "8192"))


def _zero_spend_mode() -> bool:
    import os
    return os.environ.get("PRAXIS_ZERO_SPEND", "false").lower() == "true"


# ── Guards ────────────────────────────────────────────────────────────────────

async def check_daily_budget(db: AsyncSession) -> None:
    """Raise BudgetExceeded if today's AI spend has reached the daily limit."""
    if _zero_spend_mode():
        raise BudgetExceeded("zero_spend_mode", 0.0, 0.0)

    limit = _get_daily_limit()
    today = date.today().isoformat()
    row = await db.execute(text("""
        SELECT COALESCE(SUM(cost_usd), 0) FROM ai_provider_call_log
        WHERE DATE(created_at) = :today
    """), {"today": today})
    current = float(row.scalar() or 0.0)
    if current >= limit:
        logger.warning("daily_budget_exceeded", extra={"limit": limit, "current": current})
        raise BudgetExceeded("daily", limit, current)


async def check_session_budget(db: AsyncSession, session_id: str) -> None:
    """Raise BudgetExceeded if this session has reached its per-session limit."""
    if _zero_spend_mode():
        raise BudgetExceeded("zero_spend_mode", 0.0, 0.0)

    limit = _get_session_limit()
    row = await db.execute(text("""
        SELECT COALESCE(SUM(cost_usd), 0) FROM ai_provider_call_log
        WHERE session_id = :sid
    """), {"sid": session_id})
    current = float(row.scalar() or 0.0)
    if current >= limit:
        logger.warning("session_budget_exceeded", extra={"session_id": session_id, "limit": limit, "current": current})
        raise BudgetExceeded("session", limit, current)


def check_request_tokens(input_tokens: int, output_tokens: Optional[int] = None) -> None:
    """Raise BudgetExceeded if a single request would exceed the token cap."""
    limit = _get_request_token_limit()
    total = input_tokens + (output_tokens or 0)
    if total > limit:
        raise BudgetExceeded("request_tokens", limit / 1000, total / 1000)


async def get_budget_status(db: AsyncSession, session_id: Optional[str] = None) -> dict:
    """Return current spend vs limits for the dashboard/observability endpoint."""
    today = date.today().isoformat()
    daily_row = await db.execute(text("""
        SELECT COALESCE(SUM(cost_usd), 0) FROM ai_provider_call_log
        WHERE DATE(created_at) = :today
    """), {"today": today})
    daily_spend = float(daily_row.scalar() or 0.0)

    session_spend = 0.0
    if session_id:
        s_row = await db.execute(text("""
            SELECT COALESCE(SUM(cost_usd), 0) FROM ai_provider_call_log
            WHERE session_id = :sid
        """), {"sid": session_id})
        session_spend = float(s_row.scalar() or 0.0)

    return {
        "zero_spend_mode": _zero_spend_mode(),
        "daily": {
            "limit_usd": _get_daily_limit(),
            "spent_usd": round(daily_spend, 6),
            "remaining_usd": round(max(0.0, _get_daily_limit() - daily_spend), 6),
            "exceeded": daily_spend >= _get_daily_limit(),
        },
        "session": {
            "limit_usd": _get_session_limit(),
            "spent_usd": round(session_spend, 6),
            "exceeded": session_spend >= _get_session_limit() if session_id else False,
        },
        "request_token_limit": _get_request_token_limit(),
    }
