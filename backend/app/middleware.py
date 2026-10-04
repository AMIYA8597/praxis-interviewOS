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
    user_id_ctx,
)

logger = logging.getLogger("praxis.http")

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
        tokens = [
            (request_id_ctx, request_id_ctx.set(request_id)),
            (user_id_ctx, user_id_ctx.set(None)),
            (candidate_id_ctx, candidate_id_ctx.set(None)),
            (session_id_ctx, session_id_ctx.set(None)),
        ]
        request.state.request_id = request_id
        started = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Request-ID"] = request_id
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
            for key in ("user_id", "candidate_id"):
                value = getattr(request.state, key, None)
                if value:
                    extra[key] = str(value)
            if not request.url.path.endswith("/health/live"):
                level = logging.WARNING if status_code >= 500 else logging.INFO
                logger.log(level, "request_completed", extra=extra)
            for var, token in reversed(tokens):
                var.reset(token)
