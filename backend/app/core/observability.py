"""
Phase 110 — Observability.

Structured logging, OpenTelemetry tracing, and request correlation.
All log records include: request_id, session_id, candidate_id, job_id.
No PII (tokens, passwords, audio content, raw resume text) is logged.
"""
import json
import logging
import time
import uuid
from contextvars import ContextVar
from typing import Optional

# ── Correlation context vars ──────────────────────────────────────────────────
_request_id: ContextVar[str] = ContextVar("request_id", default="")
_session_id: ContextVar[str] = ContextVar("session_id", default="")
_candidate_id: ContextVar[str] = ContextVar("candidate_id", default="")
_job_id: ContextVar[str] = ContextVar("job_id", default="")


def set_request_context(
    request_id: Optional[str] = None,
    session_id: Optional[str] = None,
    candidate_id: Optional[str] = None,
    job_id: Optional[str] = None,
) -> None:
    if request_id:
        _request_id.set(request_id)
    if session_id:
        _session_id.set(session_id)
    if candidate_id:
        _candidate_id.set(candidate_id)
    if job_id:
        _job_id.set(job_id)


def get_request_id() -> str:
    return _request_id.get() or str(uuid.uuid4())


# ── JSON log formatter ────────────────────────────────────────────────────────

class StructuredLogFormatter(logging.Formatter):
    """Emits JSON log records compatible with Cloud Logging."""

    _SEVERITY_MAP = {
        logging.DEBUG: "DEBUG",
        logging.INFO: "INFO",
        logging.WARNING: "WARNING",
        logging.ERROR: "ERROR",
        logging.CRITICAL: "CRITICAL",
    }

    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            "severity": self._SEVERITY_MAP.get(record.levelno, "DEFAULT"),
            "message": record.getMessage(),
            "logger": record.name,
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S.%fZ"),
            "request_id": _request_id.get() or "",
            "session_id": _session_id.get() or "",
            "candidate_id": _candidate_id.get() or "",
            "job_id": _job_id.get() or "",
        }

        # Merge extra fields attached via logger.info("event", extra={...})
        for key, value in record.__dict__.items():
            if key not in (
                "msg", "args", "levelname", "levelno", "name", "pathname",
                "filename", "module", "funcName", "lineno", "created", "msecs",
                "relativeCreated", "thread", "threadName", "process",
                "processName", "exc_info", "exc_text", "stack_info", "message",
            ):
                payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


def configure_logging(log_level: str = "INFO", log_format: str = "json") -> None:
    """Configure root logger. Call once at application startup."""
    root = logging.getLogger()
    root.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    if not root.handlers:
        handler = logging.StreamHandler()
        if log_format == "json":
            handler.setFormatter(StructuredLogFormatter())
        else:
            handler.setFormatter(logging.Formatter(
                "%(asctime)s %(levelname)s %(name)s [req=%(request_id)s] %(message)s"
            ))
        root.addHandler(handler)


# ── FastAPI middleware ─────────────────────────────────────────────────────────

async def request_id_middleware(request, call_next):
    """FastAPI middleware: inject request_id into context and response header."""
    req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    _request_id.set(req_id)
    start = time.monotonic()
    response = await call_next(request)
    duration_ms = (time.monotonic() - start) * 1000
    response.headers["X-Request-ID"] = req_id
    response.headers["X-Response-Time-Ms"] = f"{duration_ms:.1f}"
    return response
