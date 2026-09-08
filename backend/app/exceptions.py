import logging
import traceback
from fastapi import Request, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

async def global_exception_handler(request: Request, exc: Exception):
    """
    Catch all unhandled exceptions and return a structured JSON response.
    Never return a raw stack trace to the client.
    """
    request_id = getattr(request.state, "request_id", "unknown")
    
    # Log the full stack trace server-side with correlation ID
    logger.error(
        f"Unhandled exception [request_id={request_id}]: {str(exc)}\n{traceback.format_exc()}"
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "code": "internal_error",
            "message": "An unexpected error occurred.",
            "retryable": True,
            "request_id": request_id
        }
    )
