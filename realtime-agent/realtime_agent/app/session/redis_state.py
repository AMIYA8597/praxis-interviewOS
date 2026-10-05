"""
Phase 104 — Realtime Session Resilience.

Session state is stored in Redis so reconnections (to any Cloud Run instance)
can resume the session without starting over.

Key design decisions:
- State is written to Redis on every meaningful transition.
- Redis is used for coordination only; the database remains authoritative.
- A session lock (SET NX EX) prevents two instances from running the same
  session simultaneously.
- On SIGTERM / clean shutdown, the lock is released immediately.
"""
import json
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

# TTLs
SESSION_STATE_TTL_S = 7200     # 2 hours — maximum session length
SESSION_LOCK_TTL_S = 30        # lock heartbeat; renewed every ~10s
SEQUENCE_NUMBER_TTL_S = 86400  # 24h to support late reconnects


def _state_key(session_id: str) -> str:
    return f"praxis:session:{session_id}:state"


def _lock_key(session_id: str) -> str:
    return f"praxis:session:{session_id}:lock"


def _seq_key(session_id: str) -> str:
    return f"praxis:session:{session_id}:seq"


async def acquire_session_lock(redis, session_id: str, instance_id: str) -> bool:
    """Acquire the per-session lock for this instance. Returns True if acquired."""
    try:
        acquired = await redis.set(
            _lock_key(session_id),
            instance_id,
            ex=SESSION_LOCK_TTL_S,
            nx=True,
        )
        return bool(acquired)
    except Exception as e:
        logger.warning("session_lock_acquire_failed", extra={"session_id": session_id, "error": str(e)})
        return True  # fail open: allow the session to proceed without coordination


async def renew_session_lock(redis, session_id: str, instance_id: str) -> bool:
    """Renew the lock TTL. Returns False if lock was stolen by another instance."""
    try:
        current = await redis.get(_lock_key(session_id))
        if current and current.decode() == instance_id:
            await redis.expire(_lock_key(session_id), SESSION_LOCK_TTL_S)
            return True
        return False
    except Exception as e:
        logger.warning("session_lock_renew_failed", extra={"session_id": session_id, "error": str(e)})
        return True  # fail open


async def release_session_lock(redis, session_id: str, instance_id: str) -> None:
    """Release the lock only if this instance holds it."""
    try:
        current = await redis.get(_lock_key(session_id))
        if current and current.decode() == instance_id:
            await redis.delete(_lock_key(session_id))
    except Exception as e:
        logger.warning("session_lock_release_failed", extra={"session_id": session_id, "error": str(e)})


async def save_session_state(redis, session_id: str, state: dict) -> None:
    """Persist session state to Redis for cross-instance recovery."""
    try:
        await redis.set(
            _state_key(session_id),
            json.dumps(state),
            ex=SESSION_STATE_TTL_S,
        )
    except Exception as e:
        logger.warning("session_state_save_failed", extra={"session_id": session_id, "error": str(e)})


async def load_session_state(redis, session_id: str) -> Optional[dict]:
    """Load session state from Redis. Returns None if not found."""
    try:
        raw = await redis.get(_state_key(session_id))
        if raw:
            return json.loads(raw)
    except Exception as e:
        logger.warning("session_state_load_failed", extra={"session_id": session_id, "error": str(e)})
    return None


async def delete_session_state(redis, session_id: str) -> None:
    """Remove session state after session completes."""
    try:
        await redis.delete(
            _state_key(session_id),
            _lock_key(session_id),
            _seq_key(session_id),
        )
    except Exception as e:
        logger.warning("session_state_delete_failed", extra={"session_id": session_id, "error": str(e)})


async def get_next_sequence(redis, session_id: str) -> int:
    """Atomic sequence counter for deduplication on reconnect."""
    try:
        seq = await redis.incr(_seq_key(session_id))
        await redis.expire(_seq_key(session_id), SEQUENCE_NUMBER_TTL_S)
        return int(seq)
    except Exception as e:
        logger.warning("session_seq_failed", extra={"session_id": session_id, "error": str(e)})
        import time
        return int(time.time() * 1000)  # monotonic fallback
