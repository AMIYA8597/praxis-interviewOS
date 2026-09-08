import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI, Depends, HTTPException
from fastapi.testclient import TestClient

from backend.app.dependencies import require_admin
from sqlalchemy.ext.asyncio import AsyncSession

app = FastAPI()

# A mock router using the dependency
@app.get("/admin/test", dependencies=[Depends(require_admin)])
async def admin_route():
    return {"message": "Admin access granted"}

@pytest.mark.asyncio
async def test_require_admin_blocks_non_admin():
    mock_db = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    # Return (False,) simulating a profile where is_admin = False
    mock_result.fetchone.return_value = (False,)
    mock_db.execute.return_value = mock_result
    
    from backend.app.dependencies import require_admin
    
    with pytest.raises(HTTPException) as exc:
        await require_admin(user={"sub": "user_123"}, db=mock_db)
        
    assert exc.value.status_code == 403
    assert exc.value.detail == "Insufficient permissions"

@pytest.mark.asyncio
async def test_require_admin_allows_admin():
    mock_db = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    # Return (True,) simulating a profile where is_admin = True
    mock_result.fetchone.return_value = (True,)
    mock_db.execute.return_value = mock_result
    
    from backend.app.dependencies import require_admin
    user = {"sub": "admin_456"}
    
    result = await require_admin(user=user, db=mock_db)
    assert result == user
