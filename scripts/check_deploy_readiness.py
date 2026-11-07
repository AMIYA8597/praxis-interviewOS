#!/usr/bin/env python3
"""Pre-deployment readiness checker for PRAXIS InterviewOS.

Validates that all required configuration is in place for:
  - Vercel (frontend) deployment
  - GCP Cloud Run (backend) deployment
  - Supabase (auth/database) integration

Usage:
    python scripts/check_deploy_readiness.py [--env staging|production]
"""
import argparse
import json
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

# Force UTF-8 output on Windows
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

PASS = "\033[92m[OK]\033[0m"
FAIL = "\033[91m[FAIL]\033[0m"
WARN = "\033[93m[WARN]\033[0m"

errors: list[str] = []
warnings: list[str] = []


def check(label: str, ok: bool, msg: str = "") -> None:
    if ok:
        print(f"  {PASS} {label}")
    else:
        print(f"  {FAIL} {label}" + (f" — {msg}" if msg else ""))
        errors.append(label)


def warn(label: str, msg: str = "") -> None:
    print(f"  {WARN} {label}" + (f" — {msg}" if msg else ""))
    warnings.append(label)


def section(title: str) -> None:
    print(f"\n{'-' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}")


def check_vercel() -> None:
    section("Vercel Frontend")

    vj = ROOT / "vercel.json"
    check("vercel.json exists", vj.exists())
    if vj.exists():
        data = json.loads(vj.read_text())
        check("buildCommand set", bool(data.get("buildCommand")))
        check("env secrets configured", bool(data.get("env")))
        env = data.get("env", {})
        for key in ["NEXT_PUBLIC_SUPABASE_URL", "NEXT_PUBLIC_SUPABASE_ANON_KEY",
                     "NEXT_PUBLIC_API_BASE_URL", "NEXT_PUBLIC_REALTIME_URL"]:
            check(f"  {key} mapped", key in env, "add to vercel.json env")

    pkg = ROOT / "apps" / "web" / "package.json"
    check("apps/web/package.json exists", pkg.exists())
    if pkg.exists():
        p = json.loads(pkg.read_text())
        check("next in dependencies", "next" in p.get("dependencies", {}))
        check("build script defined", "build" in p.get("scripts", {}))

    nc = ROOT / "apps" / "web" / "next.config.js"
    check("next.config.js exists", nc.exists())

    mw = ROOT / "apps" / "web" / "src" / "middleware.ts"
    check("Next.js middleware exists", mw.exists(), "auth/headers won't work without it")

    health = ROOT / "apps" / "web" / "src" / "app" / "api" / "health" / "route.ts"
    check("Health API route exists", health.exists())

    env_example = ROOT / "apps" / "web" / ".env.local.example"
    check(".env.local.example exists", env_example.exists())
    if env_example.exists():
        content = env_example.read_text()
        check("  uses NEXT_PUBLIC_API_BASE_URL", "NEXT_PUBLIC_API_BASE_URL" in content,
              "wrong env var name — code reads NEXT_PUBLIC_API_BASE_URL")
        check("  uses NEXT_PUBLIC_REALTIME_URL", "NEXT_PUBLIC_REALTIME_URL" in content,
              "wrong env var name — code reads NEXT_PUBLIC_REALTIME_URL")


def check_gcp() -> None:
    section("GCP Backend")

    for name in ["Dockerfile.api", "Dockerfile.realtime", "Dockerfile.worker"]:
        check(f"docker/{name} exists", (ROOT / "docker" / name).exists())

    cb = ROOT / "cloudbuild.yaml"
    check("cloudbuild.yaml exists", cb.exists())

    deploy = ROOT / ".github" / "workflows" / "deploy.yml"
    check("deploy.yml workflow exists", deploy.exists())

    tf = ROOT / "infra" / "gcp" / "main.tf"
    check("Terraform main.tf exists", tf.exists())
    if tf.exists():
        content = tf.read_text()
        check("  frontend_url variable defined", "frontend_url" in content,
              "CORS won't include Vercel domain")
        check("  CORS_ALLOW_ORIGINS env set", "CORS_ALLOW_ORIGINS" in content,
              "API won't accept cross-origin requests from frontend")

    secrets = ROOT / "scripts" / "setup-secrets.sh"
    check("setup-secrets.sh exists", secrets.exists())


def check_backend() -> None:
    section("Backend Configuration")

    settings = ROOT / "packages" / "config" / "settings.py"
    check("settings.py exists", settings.exists())

    env_example = ROOT / ".env.example"
    check(".env.example exists", env_example.exists())
    if env_example.exists():
        content = env_example.read_text()
        for key in ["DATABASE_URL", "REDIS_URL", "SUPABASE_URL", "SUPABASE_ANON_KEY",
                     "CORS_ALLOW_ORIGINS", "FERNET_KEY"]:
            check(f"  {key} documented", key in content)

    models = ROOT / "config" / "models.yaml"
    check("config/models.yaml exists", models.exists())


def check_supabase() -> None:
    section("Supabase Integration")

    client = ROOT / "apps" / "web" / "src" / "lib" / "supabase.ts"
    check("Frontend Supabase client exists", client.exists())

    ssr_mw = ROOT / "apps" / "web" / "src" / "utils" / "supabase" / "middleware.ts"
    check("Supabase SSR middleware exists", ssr_mw.exists())

    server = ROOT / "apps" / "web" / "src" / "utils" / "supabase" / "server.ts"
    check("Supabase server utils exists", server.exists())


def check_security() -> None:
    section("Security")

    gi = ROOT / ".gitignore"
    if gi.exists():
        content = gi.read_text()
        check(".env.local gitignored", ".env.local" in content)
        check(".env gitignored", ".env" in content.split("\n") or "*.env" in content or ".env\n" in content)

    ci = ROOT / ".github" / "workflows" / "ci.yml"
    check("CI workflow exists", ci.exists())
    if ci.exists():
        content = ci.read_text()
        check("  Bandit SAST in CI", "bandit" in content.lower())

    tracked_envs = os.popen(f"cd {ROOT} && git ls-files -- '*.env' '.env.*' 'apps/web/.env*' 2>/dev/null").read().strip()
    safe = not any(line.strip() and not line.strip().endswith(".example") for line in tracked_envs.split("\n"))
    check("No .env files tracked (except .example)", safe, f"tracked: {tracked_envs}")


def main() -> None:
    parser = argparse.ArgumentParser(description="PRAXIS deploy readiness check")
    parser.add_argument("--env", choices=["staging", "production"], default="staging")
    args = parser.parse_args()

    print(f"\n  PRAXIS InterviewOS — Deployment Readiness ({args.env})")

    check_vercel()
    check_gcp()
    check_backend()
    check_supabase()
    check_security()

    print(f"\n{'-' * 60}")
    if errors:
        print(f"  {FAIL} {len(errors)} errors, {len(warnings)} warnings")
        sys.exit(1)
    elif warnings:
        print(f"  {WARN} All checks passed with {len(warnings)} warnings")
    else:
        print(f"  {PASS} All checks passed — ready to deploy!")
    print()


if __name__ == "__main__":
    main()
