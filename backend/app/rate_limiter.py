import time
import jwt
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from packages.config.settings import settings

# Per-route limits: (tokens_per_minute, burst)
# Default is (60, 20)
ROUTE_LIMITS = {
    "/api/v1/auth/signup": (5, 5),
    "/api/v1/resumes": (10, 5),
    "/api/v1/jobs/analyze": (10, 5),
    "/api/v1/health": (120, 60),
}

class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if settings.LOCAL_ONLY_MODE and not getattr(settings, "ENABLE_RATE_LIMIT", True):
            return await call_next(request)
            
        redis = getattr(request.app.state, "redis_pool", None)
        if not redis:
            return await call_next(request)

        # 1. Resolve scope + identifier
        identifier = request.client.host if request.client else "unknown"
        
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            try:
                # We decode WITHOUT verification here ONLY to extract the user ID for rate limiting.
                # True cryptographic verification happens in the `get_current_user` dependency.
                payload = jwt.decode(token, options={"verify_signature": False})
                if "sub" in payload:
                    identifier = payload["sub"]
            except Exception:
                pass # Fall back to IP if token is malformed

        # 2. Determine per-route limit
        path = request.url.path
        limit_rpm = 60
        
        for prefix, (rpm, burst) in ROUTE_LIMITS.items():
            if path.startswith(prefix):
                limit_rpm = rpm
                break

        # 3. Check/increment Token Bucket in Redis via Lua Script
        # Key: ratelimit:{identifier}:{path} or just ratelimit:{identifier}
        # Let's do global per-user limiting, but we can do it per-endpoint if we want.
        # Actually, global per-user with different costs per route is better, 
        # but the spec says "Apply stricter limits to expensive routes".
        # We will track rate limit per identifier per minute window using simple counters for simplicity and speed.
        
        current_minute = int(time.time() / 60)
        key = f"ratelimit:{identifier}:{current_minute}"
        
        try:
            # Increment and set TTL pipeline
            pipe = redis.pipeline()
            pipe.incr(key)
            pipe.expire(key, 120)
            result = await pipe.execute()
            
            count = result[0]
            if count > limit_rpm:
                return JSONResponse(
                    status_code=429,
                    content={"code": "rate_limit_exceeded", "message": "Too many requests"},
                    headers={"Retry-After": "60"}
                )
        except Exception:
            # Fail open if Redis is unreachable during rate check
            pass

        return await call_next(request)
