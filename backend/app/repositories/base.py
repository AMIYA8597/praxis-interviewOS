"""
Shared data-access helpers.

Keyset (cursor) pagination over (created_at DESC, id DESC). The cursor format
is "<iso8601 created_at>_<uuid id>", identical to what the API emitted before
this layer existed, so existing clients keep working.
"""
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Generic, List, Optional, Sequence, Tuple, TypeVar

from sqlalchemy import Select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.exceptions import BadRequestError

T = TypeVar("T")

DEFAULT_LIMIT = 20
MAX_LIMIT = 100


@dataclass
class Page(Generic[T]):
    items: List[T]
    next_cursor: Optional[str]


def encode_cursor(created_at: datetime, row_id: Any) -> str:
    return f"{created_at.isoformat()}_{row_id}"


def decode_cursor(cursor: str) -> Tuple[datetime, uuid.UUID]:
    try:
        ts_str, id_str = cursor.rsplit("_", 1)
        return datetime.fromisoformat(ts_str), uuid.UUID(id_str)
    except (ValueError, AttributeError):
        raise BadRequestError("Invalid cursor format", code="invalid_cursor")


async def paginate(
    db: AsyncSession,
    stmt: Select,
    model: Any,
    *,
    cursor: Optional[str],
    limit: int,
) -> Page:
    """Apply keyset pagination to `stmt` (which must select `model`)."""
    limit = max(1, min(int(limit or DEFAULT_LIMIT), MAX_LIMIT))
    if cursor:
        ts, row_id = decode_cursor(cursor)
        # Expanded form of (created_at, id) < (ts, id): portable across
        # Postgres and SQLite and still index-friendly.
        stmt = stmt.where(
            or_(
                model.created_at < ts,
                and_(model.created_at == ts, model.id < row_id),
            )
        )
    stmt = stmt.order_by(model.created_at.desc(), model.id.desc()).limit(limit + 1)
    rows: Sequence[Any] = (await db.execute(stmt)).scalars().all()
    items = list(rows[:limit])
    next_cursor = None
    if len(rows) > limit and items:
        last = items[-1]
        next_cursor = encode_cursor(last.created_at, last.id)
    return Page(items=items, next_cursor=next_cursor)


def as_uuid(value: Any) -> Optional[uuid.UUID]:
    """Parse ids from untrusted input; None when not a valid UUID."""
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (ValueError, AttributeError, TypeError):
        return None
