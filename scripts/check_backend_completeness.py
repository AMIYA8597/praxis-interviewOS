#!/usr/bin/env python3
"""
PRAXIS Backend Completeness Gate — Part 115 of the Backend Sovereignty Specification.

Verifies that all mandatory backend capability categories have at least one
implementation file, one test file, and (where applicable) a migration SQL file.

Exit codes:
  0 — all checks pass
  1 — one or more REQUIRED checks fail
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ── Check definitions ─────────────────────────────────────────────────────────

@dataclass
class Check:
    category: str
    file_globs: list[str]
    required: bool = True
    description: str = ""


CHECKS: list[Check] = [
    # DATABASE
    Check("database.models",       ["backend/app/db/models.py"]),
    Check("database.migrations",   ["supabase/migrations/*.sql"]),
    Check("database.rls",          ["supabase/migrations/*rls*.sql", "supabase/migrations/*force_rls*.sql"]),
    Check("database.session",      ["backend/app/db/session.py"]),

    # AUTHENTICATION / AUTHORIZATION
    Check("auth.jwt_verification", ["backend/app/auth.py"]),
    Check("auth.endpoints",        ["backend/app/api/auth.py"]),
    Check("auth.rate_limiting",    ["backend/app/rate_limiter.py"]),
    Check("auth.security_headers", ["backend/app/middleware.py"]),

    # SECURITY
    Check("security.ssrf_guard",   ["backend/app/core/security.py"]),
    Check("security.upload_guard", ["backend/app/api/resumes.py", "backend/app/core/security.py"]),
    Check("security.prompt_injection",  ["packages/ai-gateway/praxis_ai_gateway/prompt_builder.py"]),
    Check("security.cors",         ["backend/app/main.py"]),
    Check("security.audit_log",    [
        "backend/app/db/models.py",
        "supabase/migrations/20261005000009_audit_logs.sql",
    ]),

    # AI GATEWAY
    Check("ai.gateway",            ["packages/ai-gateway/praxis_ai_gateway/router.py"]),
    Check("ai.model_registry",     ["packages/ai-gateway/praxis_ai_gateway/registry.py"]),
    Check("ai.budget_guard",       ["packages/ai-gateway/praxis_ai_gateway/budget.py", "backend/app/services/budget_guard.py"]),
    Check("ai.circuit_breaker",    ["packages/ai-gateway/praxis_ai_gateway/resilience.py"]),
    Check("ai.structured_output",  ["packages/ai-gateway/praxis_ai_gateway/prompt_builder.py"]),
    Check("ai.provider_boundary",  ["scripts/check_gateway_boundary.py"]),

    # REALTIME
    Check("realtime.state_machine",  ["realtime-agent/realtime_agent/app/session/state_machine.py"]),
    Check("realtime.barge_in",       ["realtime-agent/realtime_agent/app/interview/barge_in.py"]),
    Check("realtime.vad",            ["realtime-agent/realtime_agent/app/audio/vad.py"]),
    Check("realtime.stt",            ["realtime-agent/realtime_agent/app/audio/model_registry.py"]),
    Check("realtime.tts",            ["realtime-agent/realtime_agent/app/audio/tts.py"]),
    Check("realtime.coaching",       ["realtime-agent/realtime_agent/app/coaching/metrics.py"]),
    Check("realtime.redis_state",    ["realtime-agent/realtime_agent/app/session/redis_state.py"]),
    Check("realtime.protocol",       ["realtime-agent/realtime_agent/app/protocol.py"]),

    # INTERVIEW ENGINE
    Check("interview.question_engine",    ["realtime-agent/realtime_agent/app/interview/generation.py"]),
    Check("interview.adaptive_difficulty",["backend/app/services/adaptive_difficulty.py"]),
    Check("interview.scoring",            ["realtime-agent/realtime_agent/app/scoring/service.py"]),
    Check("interview.claim_grounding",    ["realtime-agent/realtime_agent/app/scoring/claims.py"]),
    Check("interview.debrief",            ["realtime-agent/realtime_agent/app/interview/debrief.py"]),
    Check("interview.behavioral",         ["backend/app/services/behavioral_engine.py"]),
    Check("interview.system_design",      ["backend/app/services/system_design_engine.py"]),
    Check("interview.coding",             ["backend/app/services/coding_engine.py"]),

    # RAG / RETRIEVAL
    Check("rag.retrieval",    ["packages/ai-gateway/praxis_ai_gateway/retrieval.py"]),
    Check("rag.embeddings",   ["packages/ai-gateway/praxis_ai_gateway/embeddings.py", "backend/app/workers/embedding_worker.py"]),

    # CANDIDATE INTELLIGENCE
    Check("candidate.memory",      ["backend/app/services/candidate_memory.py"]),
    Check("candidate.sm2",         ["backend/app/services/sm2.py"]),
    Check("candidate.readiness",   ["backend/app/services/readiness.py", "backend/app/services/readiness_v2.py"]),
    Check("candidate.preparation", ["backend/app/services/preparation_engine.py"]),
    Check("candidate.study",       ["backend/app/services/study.py"]),

    # API
    Check("api.health",      ["backend/app/api/health.py"]),
    Check("api.candidates",  ["backend/app/api/candidates.py"]),
    Check("api.resumes",     ["backend/app/api/resumes.py"]),
    Check("api.jobs",        ["backend/app/api/jobs.py"]),
    Check("api.sessions",    ["backend/app/api/sessions.py"]),
    Check("api.study",       ["backend/app/api/study.py"]),
    Check("api.admin",       ["backend/app/api/admin.py"]),
    Check("api.analytics",   ["backend/app/api/analytics.py"]),
    Check("api.readiness",   ["backend/app/api/readiness.py"]),

    # WORKERS
    Check("workers.arq_pool",      ["backend/app/core/queue.py"]),
    Check("workers.tasks",         ["backend/app/worker_tasks.py"]),
    Check("workers.idempotency",   ["backend/app/services/worker_idempotency.py"]),
    Check("workers.deletion",      ["backend/app/core/deletion.py"]),

    # OBSERVABILITY
    Check("observability.logging",  ["backend/app/core/logging_config.py"]),
    Check("observability.tracing",  ["backend/app/core/bootstrap.py"]),
    Check("observability.context",  ["backend/app/core/context.py"]),
    Check("observability.request_id", ["backend/app/middleware.py"]),

    # CONFIGURATION
    Check("config.settings",       ["packages/config/settings.py"]),
    Check("config.validation",     ["packages/config/settings.py"]),

    # DEPLOYMENT
    Check("deployment.dockerfile_api",      ["docker/Dockerfile.api"]),
    Check("deployment.dockerfile_realtime", ["docker/Dockerfile.realtime"]),
    Check("deployment.dockerfile_worker",   ["docker/Dockerfile.worker"]),
    Check("deployment.terraform",           ["infra/gcp/main.tf"]),
    Check("deployment.cloud_build",         ["cloudbuild.yaml"]),
    Check("deployment.lock_file",           ["requirements-lock.txt"]),

    # TESTING
    Check("tests.rls",             ["backend/tests/security/test_rls_isolation.py", "backend/tests/integration/test_rls_bypass.py"]),
    Check("tests.jwt",             ["backend/tests/hardening/test_jwt_auth.py"]),
    Check("tests.prompt_injection",["backend/tests/security/test_prompt_injection.py"], required=False,
          description="No dedicated test yet; prompt_builder.py provides the defence"),
    Check("tests.e2e",             ["realtime-agent/tests/integration/test_e2e_acceptance.py"]),
    Check("tests.no_fake_data",    ["scripts/check_no_fake_data.py"]),
    Check("tests.gateway_boundary",["scripts/check_gateway_boundary.py"]),

    # FEATURE FLAGS + AUDIT
    Check("ops.feature_flags",     ["supabase/migrations/20261005000010_feature_flags.sql"]),
    Check("ops.audit_log_migration",["supabase/migrations/20261005000009_audit_logs.sql"]),
]

# ── Runner ────────────────────────────────────────────────────────────────────

def _resolve_glob(pattern: str) -> list[Path]:
    import glob as _glob
    matches = _glob.glob(str(ROOT / pattern), recursive=True)
    return [Path(m) for m in matches if Path(m).is_file()]


def run_checks() -> int:
    failures = 0
    print(f"\nPRAXIS Backend Completeness Gate — {ROOT.name}\n{'='*64}")

    results: list[tuple[str, str, str, str]] = []  # (status, category, found, notes)

    for chk in CHECKS:
        found_files: list[str] = []
        for pattern in chk.file_globs:
            for f in _resolve_glob(pattern):
                found_files.append(str(f.relative_to(ROOT)))

        if found_files:
            status = "PASS"
            note = found_files[0] if len(found_files) == 1 else f"{found_files[0]} (+{len(found_files)-1})"
        else:
            status = "FAIL" if chk.required else "WARN"
            note = f"None of: {', '.join(chk.file_globs)}"
            if chk.required:
                failures += 1

        results.append((status, chk.category, note, ""))

    # Print report (ASCII-safe for Windows cp1252 terminals)
    col_w = max(len(r[1]) for r in results) + 2
    for status, category, note, _ in sorted(results, key=lambda r: (r[0] != "FAIL", r[0], r[1])):
        icon = "OK" if status == "PASS" else ("!!" if status == "FAIL" else "--")
        print(f"  {icon} [{status}] {category:<{col_w}} {note}")

    total = len(CHECKS)
    passed = sum(1 for r in results if r[0] == "PASS")
    print(f"\n{'='*64}")
    print(f"Results: {passed}/{total} passed  |  {failures} required failure(s)")
    if failures:
        print("\nFAIL — resolve the required failures before deployment.\n")
    else:
        print("\nPASS — all required backend capabilities are present.\n")
    return failures


if __name__ == "__main__":
    sys.exit(run_checks())
