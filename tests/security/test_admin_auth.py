import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.dependencies import require_admin


def _db_returning(row):
    mock_db = AsyncMock(spec=AsyncSession)
    result = MagicMock()
    result.first.return_value = row
    result.fetchone.return_value = row
    mock_db.execute.return_value = result
    return mock_db


@pytest.mark.asyncio
async def test_require_admin_blocks_non_admin():
    with pytest.raises(HTTPException) as exc:
        await require_admin(current_user={"sub": str(uuid.uuid4())}, db=_db_returning(None))
    assert exc.value.status_code == 403
    assert exc.value.detail == "Admin access required"


@pytest.mark.asyncio
async def test_require_admin_allows_admin():
    user = {"sub": str(uuid.uuid4())}
    result = await require_admin(current_user=user, db=_db_returning((uuid.uuid4(),)))
    assert result == user


@pytest.mark.asyncio
async def test_require_admin_rejects_non_uuid_subject_without_querying():
    db = _db_returning((uuid.uuid4(),))
    with pytest.raises(HTTPException) as exc:
        await require_admin(current_user={"sub": "admin_456"}, db=db)
    assert exc.value.status_code == 403
    db.execute.assert_not_called()
