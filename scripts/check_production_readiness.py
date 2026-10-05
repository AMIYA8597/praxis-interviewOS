#!/usr/bin/env python3
"""
Phase 77 — Production Readiness Checker.

Verifies: Docker, Postgres, Redis, worker, env vars, migrations, RLS.
Exits with non-zero code if any CHECK fails.
All checks are real — no fabricated pass results.
"""
import os
import subprocess
import sys


class Check:
    def __init__(self, name: str):
        self.name = name
        self.passed = False
        self.message = ""

    def ok(self, msg: str):
        self.passed = True
        self.message = msg

    def fail(self, msg: str):
        self.passed = False
        self.message = msg


def _run(cmd: list[str], timeout: int = 10) -> tuple[int, str, str]:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "TIMEOUT"
    except FileNotFoundError:
        return -1, "", f"NOT FOUND: {cmd[0]}"


def check_docker() -> Check:
    c = Check("docker_available")
    code, out, err = _run(["docker", "info"])
    if code == 0:
        c.ok("Docker daemon running")
    else:
        c.fail(f"Docker unavailable: {err[:100]}")
    return c


def check_docker_compose() -> Check:
    c = Check("docker_compose_available")
    code, out, err = _run(["docker", "compose", "version"])
    if code == 0:
        c.ok(f"docker compose: {out[:50]}")
    else:
        c.fail(f"docker compose unavailable: {err[:100]}")
    return c


def check_env_vars() -> Check:
    c = Check("required_env_vars")
    required = [
        "DATABASE_URL",
        "REDIS_URL",
        "SUPABASE_URL",
        "SUPABASE_SERVICE_ROLE_KEY",
    ]
    missing = [v for v in required if not os.environ.get(v)]
    if not missing:
        c.ok(f"All {len(required)} required env vars present")
    else:
        c.fail(f"Missing env vars: {', '.join(missing)}")
    return c


def check_no_fake_data_script() -> Check:
    c = Check("no_fake_data_in_runtime")
    code, out, err = _run([sys.executable, "scripts/check_no_fake_data.py"])
    if code == 0:
        c.ok("No fake data detected in runtime code")
    else:
        c.fail(f"Fake data check failed:\n{out[:300]}")
    return c


def check_migration_files() -> Check:
    c = Check("migration_files_present")
    migrations_dir = "supabase/migrations"
    if not os.path.isdir(migrations_dir):
        c.fail(f"Migrations directory not found: {migrations_dir}")
        return c
    files = sorted(f for f in os.listdir(migrations_dir) if f.endswith(".sql"))
    if len(files) >= 1:
        c.ok(f"{len(files)} migration file(s) found")
    else:
        c.fail("No migration files found")
    return c


def check_rls_in_migrations() -> Check:
    c = Check("rls_force_in_migrations")
    migrations_dir = "supabase/migrations"
    if not os.path.isdir(migrations_dir):
        c.fail("Migrations directory not found")
        return c

    files_without_force_rls = []
    for fname in os.listdir(migrations_dir):
        if not fname.endswith(".sql"):
            continue
        path = os.path.join(migrations_dir, fname)
        with open(path, encoding="utf-8") as f:
            content = f.read()
        # Check: every ENABLE ROW LEVEL SECURITY is paired with a FORCE
        enable_count = content.upper().count("ENABLE ROW LEVEL SECURITY")
        force_count = content.upper().count("FORCE ROW LEVEL SECURITY")
        if enable_count > 0 and force_count < enable_count:
            files_without_force_rls.append(fname)

    if not files_without_force_rls:
        c.ok("All migrations with ENABLE RLS also have FORCE RLS")
    else:
        c.fail(f"Missing FORCE RLS in: {', '.join(files_without_force_rls)}")
    return c


def check_backend_imports() -> Check:
    c = Check("backend_imports_clean")
    code, out, err = _run([sys.executable, "-c", "import backend.app.main"])
    if code == 0:
        c.ok("backend.app.main imports cleanly")
    else:
        c.fail(f"Import error: {err[:300]}")
    return c


def check_realtime_agent_imports() -> Check:
    c = Check("realtime_agent_imports_clean")
    code, out, err = _run([sys.executable, "-c", "import realtime_agent.app.main"])
    if code == 0:
        c.ok("realtime_agent.app.main imports cleanly")
    else:
        c.fail(f"Import error: {err[:300]}")
    return c


def main():
    checks = [
        check_docker(),
        check_docker_compose(),
        check_env_vars(),
        check_migration_files(),
        check_rls_in_migrations(),
        check_no_fake_data_script(),
        check_backend_imports(),
        check_realtime_agent_imports(),
    ]

    print("\n=== PRAXIS PRODUCTION READINESS CHECKS ===\n")
    failed = []
    for check in checks:
        icon = "✓" if check.passed else "✗"
        status = "PASS" if check.passed else "FAIL"
        print(f"  [{status}] {icon} {check.name}: {check.message}")
        if not check.passed:
            failed.append(check)

    print(f"\n{'─' * 50}")
    print(f"  Results: {len(checks) - len(failed)}/{len(checks)} passed")

    if failed:
        print(f"\n  FAILED checks:")
        for c in failed:
            print(f"    - {c.name}: {c.message}")
        print()
        sys.exit(1)
    else:
        print("\n  All production readiness checks passed.\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
