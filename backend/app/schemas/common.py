from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    next_cursor: Optional[str] = None


class StatusResponse(BaseModel):
    status: str
    id: Optional[str] = None
    message: Optional[str] = None


class ErrorResponse(BaseModel):
    """Documented error envelope (see backend.app.exceptions)."""

    code: str
    message: str
    detail: Optional[object] = None
    retryable: bool = False
    request_id: str


# Attach to routers so OpenAPI documents the shared error envelope.
COMMON_ERROR_RESPONSES = {
    400: {"model": ErrorResponse},
    401: {"model": ErrorResponse},
    403: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    422: {"model": ErrorResponse},
    500: {"model": ErrorResponse},
}
