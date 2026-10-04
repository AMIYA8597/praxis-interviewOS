"""
Standard error model for the PRAXIS API.

Every error response has the same JSON envelope:

    {
      "code": "not_found",            # stable, machine-readable
      "message": "Resume not found",  # human readable
      "detail": "Resume not found",   # legacy alias read by existing clients
      "retryable": false,
      "request_id": "…",
      "errors": [...]                 # only for request validation failures
    }

Services raise `AppError` subclasses; route handlers never build error
responses by hand.
"""
import logging
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class AppError(HTTPException):
    """
    Base class for expected, client-visible errors.

    Subclasses HTTPException so existing callers/tests that catch
    HTTPException keep working; FastAPI resolves handlers by MRO, so the
    dedicated AppError handler below still formats the response.
    """

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    code: str = "internal_error"
    retryable: bool = False

    def __init__(
        self,
        message: Optional[str] = None,
        *,
        code: Optional[str] = None,
        status_code: Optional[int] = None,
        retryable: Optional[bool] = None,
        headers: Optional[Dict[str, str]] = None,
    ):
        self.message = message or self.default_message()
        if code:
            self.code = code
        if retryable is not None:
            self.retryable = retryable
        super().__init__(
            status_code=status_code or type(self).status_code,
            detail=self.message,
            headers=headers,
        )

    def default_message(self) -> str:
        return "An unexpected error occurred."


class BadRequestError(AppError):
    status_code = status.HTTP_400_BAD_REQUEST
    code = "bad_request"

    def default_message(self) -> str:
        return "The request is invalid."


class UnauthorizedError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "unauthorized"

    def __init__(self, message: str = "Invalid or expired session", **kw):
        kw.setdefault("headers", {"WWW-Authenticate": "Bearer"})
        super().__init__(message, **kw)


class ForbiddenError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "forbidden"

    def default_message(self) -> str:
        return "You do not have access to this resource."


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "not_found"

    def __init__(self, resource: str = "Resource", message: Optional[str] = None, **kw):
        super().__init__(message or f"{resource} not found", **kw)


class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT
    code = "conflict"

    def default_message(self) -> str:
        return "The resource is in a conflicting state."


class PayloadTooLargeError(AppError):
    status_code = 413
    code = "payload_too_large"

    def default_message(self) -> str:
        return "The uploaded payload is too large."


class UnsupportedMediaTypeError(AppError):
    # Kept as 400 for client compatibility (existing clients treat any 4xx
    # upload failure the same way, and the contract specifies 400).
    status_code = status.HTTP_400_BAD_REQUEST
    code = "unsupported_file_type"

    def default_message(self) -> str:
        return "Unsupported file type."


class ServiceUnavailableError(AppError):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    code = "service_unavailable"
    retryable = True

    def default_message(self) -> str:
        return "A required service is temporarily unavailable."


_STATUS_CODES = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    413: "payload_too_large",
    415: "unsupported_media_type",
    422: "validation_error",
    429: "rate_limit_exceeded",
    503: "service_unavailable",
}


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", None) or "unknown"


def error_body(
    request: Request,
    *,
    code: str,
    message: str,
    retryable: bool = False,
    errors: Optional[List[Any]] = None,
    detail: Any = None,
) -> Dict[str, Any]:
    body: Dict[str, Any] = {
        "code": code,
        "message": message,
        "detail": detail if detail is not None else message,
        "retryable": retryable,
        "request_id": _request_id(request),
    }
    if errors is not None:
        body["errors"] = errors
    return body


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    if exc.status_code >= 500:
        logger.error("app_error", extra={"error_code": exc.code, "error_message": exc.message})
    return JSONResponse(
        status_code=exc.status_code,
        content=error_body(request, code=exc.code, message=exc.message, retryable=exc.retryable),
        headers=exc.headers,
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    detail = exc.detail
    if isinstance(detail, dict):
        # Structured detail (e.g. readiness probe payload): keep it verbatim.
        code = str(detail.get("code") or _STATUS_CODES.get(exc.status_code, "error"))
        message = str(detail.get("message") or detail.get("status") or code)
    else:
        code = _STATUS_CODES.get(exc.status_code, "error")
        message = str(detail) if detail else code
    return JSONResponse(
        status_code=exc.status_code,
        content=error_body(
            request,
            code=code,
            message=message,
            retryable=exc.status_code in (429, 502, 503, 504),
            detail=detail,
        ),
        headers=getattr(exc, "headers", None),
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = []
    for err in exc.errors():
        # Never echo submitted values back (could contain secrets/PII).
        errors.append({"loc": list(err.get("loc", [])), "msg": err.get("msg"), "type": err.get("type")})
    return JSONResponse(
        status_code=422,
        content=error_body(request, code="validation_error", message="Request validation failed", errors=errors),
    )


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Catch all unhandled exceptions and return a structured JSON response.
    Never return a raw stack trace (or exception text) to the client.
    """
    logger.error(
        "unhandled_exception",
        exc_info=(type(exc), exc, exc.__traceback__),
        extra={"exception_type": type(exc).__name__, "http_path": request.url.path},
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_body(request, code="internal_error", message="An unexpected error occurred.", retryable=True),
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, global_exception_handler)
