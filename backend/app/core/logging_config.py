"""
Structured logging for the backend, worker and realtime agent.

* Every record gets request_id / user_id / candidate_id / session_id from the
  current context (see backend.app.core.context).
* `extra={...}` fields are emitted as top-level JSON keys.
* Sensitive keys (tokens, passwords, raw resume text, ...) are redacted
  defensively even if a caller passes them by mistake.
"""
import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict

from backend.app.core.context import snapshot

_STD_ATTRS = set(
    logging.LogRecord("x", logging.INFO, "x", 0, "x", None, None).__dict__.keys()
) | {"message", "asctime", "request_id", "trace_id", "user_id", "candidate_id", "session_id"}

SENSITIVE_KEYS = {
    "token", "access_token", "refresh_token", "authorization", "jwt", "password",
    "secret", "api_key", "apikey", "service_role_key", "raw_text", "resume_text",
    "content", "file_bytes", "image_base64", "email", "user_email", "phone",
    "phone_number", "ssn", "credit_card",
}


def _redact(key: str, value: Any) -> Any:
    k = key.lower()
    if (
        k in SENSITIVE_KEYS
        or k.endswith("_token")
        or k.endswith("_secret")
        or k.endswith("_password")
        or k.endswith("_email")
        or k.endswith("_key")
        or "password" in k
        or "secret" in k
    ):
        if isinstance(value, (str, bytes)):
            return f"<redacted len={len(value)}>"
        return "<redacted>"
    if isinstance(value, dict):
        return {k_: _redact(k_, v_) for k_, v_ in value.items()}
    if isinstance(value, list):
        return [_redact(key, item) if isinstance(item, (dict, list)) else item for item in value]
    return value


class ContextFilter(logging.Filter):
    """Injects correlation identifiers into every record."""

    def filter(self, record: logging.LogRecord) -> bool:
        for key, value in snapshot().items():
            if not hasattr(record, key) or getattr(record, key) in (None, "-"):
                setattr(record, key, value)
        return True


# Backwards-compatible name used by older code.
RequestIdFilter = ContextFilter


class StructuredFormatter(logging.Formatter):
    def __init__(self, service: str = "praxis-backend"):
        super().__init__()
        self.service = service

    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": self.service,
        }
        for key in ("request_id", "trace_id", "user_id", "candidate_id", "session_id"):
            value = getattr(record, key, None)
            if value not in (None, "-"):
                log_data[key] = value

        if "trace_id" not in log_data:
            try:
                from opentelemetry import trace
                span = trace.get_current_span()
                if span and span.get_span_context().is_valid:
                    log_data["trace_id"] = format(span.get_span_context().trace_id, "032x")
            except Exception:
                pass
        for key, value in record.__dict__.items():
            if key not in _STD_ATTRS and not key.startswith("_"):
                log_data[key] = _redact(key, value)
        if record.exc_info:
            log_data["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(log_data, default=str)


class TextFormatter(logging.Formatter):
    def __init__(self):
        super().__init__(
            "%(asctime)s %(levelname)s %(name)s [req=%(request_id)s cand=%(candidate_id)s sess=%(session_id)s] %(message)s"
        )

    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)
        extras = {
            k: _redact(k, v)
            for k, v in record.__dict__.items()
            if k not in _STD_ATTRS and not k.startswith("_")
        }
        if extras:
            base += " " + " ".join(f"{k}={v}" for k, v in extras.items())
        return base


_configured = False


def setup_structured_logging(
    service: str = "praxis-backend", level: str = "INFO", fmt: str = "json", force: bool = False
) -> None:
    """Configure the root logger once per process."""
    global _configured
    if _configured and not force:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredFormatter(service) if fmt == "json" else TextFormatter())
    handler.addFilter(ContextFilter())

    root = logging.getLogger()
    # Replace only handlers we own; keep pytest's capture handlers intact.
    for h in list(root.handlers):
        if getattr(h, "_praxis", False):
            root.removeHandler(h)
    handler._praxis = True  # type: ignore[attr-defined]
    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    for noisy in ("uvicorn.access",):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    _configured = True
