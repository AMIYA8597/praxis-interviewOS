"""
Generic CRUD for tables that carry a `candidate_id` owner column.

Every read/update/delete filters on BOTH the primary key and candidate_id,
so a candidate can never observe or touch another candidate's row; a
foreign id is indistinguishable from a missing one (-> 404, no existence
oracle).
"""
from typing import Any, Dict, Optional, Type

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.repositories.base import Page, as_uuid, paginate


def _owned_filter(model: Type[Any], row_id: Any, candidate_id: Any):
    return (model.id == as_uuid(row_id), model.candidate_id == as_uuid(candidate_id))


async def get_owned(db: AsyncSession, model: Type[Any], row_id: Any, candidate_id: Any, *, extra=()) -> Optional[Any]:
    if as_uuid(row_id) is None or as_uuid(candidate_id) is None:
        return None
    stmt = select(model).where(*_owned_filter(model, row_id, candidate_id), *extra)
    return (await db.execute(stmt)).scalar_one_or_none()


async def list_owned(
    db: AsyncSession,
    model: Type[Any],
    candidate_id: Any,
    *,
    cursor: Optional[str],
    limit: int,
    extra=(),
) -> Page:
    owner = as_uuid(candidate_id)
    if owner is None:  # never degrade to `candidate_id IS NULL`
        return Page(items=[], next_cursor=None)
    stmt = select(model).where(model.candidate_id == owner, *extra)
    return await paginate(db, stmt, model, cursor=cursor, limit=limit)


async def create_owned(db: AsyncSession, model: Type[Any], candidate_id: Any, values: Dict[str, Any]) -> Any:
    obj = model(candidate_id=as_uuid(candidate_id), **values)
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def update_owned(
    db: AsyncSession, model: Type[Any], row_id: Any, candidate_id: Any, values: Dict[str, Any], *, extra=()
) -> Optional[Any]:
    if as_uuid(row_id) is None or as_uuid(candidate_id) is None:
        return None
    if values:
        stmt = (
            update(model)
            .where(*_owned_filter(model, row_id, candidate_id), *extra)
            .values(**values)
            .execution_options(synchronize_session=False)
        )
        result = await db.execute(stmt)
        if result.rowcount == 0:
            return None
    obj = await get_owned(db, model, row_id, candidate_id, extra=extra)
    if obj is not None:
        await db.refresh(obj)
    return obj


async def delete_owned(db: AsyncSession, model: Type[Any], row_id: Any, candidate_id: Any) -> bool:
    if as_uuid(row_id) is None or as_uuid(candidate_id) is None:
        return False
    result = await db.execute(delete(model).where(*_owned_filter(model, row_id, candidate_id)))
    return (result.rowcount or 0) > 0
