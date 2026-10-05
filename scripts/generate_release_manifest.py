#!/usr/bin/env python3
"""
Generate release/staging-release.json — immutable release manifest.

Called by Cloud Build after successful staging deployment. Records exact
image digests, git commit, migration head, and version information.

No secrets are included. The manifest is safe to commit.

Usage:
    python scripts/generate_release_manifest.py
    # Reads from environment variables set by Cloud Build step capture-digests.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def run(cmd: list[str], default: str = "UNKNOWN") -> str:
    try:
        return subprocess.check_output(cmd, stderr=subprocess.DEVNULL, text=True).strip()
    except Exception:
        return default


def get_migration_head() -> str:
    # Read the latest migration file name from supabase/migrations/
    migrations_dir = Path("supabase/migrations")
    if not migrations_dir.exists():
        return "UNKNOWN"
    files = sorted(migrations_dir.glob("*.sql"))
    return files[-1].stem if files else "UNKNOWN"


def main() -> None:
    git_sha = os.environ.get("GIT_SHA") or run(["git", "rev-parse", "HEAD"])
    build_time = os.environ.get("BUILD_TIME") or datetime.now(timezone.utc).isoformat()

    # Digests are set by the capture-digests Cloud Build step.
    api_image   = os.environ.get("API_IMAGE", "UNKNOWN")
    api_digest  = os.environ.get("API_DIGEST", "UNSET")
    rt_image    = os.environ.get("REALTIME_IMAGE", "UNKNOWN")
    rt_digest   = os.environ.get("REALTIME_DIGEST", "UNSET")
    w_image     = os.environ.get("WORKER_IMAGE", "UNKNOWN")
    w_digest    = os.environ.get("WORKER_DIGEST", "UNSET")

    region          = os.environ.get("REGION", "us-central1")
    staging_project = os.environ.get("STAGING_PROJECT", "UNKNOWN")
    registry_project = os.environ.get("REGISTRY_PROJECT", "UNKNOWN")

    # Python version
    py_version = run(["python", "--version"])

    # Node version
    node_version = run(["node", "--version"])

    # Terraform version
    tf_version = run(["terraform", "version", "-json"])
    try:
        tf_version = json.loads(tf_version).get("terraform_version", "UNKNOWN")
    except Exception:
        tf_version = "UNKNOWN"

    manifest = {
        "schema_version": "1",
        "git_commit": git_sha,
        "build_time": build_time,
        "api_image": api_image,
        "api_digest": api_digest,
        "realtime_image": rt_image,
        "realtime_digest": rt_digest,
        "worker_image": w_image,
        "worker_digest": w_digest,
        "migration_head": get_migration_head(),
        "terraform_version": tf_version,
        "python_version": py_version.replace("Python ", ""),
        "node_version": node_version.lstrip("v"),
        "region": region,
        "gcp_project": staging_project,
        "registry_project": registry_project,
        "supabase_project_ref": "BLOCKED_NOT_YET_PROVISIONED",
        "redis_instance": f"praxis-staging (project: {staging_project})",
        "model_versions": {
            "faster_whisper": "base.en",
            "silero_vad": "5.1.2",
            "bge_small_en": "BAAI/bge-small-en-v1.5",
        },
        "prompt_versions": "see prompts/ directory",
        "rubric_versions": "see backend/app/services/behavioral_engine.py",
    }

    out_dir = Path("release")
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "staging-release.json"

    with open(out_path, "w") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")

    print(f"Release manifest written to {out_path}")
    print(json.dumps(manifest, indent=2))

    # Fail loudly if digests are missing (indicates build pipeline issue)
    missing = [k for k, v in [
        ("api_digest", api_digest),
        ("realtime_digest", rt_digest),
        ("worker_digest", w_digest),
    ] if v in ("UNSET", "DIGEST_UNAVAILABLE")]

    if missing:
        print(f"\nWARNING: Missing digests for: {missing}", file=sys.stderr)
        print("Images pushed but digests could not be captured. Check push-cache step.", file=sys.stderr)


if __name__ == "__main__":
    main()
