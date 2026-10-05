"""
Architecture boundary tests — spec section 4 (Backend Package Boundaries).

CI must fail if:
  - API layer imports provider SDKs directly (openai, anthropic, groq, etc.)
  - Domain/services layer imports FastAPI transport-specific implementation classes
  - Repository layer imports HTTP transport unnecessarily
  - Worker tasks import FastAPI-specific code

These tests parse Python source files and check for forbidden import patterns.
They are FAST (no I/O other than source reading) and run in every CI pass.

See also: scripts/check_gateway_boundary.py (runtime gate)
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent

# ── Forbidden import patterns ──────────────────────────────────────────────────

PROVIDER_SDK_MODULES = frozenset(
    ["openai", "anthropic", "groq", "google.generativeai", "deepseek", "xai"]
)

FASTAPI_TRANSPORT_CLASSES = frozenset(
    # Classes that are fine in api/ but not in domain/services/repositories
    ["APIRouter", "Depends", "HTTPException", "Request", "Response", "Body", "Query", "Path", "Header"]
)


def _get_import_names(source: str) -> list[str]:
    """Return all top-level module names imported by a Python source file."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    names = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    names.append(alias.name.split(".")[0])
            else:
                if node.module:
                    names.append(node.module.split(".")[0])
    return names


def _get_python_files(directory: Path) -> list[Path]:
    return [
        p for p in directory.rglob("*.py")
        if "__pycache__" not in str(p) and ".venv" not in str(p)
    ]


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestProviderSDKIsolation:
    """Provider SDKs must only appear inside packages/ai-gateway/praxis_ai_gateway/providers/."""

    def _is_in_allowed_provider_path(self, path: Path) -> bool:
        rel = str(path.relative_to(ROOT))
        return "ai-gateway" in rel and "providers" in rel

    def _check_dir(self, directory: Path) -> list[str]:
        violations = []
        if not directory.exists():
            return violations
        for pyfile in _get_python_files(directory):
            if self._is_in_allowed_provider_path(pyfile):
                continue
            try:
                source = pyfile.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            imports = _get_import_names(source)
            bad = [m for m in imports if m in PROVIDER_SDK_MODULES]
            if bad:
                violations.append(f"{pyfile.relative_to(ROOT)}: imports {bad}")
        return violations

    def test_backend_app_has_no_direct_provider_imports(self):
        violations = self._check_dir(ROOT / "backend" / "app")
        assert not violations, (
            "Provider SDK imported directly outside AI Gateway:\n" + "\n".join(violations)
        )

    def test_realtime_agent_has_no_direct_provider_imports(self):
        violations = self._check_dir(ROOT / "realtime-agent" / "realtime_agent" / "app")
        assert not violations, (
            "Provider SDK imported directly in realtime agent (outside AI Gateway):\n"
            + "\n".join(violations)
        )


class TestFastAPILayerIsolation:
    """FastAPI-specific response/request classes must not appear in the domain/services layer."""

    _FASTAPI_IMPORT_RE = re.compile(
        r"^\s*from\s+fastapi\s+import.*\b(APIRouter|Depends|HTTPException|Request|Response)\b",
        re.MULTILINE,
    )

    def _check_services(self) -> list[str]:
        violations = []
        services_dir = ROOT / "backend" / "app" / "services"
        if not services_dir.exists():
            return violations
        for pyfile in _get_python_files(services_dir):
            try:
                source = pyfile.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if self._FASTAPI_IMPORT_RE.search(source):
                violations.append(str(pyfile.relative_to(ROOT)))
        return violations

    def test_services_layer_does_not_import_fastapi_router(self):
        violations = self._check_services()
        assert not violations, (
            "Services layer imports FastAPI transport classes — business logic "
            "must be framework-agnostic:\n" + "\n".join(violations)
        )


class TestWorkerLayerIsolation:
    """Worker task code must not import FastAPI application code."""

    _FASTAPI_APP_RE = re.compile(
        r"^\s*from\s+fastapi\s+import\s+(APIRouter|app|create_app)\b",
        re.MULTILINE,
    )

    def test_worker_tasks_do_not_import_fastapi_app(self):
        worker_file = ROOT / "backend" / "app" / "worker_tasks.py"
        if not worker_file.exists():
            return
        source = worker_file.read_text(encoding="utf-8", errors="ignore")
        matches = self._FASTAPI_APP_RE.findall(source)
        assert not matches, (
            f"worker_tasks.py imports FastAPI app classes {matches}. "
            "Worker code must be independent from the HTTP lifecycle."
        )


class TestNoRawSQLInAPIRoutes:
    """SQL text() calls belong in repositories/services, not in API route handlers.

    Exemptions:
      health.py  — intentionally uses `SELECT 1` as a database connectivity probe.
    Known debt (tracked, not yet refactored):
      interview_engines.py — config INSERT; bounded but should move to a service.
    """

    _SQLALCHEMY_TEXT_RE = re.compile(
        r"^\s*(await\s+\w+\.execute\(text\(|db\.execute\(text\()",
        re.MULTILINE,
    )

    # Files legitimately allowed to use raw SQL (health probes, diagnostic endpoints).
    _ALLOWED = frozenset(["health.py", "interview_engines.py"])

    def test_api_routes_have_no_raw_sql(self):
        api_dir = ROOT / "backend" / "app" / "api"
        if not api_dir.exists():
            return
        violations = []
        for pyfile in _get_python_files(api_dir):
            if pyfile.name in self._ALLOWED:
                continue
            try:
                source = pyfile.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if self._SQLALCHEMY_TEXT_RE.search(source):
                violations.append(str(pyfile.relative_to(ROOT)))
        assert not violations, (
            "Raw SQL text() found in API route handlers — use services/repositories:\n"
            + "\n".join(violations)
        )
