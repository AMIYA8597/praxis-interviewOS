"""Put this checkout's sources first on sys.path (see /conftest.py for rationale)."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
for _rel in ("realtime-agent", os.path.join("packages", "ai-gateway"), ""):
    _p = os.path.join(ROOT, _rel) if _rel else ROOT
    if _p in sys.path:
        sys.path.remove(_p)
    sys.path.insert(0, _p)
for _mod in [m for m in sys.modules if m == "praxis_ai_gateway" or m.startswith("praxis_ai_gateway.")]:
    _f = getattr(sys.modules[_mod], "__file__", "") or ""
    if not os.path.abspath(_f).startswith(ROOT):
        del sys.modules[_mod]
os.environ.setdefault("OTEL_SDK_DISABLED", "true")
os.environ.setdefault("ENABLE_RATE_LIMIT", "false")
