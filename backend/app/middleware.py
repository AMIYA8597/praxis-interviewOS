import logging
import re
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from backend.app.core.context import (
    candidate_id_ctx,
    request_id_ctx,
    session_id_ctx,
    trace_id_ctx,
    user_id_ctx,
)

logger = logging.getLogger("praxis.http")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds OWASP-recommended security headers to every response.

    HSTS is only set in production (HTTP in dev would lock out local debugging).
    No CSP here — this API returns JSON; the frontend owns its own CSP.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        # X-XSS-Protection: 0 is the modern recommendation (disables legacy filter that itself caused XSS)
        response.headers.setdefault("X-XSS-Protection", "0")
        # Prevent caching of authenticated API responses that may contain PII
        path = request.url.path
        if not (path.endswith("/health/live") or path.endswith("/health/ready") or path == "/api/v1/health"):
            response.headers.setdefault("Cache-Control", "no-store")
            response.headers.setdefault("Pragma", "no-cache")
        # HSTS only makes sense over real HTTPS; omit it in dev to avoid locking out HTTP.
        from packages.config.settings import Settings
        try:
            env = request.app.state.__dict__.get("settings_app_env") or Settings().APP_ENV
        except Exception:
            env = "development"
        if env in ("staging", "production"):
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=63072000; includeSubDomains",
            )
        return response


class RequestBodyLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests with bodies exceeding a size limit (defense-in-depth behind Cloud Armor)."""

    MAX_BODY_BYTES = 10 * 1024 * 1024  # 10 MB

    async def dispatch(self, request: Request, call_next) -> Response:
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.MAX_BODY_BYTES:
            return Response(
                content='{"detail":"Request body too large"}',
                status_code=413,
                media_type="application/json",
            )
        return await call_next(request)


# Accept client-supplied ids only if they look like a sane token; otherwise
# generate our own so log lines cannot be forged/injected via the header.
_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._:\-]{8,128}$")


def _resolve_request_id(raw: str | None) -> str:
    if raw and _REQUEST_ID_RE.match(raw):
        return raw
    return str(uuid.uuid4())


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Assigns a request id, binds correlation context and logs one access line per request."""

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = _resolve_request_id(request.headers.get("X-Request-ID"))
        trace_id = request.headers.get("X-Trace-ID")
        if not trace_id:
            traceparent = request.headers.get("traceparent")
            if traceparent and len(traceparent.split("-")) >= 3:
                trace_id = traceparent.split("-")[1]

        tokens = [
            (request_id_ctx, request_id_ctx.set(request_id)),
            (trace_id_ctx, trace_id_ctx.set(trace_id)),
            (user_id_ctx, user_id_ctx.set(None)),
            (candidate_id_ctx, candidate_id_ctx.set(None)),
            (session_id_ctx, session_id_ctx.set(None)),
        ]
        request.state.request_id = request_id
        if trace_id:
            request.state.trace_id = trace_id
        started = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Request-ID"] = request_id
            if trace_id:
                response.headers["X-Trace-ID"] = trace_id
            return response
        finally:
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            # Auth dependencies stash identifiers on request.state because
            # context set inside the endpoint task is not visible here.
            extra = {
                "http_method": request.method,
                "http_path": request.url.path,
                "http_status": status_code,
                "duration_ms": duration_ms,
            }
            for key in ("user_id", "candidate_id", "session_id", "trace_id"):
                value = getattr(request.state, key, None)
                if value:
                    extra[key] = str(value)
            if not request.url.path.endswith("/health/live"):
                level = logging.WARNING if status_code >= 500 else logging.INFO
                logger.log(level, "request_completed", extra=extra)
            for var, token in reversed(tokens):
                var.reset(token)
