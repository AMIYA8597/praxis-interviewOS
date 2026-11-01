#!/usr/bin/env python3
"""
PRAXIS InterviewOS — Security Baseline Runner
Executes security configuration checks, secret scans, and automated security test suites.
"""
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def run_secret_scan():
    """Scans tracked repository source files for dangerous secret signatures."""
    print("Running Secret Leakage Scan...")
    secret_patterns = [
        re.compile(r"sk-proj-[A-Za-z0-9_-]{20,}"),
        re.compile(r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----"),
        re.compile(r"ghp_[A-Za-z0-9]{36}"),
        re.compile(r"AIzaSy[A-Za-z0-9_-]{33}"),
    ]

    findings = []
    # Ignore git, logs, artifacts, and node_modules
    ignored_dirs = {".git", ".system_generated", "node_modules", ".next", "dist", "__pycache__", ".venv"}

    for root, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in ignored_dirs]
        for file in files:
            if file.endswith((".py", ".ts", ".tsx", ".js", ".json", ".sql", ".tf", ".yaml", ".yml")):
                file_path = Path(root) / file
                # Skip test files and documentation that intentionally reference test/mock keys
                rel_str = str(file_path.relative_to(ROOT)).replace("\\", "/")
                if any(x in rel_str for x in ["test_", "conftest", "mock", "docs/"]):
                    continue
                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    for pat in secret_patterns:
                        if pat.search(content):
                            findings.append(f"{rel_str}: matched pattern {pat.pattern}")
                except Exception:
                    pass

    if findings:
        for f in findings:
            print(f"  [CRITICAL LEAK] Found potential secret in: {f}")
        return False, f"Found {len(findings)} potential secret(s)"
    return True, "Zero active hardcoded secrets found in production source"


def run_configuration_check():
    print("Running Security Configuration Checks...")
    res = subprocess.run([sys.executable, str(ROOT / "scripts" / "security" / "verify_security_configuration.py")], capture_output=True, text=True)
    if res.returncode == 0:
        return True, "Security configurations passed"
    return False, res.stdout or res.stderr


def run_security_tests():
    print("Running Automated Security Test Suite...")
    test_dir = str(ROOT / "backend" / "tests" / "security")
    res = subprocess.run([sys.executable, "-m", "pytest", test_dir, "-q"], capture_output=True, text=True, cwd=str(ROOT))
    if res.returncode == 0:
        return True, res.stdout.strip().splitlines()[-1] if res.stdout else "Tests passed"
    return False, res.stdout or res.stderr


def main():
    print("=" * 64)
    print("  PRAXIS SECURITY BASELINE & SUITE RUNNER")
    print("=" * 64)

    steps = [
        ("Secret Leakage Scan", run_secret_scan),
        ("Security Configuration Verifier", run_configuration_check),
        ("Security Regression Tests", run_security_tests),
    ]

    all_passed = True
    for name, fn in steps:
        ok, msg = fn()
        status_str = "[PASS]" if ok else "[FAIL]"
        print(f"  {status_str} {name}: {msg}")
        if not ok:
            all_passed = False

    print("-" * 64)
    if all_passed:
        print("  [SUCCESS] All security baseline checks passed.")
        sys.exit(0)
    else:
        print("  [FAILURE] One or more security baseline checks failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
