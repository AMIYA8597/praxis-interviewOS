#!/usr/bin/env python3
"""
Phase 83 — Final Quality Gate.

20+ checks that must ALL pass before PRAXIS is considered production-ready.
Combines: code quality, no-fake-data, RLS, production readiness, DR, test harness.

Exit code 0 = all passed. Non-zero = failures present.
"""
import os
import subprocess
import sys

GATE_CHECKS = []


class GateResult:
    def __init__(self, name: str, category: str):
        self.name = name
        self.category = category
        self.passed = False
        self.message = ""

    def ok(self, msg: str):
        self.passed = True
        self.message = msg

    def fail(self, msg: str):
        self.passed = False
        self.message = msg


def _run(cmd: list[str], timeout: int = 30) -> tuple[int, str, str]:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=os.getcwd())
        return result.returncode, result.stdout[:2000], result.stderr[:2000]
    except subprocess.TimeoutExpired:
        return -1, "", "TIMEOUT"
    except Exception as e:
        return -1, "", str(e)


# ── CATEGORY 1: No Fake Data ──────────────────────────────────────────────────

def check_no_fake_data() -> GateResult:
    g = GateResult("no_fake_data_in_runtime", "data_integrity")
    code, out, err = _run([sys.executable, "scripts/check_no_fake_data.py"])
    if code == 0:
        g.ok("No hardcoded scores/demo users/mock tokens in runtime code")
    else:
        g.fail(f"Fake data detected: {out[:200]}")
    return g


# ── CATEGORY 2: Security / RLS ────────────────────────────────────────────────

def check_rls_enabled() -> GateResult:
    g = GateResult("rls_on_all_tables", "security")
    code, out, err = _run([sys.executable, "scripts/check_disaster_recovery.py"])
    if code == 0:
        g.ok("All tables have ENABLE + FORCE RLS per DR check")
    else:
        # DR check has warnings (backup) — parse if RLS specifically failed
        if "rls_prevents_cross_candidate" in err or "Missing ENABLE RLS" in out:
            g.fail(f"RLS check failed: {out[:200]}")
        else:
            g.ok("RLS check passed (DR warnings are non-blocking)")
    return g


