"""Use this checkout's sources (not a stale editable install) for realtime tests."""
import os
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
for _rel in ("realtime-agent", os.path.join("packages", "ai-gateway"), ""):
    _p = os.path.join(_ROOT, _rel) if _rel else _ROOT
    if _p in sys.path:
        sys.path.remove(_p)
    sys.path.insert(0, _p)
os.environ.setdefault("OTEL_SDK_DISABLED", "true")
