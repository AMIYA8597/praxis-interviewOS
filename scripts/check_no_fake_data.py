"""
Phase 47 — No-fake-data gate.

Scans runtime source files (backend, realtime-agent, packages) for patterns
that would introduce fabricated scores, demo users, hardcoded metrics, or
mock tokens in production code paths.

Test fixtures (tests/, *_test.py, test_*.py, *.test.ts, *.test.tsx) are
intentionally excluded because mocks are allowed in automated tests.
"""
import os
import re
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

_SCAN_DIRS = ["backend", "packages"]
# realtime-agent/scripts/ contains dev tooling (not runtime); realtime-agent/realtime_agent/ is runtime
_REALTIME_RUNTIME = os.path.join(_ROOT, "realtime-agent", "realtime_agent")

_EXCLUDE_DIRS = {
    ".venv", "node_modules", ".git", "__pycache__",
    ".claude", "dist", "build", ".next",
}

_TEST_PATTERNS = re.compile(
    r"([\\/]tests?[\\/]|test_|_test\.(py|ts|tsx)|\.test\.(ts|tsx))", re.IGNORECASE
)

_FAKE_PATTERNS = [
    # Hardcoded numeric metrics presented as real
    (re.compile(r'\b(overall_score|accuracy|correctness|grounding)\s*=\s*0\.\d{1,2}\b'), "hardcoded numeric score"),
    # Demo / fake user UUIDs (the dev-bypass UUID is allowed only in settings.py)
    (re.compile(r'00000000-0000-0000-0000-000000000001'), "hardcoded non-dev-bypass UUID"),
    # Mock tokens in runtime (not test) code
    (re.compile(r'(?i)(mock[-_]token|fake[-_]token|test[-_]token)\s*=\s*["\'][^"\']+["\']'), "hardcoded mock token in runtime"),
    # "Demo" users
    (re.compile(r'(?i)demo[-_]user|fake[-_]user'), "demo/fake user reference"),
]

_ALLOWED_FILES = {
    # The dev bypass UUID is allowed only in these config files
    "packages/config/settings.py",
}


def should_skip(path: str) -> bool:
    rel = os.path.relpath(path, _ROOT).replace("\\", "/")
    if _TEST_PATTERNS.search(rel):
        return True
    parts = rel.split("/")
    if any(p in _EXCLUDE_DIRS for p in parts):
        return True
    return False


def scan() -> list[str]:
    violations: list[str] = []
    all_dirs = _SCAN_DIRS + [_REALTIME_RUNTIME]
    for scan_dir in all_dirs:
        abs_dir = os.path.join(_ROOT, scan_dir)
        if not os.path.isdir(abs_dir):
            continue
        for dirpath, dirnames, filenames in os.walk(abs_dir):
            dirnames[:] = [d for d in dirnames if d not in _EXCLUDE_DIRS]
            for filename in filenames:
                if not filename.endswith((".py", ".ts", ".tsx")):
                    continue
                filepath = os.path.join(dirpath, filename)
                if should_skip(filepath):
                    continue
                rel = os.path.relpath(filepath, _ROOT).replace("\\", "/")
                try:
                    with open(filepath, encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                except OSError:
                    continue
                lines_list = content.splitlines()
                for pattern, desc in _FAKE_PATTERNS:
                    for m in pattern.finditer(content):
                        lineno = content[: m.start()].count("\n") + 1
                        # Allow the dev-bypass UUID in settings.py
                        if "00000000" in m.group() and rel in _ALLOWED_FILES:
                            continue
                        # Allow legitimate LLM-failure fallback lines
                        line_text = lines_list[lineno - 1] if lineno <= len(lines_list) else ""
                        if "fallback" in line_text.lower() or "# scoring failed" in line_text.lower():
                            continue
                        violations.append(f"{rel}:{lineno}: [{desc}] {m.group()[:80]}")
    return violations


def main() -> None:
    violations = scan()
    if violations:
        print("FAIL — fake/hardcoded data found in runtime source:")
        for v in violations:
            print(f"  {v}")
        sys.exit(1)
    print("OK — no fake/hardcoded production data detected.")


if __name__ == "__main__":
    main()
