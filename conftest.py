"""
Repository-wide pytest bootstrap.

Guarantees the in-repo sources are imported (not a stale editable install that
may point at a different checkout/worktree). CI also installs these packages
in editable mode from the same paths, so this is a no-op there.
"""
import os
import sys

_ROOT = os.path.dirname(os.path.abspath(__file__))

for _rel in ("realtime-agent", os.path.join("packages", "ai-gateway"), ""):
    _path = os.path.join(_ROOT, _rel) if _rel else _ROOT
    if _path in sys.path:
        sys.path.remove(_path)
    sys.path.insert(0, _path)

# Tests must never try to ship spans to a collector that is not running.
os.environ.setdefault("OTEL_SDK_DISABLED", "true")