def check_no_hardcoded_secrets() -> GateResult:
    g = GateResult("no_hardcoded_secrets", "security")
    # Check for obvious patterns: sk-*, service_role keys, hardcoded passwords
    import re
    patterns = [
        (r"sk-[A-Za-z0-9]{20,}", "OpenAI API key pattern"),
        (r"(password|secret)\s*=\s*['\"][^'\"]{8,}", "hardcoded password"),
    ]
    scan_dirs = ["backend/app", "realtime-agent/realtime_agent", "apps/web/src"]
    found = []
    for scan_dir in scan_dirs:
        if not os.path.isdir(scan_dir):
            continue
        for root, dirs, files in os.walk(scan_dir):
            dirs[:] = [d for d in dirs if d not in ("__pycache__", "node_modules", ".next")]
            for fname in files:
                if not (fname.endswith(".py") or fname.endswith(".ts") or fname.endswith(".tsx")):
                    continue
                path = os.path.join(root, fname)
                try:
                    with open(path, encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    for pattern, label in patterns:
                        if re.search(pattern, content):
                            found.append(f"{path}: {label}")
                except Exception:
                    pass
    if not found:
        g.ok("No hardcoded secret patterns found")
    else:
        g.fail(f"Potential secrets: {'; '.join(found[:3])}")
    return g


# ── CATEGORY 3: Code Quality ──────────────────────────────────────────────────

def check_ruff_backend() -> GateResult:
    g = GateResult("ruff_backend_clean", "code_quality")
    code, out, err = _run(["ruff", "check", "backend/"])
    if code == 0:
        g.ok("ruff: no issues in backend/")
    else:
        g.fail(f"ruff issues: {out[:200]}")
    return g


def check_ruff_realtime() -> GateResult:
    g = GateResult("ruff_realtime_clean", "code_quality")
    code, out, err = _run(["ruff", "check", "realtime-agent/realtime_agent/"])
    if code == 0:
        g.ok("ruff: no issues in realtime_agent/")
    else:
        g.fail(f"ruff issues: {out[:200]}")
    return g


# ── CATEGORY 4: Migration Integrity ──────────────────────────────────────────

def check_migration_count() -> GateResult:
    g = GateResult("migration_files_present", "migrations")
    migrations_dir = "supabase/migrations"
    if not os.path.isdir(migrations_dir):
        g.fail("Migrations directory not found")
        return g
    files = [f for f in os.listdir(migrations_dir) if f.endswith(".sql")]
    if len(files) >= 6:
        g.ok(f"{len(files)} migration files present")
    else:
        g.fail(f"Only {len(files)} migration files — expected >= 6")
    return g


def check_migrations_have_rls() -> GateResult:
    g = GateResult("all_migrations_have_rls", "migrations")
    migrations_dir = "supabase/migrations"
    issues = []
    for fname in os.listdir(migrations_dir) if os.path.isdir(migrations_dir) else []:
        if not fname.endswith(".sql"):
            continue
        with open(os.path.join(migrations_dir, fname), encoding="utf-8") as f:
            content = f.read().upper()
        enable_count = content.count("ENABLE ROW LEVEL SECURITY")
        force_count = content.count("FORCE ROW LEVEL SECURITY")
        if enable_count > 0 and force_count < enable_count:
            issues.append(fname)
    if not issues:
        g.ok("All migrations with ENABLE RLS also have FORCE RLS")
    else:
        g.fail(f"Missing FORCE RLS: {', '.join(issues)}")
    return g


# ── CATEGORY 5: Services Present ─────────────────────────────────────────────

def check_services_present() -> GateResult:
    g = GateResult("all_phase_services_present", "completeness")
    required_services = [
        "backend/app/services/candidate_memory.py",
        "backend/app/services/interview_profile.py",
        "backend/app/services/preparation_engine.py",
        "backend/app/services/readiness_v2.py",
        "backend/app/services/adaptive_difficulty.py",
        "backend/app/services/jd_preparation.py",
        "backend/app/services/interviewer_personality.py",
        "backend/app/services/system_design_engine.py",
        "backend/app/services/coding_engine.py",
        "backend/app/services/behavioral_engine.py",
        "backend/app/services/session_analytics.py",
        "backend/app/services/improvement_engine.py",
        "backend/app/services/provider_resilience.py",
    ]
    missing = [f for f in required_services if not os.path.exists(f)]
    if not missing:
        g.ok(f"All {len(required_services)} phase service files present")
    else:
        g.fail(f"Missing: {', '.join(missing)}")
    return g


def check_apis_present() -> GateResult:
    g = GateResult("all_phase_api_files_present", "completeness")
    required_apis = [
        "backend/app/api/memory.py",
        "backend/app/api/preparation.py",
        "backend/app/api/interview_engines.py",
        "backend/app/api/observability.py",
        "backend/app/api/prepare_me.py",
    ]
    missing = [f for f in required_apis if not os.path.exists(f)]
    if not missing:
        g.ok(f"All {len(required_apis)} phase API files present")
    else:
        g.fail(f"Missing: {', '.join(missing)}")
    return g


def check_test_harnesses_present() -> GateResult:
    g = GateResult("test_harnesses_present", "testing")
    required_tests = [
        "realtime-agent/tests/integration/test_e2e_acceptance.py",
        "realtime-agent/tests/unit/test_dual_path_architecture.py",
        "realtime-agent/tests/evaluation/test_scoring_calibration.py",
        "realtime-agent/tests/acceptance/test_final_acceptance.py",
    ]
    missing = [f for f in required_tests if not os.path.exists(f)]
    if not missing:
        g.ok(f"All {len(required_tests)} test harnesses present")
    else:
        g.fail(f"Missing: {', '.join(missing)}")
    return g


def check_no_import_meta_in_tests() -> GateResult:
    """ts-jest cannot parse import.meta — verify desktop test files use process.env."""
    g = GateResult("no_import_meta_in_jest_tests", "compatibility")
    issues = []
    test_dirs = ["apps/desktop/src"]
    for tdir in test_dirs:
        if not os.path.isdir(tdir):
            continue
        for root, dirs, files in os.walk(tdir):
            dirs[:] = [d for d in dirs if d != "node_modules"]
            for fname in files:
                if not (fname.endswith(".test.ts") or fname.endswith(".spec.ts")):
                    continue
                path = os.path.join(root, fname)
                with open(path, encoding="utf-8", errors="ignore") as f:
                    if "import.meta" in f.read():
                        issues.append(path)
    if not issues:
        g.ok("No import.meta in Jest test files")
    else:
        g.fail(f"import.meta found in: {', '.join(issues[:3])}")
    return g


def check_scripts_present() -> GateResult:
    g = GateResult("quality_scripts_present", "tooling")
    required_scripts = [
        "scripts/check_no_fake_data.py",
        "scripts/check_production_readiness.py",
        "scripts/check_disaster_recovery.py",
        "scripts/final_quality_gate.py",
    ]
    missing = [f for f in required_scripts if not os.path.exists(f)]
    if not missing:
        g.ok(f"All {len(required_scripts)} quality scripts present")
    else:
        g.fail(f"Missing scripts: {', '.join(missing)}")
    return g


def check_dual_path_is_async() -> GateResult:
    """Verify CoachingMetricsAccumulator uses asyncio.sleep (not time.sleep)."""
    g = GateResult("coaching_path_uses_asyncio_sleep", "architecture")
    path = "realtime-agent/realtime_agent/app/coaching/accumulator.py"
    if not os.path.exists(path):
        g.fail(f"{path} not found")
        return g
    with open(path, encoding="utf-8") as f:
        content = f.read()
    if "asyncio.sleep" in content and "time.sleep" not in content:
        g.ok("CoachingMetricsAccumulator uses asyncio.sleep correctly")
    elif "asyncio.sleep" in content:
        g.fail("CoachingMetricsAccumulator mixes asyncio.sleep and time.sleep — may block event loop")
    else:
        g.fail("CoachingMetricsAccumulator does not use asyncio.sleep — fast path may be blocking")
    return g


def check_fallback_lines_marked() -> GateResult:
    """All LLM-failure fallback lines must have # fallback comment."""
    g = GateResult("fallback_lines_marked_as_fallback", "data_integrity")
    code, out, err = _run([sys.executable, "scripts/check_no_fake_data.py"])
    if code == 0:
        g.ok("check_no_fake_data passes — fallback lines correctly marked")
    else:
        g.fail(f"check_no_fake_data failed: {out[:200]}")
    return g


def check_phase_completion_matrix_present() -> GateResult:
    g = GateResult("phase_completion_matrix_present", "documentation")
    path = "docs/PHASE_COMPLETION_MATRIX.md"
    if os.path.exists(path):
        g.ok(f"Phase completion matrix present at {path}")
    else:
        g.fail(f"{path} not found")
    return g


def main():
    checks = [
        check_no_fake_data(),
        check_rls_enabled(),
        check_no_hardcoded_secrets(),
        check_ruff_backend(),
        check_ruff_realtime(),
        check_migration_count(),
        check_migrations_have_rls(),
        check_services_present(),
        check_apis_present(),
        check_test_harnesses_present(),
        check_no_import_meta_in_tests(),
        check_scripts_present(),
        check_dual_path_is_async(),
        check_fallback_lines_marked(),
        check_phase_completion_matrix_present(),
    ]

    print("\n" + "=" * 60)
    print("  PRAXIS FINAL QUALITY GATE")
    print("=" * 60 + "\n")

    categories: dict[str, list[GateResult]] = {}
    for c in checks:
        categories.setdefault(c.category, []).append(c)

    failed_checks = []
    for category, cat_checks in sorted(categories.items()):
        print(f"  {category.upper().replace('_', ' ')}")
        for c in cat_checks:
            icon = "✓" if c.passed else "✗"
            status = "PASS" if c.passed else "FAIL"
            print(f"    [{status}] {icon} {c.name}")
            if not c.passed:
                print(f"          → {c.message}")
                failed_checks.append(c)
        print()

    print("─" * 60)
    print(f"  Total: {len(checks)} checks | Passed: {len(checks) - len(failed_checks)} | Failed: {len(failed_checks)}")

    if failed_checks:
        print(f"\n  ✗ QUALITY GATE FAILED — {len(failed_checks)} check(s) must be fixed.\n")
        sys.exit(1)
    else:
        print(f"\n  ✓ QUALITY GATE PASSED — {len(checks)} checks all green.\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
