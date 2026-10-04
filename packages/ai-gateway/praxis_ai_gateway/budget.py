from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional
from datetime import datetime, timezone

class ConsentRequiredError(Exception):
    pass

class BudgetExceededError(Exception):
    pass

class BudgetGuard:
    def __init__(self, redis: Redis, db: AsyncSession):
        self.redis = redis
        self.db = db
        # Defaults, could be overridden by user_settings
        self.default_daily_cap = 5.00
        self.default_session_cap = 1.00

    async def check_consent(self, user_id: str):
        """Paid providers require prior paid usage or explicit acknowledgement.

        Fails closed: if consent cannot be established (no DB, unknown user,
        missing column) the paid provider is skipped and the router falls
        back to the next (free) candidate.
        """
        profile_id = str(user_id)
        if self.db is None:
            raise ConsentRequiredError("First use of a paid provider requires explicit consent.")
        try:
            result = await self.db.execute(text("""
                SELECT EXISTS(
                    SELECT 1 FROM usage_events
                    WHERE profile_id = CAST(:uid AS uuid) AND was_free_tier = false
                )
            """), {"uid": profile_id})
            if result.scalar():
                return
            res2 = await self.db.execute(text("""
                SELECT 1 FROM profiles
                WHERE id = CAST(:uid AS uuid) AND paid_provider_acknowledged = true
            """), {"uid": profile_id})
            if res2.scalar():
                return
        except Exception:
            pass
        raise ConsentRequiredError("First use of a paid provider requires explicit consent.")

    async def check_and_reserve(self, user_id: str, session_id: Optional[str], estimated_cost: float):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        daily_key = f"budget:daily:{user_id}:{today}"
        
        # Check daily
        daily_spend = float(await self.redis.get(daily_key) or 0.0)
        if daily_spend + estimated_cost > self.default_daily_cap:
            raise BudgetExceededError(f"Daily budget cap of ${self.default_daily_cap:.2f} exceeded.")
            
        # Check session
        if session_id:
            session_key = f"budget:session:{session_id}"
            session_spend = float(await self.redis.get(session_key) or 0.0)
            if session_spend + estimated_cost > self.default_session_cap:
                raise BudgetExceededError(f"Session budget cap of ${self.default_session_cap:.2f} exceeded.")

    async def commit_spend(self, user_id: str, session_id: Optional[str], actual_cost: float):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        daily_key = f"budget:daily:{user_id}:{today}"
        await self.redis.incrbyfloat(daily_key, actual_cost)
        await self.redis.expire(daily_key, 86400) # 24h
        
        if session_id:
            session_key = f"budget:session:{session_id}"
            await self.redis.incrbyfloat(session_key, actual_cost)
            await self.redis.expire(session_key, 86400)
