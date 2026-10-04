"""
Per-request / per-task correlation context.

Values are stored in ContextVars so they follow the request through awaits
and are automatically attached to every log record by `ContextFilter`.
"""
from contextvars import ContextVar
from typing import Dict, Optional

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")
user_id_ctx: ContextVar[Optional[str]] = ContextVar("user_id", default=None)
candidate_id_ctx: ContextVar[Optional[str]] = ContextVar("candidate_id", default=None)
session_id_ctx: ContextVar[Optional[str]] = ContextVar("session_id", default=None)

# Backwards-compatible alias (previously defined in backend.app.main).
request_id_context = request_id_ctx


def bind(
    *,
    user_id: Optional[str] = None,
    candidate_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> None:
    """Attach identifiers to the current context (only non-None values are set)."""
    if user_id is not None:
        user_id_ctx.set(str(user_id))
    if candidate_id is not None:
        candidate_id_ctx.set(str(candidate_id))
    if session_id is not None:
        session_id_ctx.set(str(session_id))


def snapshot() -> Dict[str, Optional[str]]:
    return {
        "request_id": request_id_ctx.get(),
        "user_id": user_id_ctx.get(),
        "candidate_id": candidate_id_ctx.get(),
        "session_id": session_id_ctx.get(),
    }
