from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from backend.app.dependencies import require_admin, get_db_session, get_ai_gateway

router = APIRouter(tags=["admin"])

class BanRequest(BaseModel):
    user_id: str
    reason: str

@router.get("/admin/users")
async def list_users(
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session)
):
    query = text("SELECT id, profile_id, current_company, created_at FROM candidates")
    res = await db.execute(query)
    return {"users": [dict(r._mapping) for r in res.fetchall()]}

@router.get("/admin/providers")
async def get_admin_providers(
    admin: dict = Depends(require_admin),
    gateway = Depends(get_ai_gateway)
):
    # Reuse Part 3's logic
    from backend.app.api.health import providers_check
    return await providers_check(gateway)

@router.get("/admin/audit-logs")
async def get_audit_logs(
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session)
):
    # Depending on schema, fetch from an audit log table
    return {"logs": []}

@router.post("/admin/users/ban")
async def ban_user(
    req: BanRequest, 
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session)
):
    # Set banned status in profiles (hypothetical)
    query = text("UPDATE profiles SET is_banned = true WHERE id = :uid")
    await db.execute(query, {"uid": req.user_id})
    await db.commit()
    return {"status": "banned", "user_id": req.user_id, "reason": req.reason}
