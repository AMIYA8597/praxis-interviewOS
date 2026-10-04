"""
Best-effort persistence helpers for gateway telemetry.

Telemetry writes (usage, fallbacks, breaker state) must NEVER fail or slow
down an otherwise successful model call, so every write here swallows and
logs errors. `SessionFactoryDB` adapts an async_sessionmaker to the small
`execute()/commit()` surface the gateway uses, opening a short-lived session
per statement so a long-lived router never pins a connection.
"""
import logging
import uuid
from typing import Any, Optional

logger = logging.getLogger("praxis.ai_gateway")


class SessionFactoryDB:
    def __init__(self, session_factory):
        self._factory = session_factory

    async def execute(self, statement, params: Optional[dict] = None):
        async with self._factory() as session:
            result = await session.execute(statement, params or {})
            await session.commit()
            return result

    async def commit(self) -> None:  # statements are committed in execute()
        return None


def resolve_db(db: Any, session_factory: Any) -> Any:
    if db is not None:
        return db
    if session_factory is not None:
        return SessionFactoryDB(session_factory)
    return None


async def safe_write(db: Any, statement, params: dict, *, what: str) -> bool:
    if db is None:
        return False
    try:
        await db.execute(statement, params)
        await db.commit()
        return True
    except Exception as e:
        logger.warning("gateway_telemetry_write_failed", extra={"what": what, "error_type": type(e).__name__})
        try:
            rollback = getattr(db, "rollback", None)
            if rollback is not None:
                await rollback()
        except Exception:
            pass
        return False


def as_uuid_str(value: Any) -> Optional[str]:
    try:
        return str(uuid.UUID(str(value)))
    except (ValueError, TypeError, AttributeError):
        return None
