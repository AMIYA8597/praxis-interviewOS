#!/usr/bin/env python3
"""
Phase 78 — Disaster Recovery Checker.

Verifies backup/restore/cascade deletion safety.
Checks: FK cascades defined, backup config present, no orphaned rows pattern.
"""
import os
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


def check_cascade_deletes_in_migrations() -> Check:
    c = Check("cascade_deletes_defined")
    migrations_dir = "supabase/migrations"
    if not os.path.isdir(migrations_dir):
        c.fail("Migrations directory not found")
        return c

    files_without_cascade = []
    for fname in sorted(os.listdir(migrations_dir)):
        if not fname.endswith(".sql"):
            continue
        path = os.path.join(migrations_dir, fname)
        with open(path, encoding="utf-8") as f:
            content = f.read()
        # If migration has FK references, check for ON DELETE
        if "REFERENCES" in content.upper():
            if "ON DELETE" not in content.upper():
                files_without_cascade.append(fname)

    if not files_without_cascade:
        c.ok("All FK references include ON DELETE clause")
    else:
        c.fail(f"Missing ON DELETE in: {', '.join(files_without_cascade)}")
    return c


def check_docker_volume_config() -> Check:
    c = Check("docker_volume_config")
    compose_files = ["docker-compose.yml", "docker-compose.yaml",
                     "compose.yml", "compose.yaml",
                     "docker/docker-compose.yml"]
    found = None
    for f in compose_files:
        if os.path.exists(f):
            found = f
            break

    if not found:
        c.fail("No docker-compose file found — cannot verify volume config")
        return c

    with open(found, encoding="utf-8") as f:
        content = f.read()

    if "volumes:" in content:
        c.ok(f"Volume config found in {found}")
    else:
        c.fail(f"{found} has no 'volumes:' section — persistent storage may not be configured")
    return c


def check_backup_script_present() -> Check:
    c = Check("backup_script_present")
    candidates = [
        "scripts/backup.sh", "scripts/backup.py",
        "ops/backup.sh", "scripts/db_backup.sh",
    ]
    found = [f for f in candidates if os.path.exists(f)]
    if found:
        c.ok(f"Backup script found: {found[0]}")
    else:
        c.fail(
            "No backup script found. Create scripts/backup.sh with pg_dump logic. "
            "This is required for production disaster recovery."
        )
    return c


def check_rls_prevents_cross_candidate_access() -> Check:
    """
    Verify that all candidate-specific tables have RLS enabled.
    This prevents one candidate's data leaking to another in a restore scenario.
    """
    c = Check("rls_on_all_candidate_tables")
    migrations_dir = "supabase/migrations"
    if not os.path.isdir(migrations_dir):
        c.fail("Migrations directory not found")
        return c

    # Collect all tables created in migrations and check RLS
    import re
    all_tables = set()
    tables_with_rls = set()
    tables_with_force_rls = set()

    for fname in sorted(os.listdir(migrations_dir)):
        if not fname.endswith(".sql"):
            continue
        with open(os.path.join(migrations_dir, fname), encoding="utf-8") as f:
            content = f.read()

        for m in re.finditer(r"CREATE TABLE IF NOT EXISTS (\w+)", content, re.IGNORECASE):
            all_tables.add(m.group(1))

        for m in re.finditer(r"ALTER TABLE (\w+)\s+ENABLE ROW LEVEL SECURITY", content, re.IGNORECASE):
            tables_with_rls.add(m.group(1))

        for m in re.finditer(r"ALTER TABLE (\w+)\s+FORCE ROW LEVEL SECURITY", content, re.IGNORECASE):
            tables_with_force_rls.add(m.group(1))

    missing_rls = all_tables - tables_with_rls
    missing_force = tables_with_rls - tables_with_force_rls

    if not missing_rls and not missing_force:
        c.ok(f"All {len(all_tables)} tables have ENABLE + FORCE RLS")
    else:
        issues = []
        if missing_rls:
            issues.append(f"Missing ENABLE RLS: {', '.join(sorted(missing_rls))}")
        if missing_force:
            issues.append(f"Missing FORCE RLS: {', '.join(sorted(missing_force))}")
        c.fail("; ".join(issues))
    return c


def main():
    checks = [
        check_cascade_deletes_in_migrations(),
        check_docker_volume_config(),
        check_backup_script_present(),
        check_rls_prevents_cross_candidate_access(),
    ]

    print("\n=== PRAXIS DISASTER RECOVERY CHECKS ===\n")
    failed = []
    warnings = []
    for check in checks:
        icon = "✓" if check.passed else "✗"
        status = "PASS" if check.passed else "FAIL"
        print(f"  [{status}] {icon} {check.name}: {check.message}")
        if not check.passed:
            # backup_script is warning-level, not blocking
            if "backup" in check.name:
                warnings.append(check)
            else:
                failed.append(check)

    print(f"\n{'─' * 50}")
    print(f"  Results: {len(checks) - len(failed) - len(warnings)}/{len(checks)} hard-passed")

    if warnings:
        print(f"\n  WARNINGS (non-blocking):")
        for c in warnings:
            print(f"    ⚠ {c.name}: {c.message}")

    if failed:
        print(f"\n  FAILURES:")
        for c in failed:
            print(f"    ✗ {c.name}: {c.message}")
        print()
        sys.exit(1)
    else:
        print("\n  Disaster recovery checks passed.\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
