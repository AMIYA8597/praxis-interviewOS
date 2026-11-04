# PRAXIS InterviewOS — Repository Inventory & Forensic Audit

**Audit Date:** 2026-11-04  
**Audit Scope:** Full repository forensic audit, baseline verification, Git commit graph, file system tree, toolchain, and CI configuration.  
**Execution Environment:** Windows Server / Windows 11 (AMD64), Python 3.13.7, Node v22.14.0 / pnpm 10.6.2, PostgreSQL 18.0 Native.  

---

## 1. Git State & Commit Verification

- **Current Branch:** `release-candidate`
- **Current HEAD Commit:** `95f6b127c8e7a6f011f73dc59e72b9963ec1c569` (`fix(gemini): respect GEMINI_MODEL in stream and structured endpoints`)
- **Remote Configuration:**
  - `origin`: `https://github.com/AMIYA8597/praxis-interviewOS.git` (fetch/push)
  - `HEAD` is 1 commit ahead of `origin/release-candidate` (`9b0ec57`).
- **Baseline Commit `325f233` Verification:**
  - `325f233` is present in the git commit ancestry: `325f233 feat: complete all missing backend features and fix runtime defects`.
  - Exactly 36 commits exist between `325f233` and `HEAD` (`95f6b12`), representing the hardening, testing, infrastructure, and release candidate stages.
  - No commits have been reset, force-pushed, or discarded.
- **Working Tree State:** Clean (`git status` reports nothing to commit, working tree clean).

### Recent Git History (Last 10 Commits)
1. `95f6b12` (HEAD -> release-candidate) fix(gemini): respect GEMINI_MODEL in stream and structured endpoints
2. `9b0ec57` (origin/release-candidate) docs(phase8): add final delivery report and performance benchmark suite
3. `2ab2030` feat(release): complete launch-readiness verification, provider resilience, and e2e test suite
4. `b625644` (origin/main, main) Merge Phase 7 Live AI Activation
5. `cbd14bc` (phase7-live-ai-activation) feat(phase7): live AI activation, error propagation, debrief traceability, and zero-spend provider routing
6. `e5c18b2` (origin/implementation-rebuild, implementation-rebuild) feat(phase6): live ai orchestration, typed unconfigured error, and boundary verification
7. `bb01ce1` feat: complete executable implementation, local infrastructure integration and e2e verification
8. `d1ab995` feat(phase5): add root terraform module and complete 15-document production engineering handoff package
9. `bef9ac6` feat(rebuild): deliver 10/10 master architecture diagrams, baseline inventory, and sequential phase handoffs
10. `22c5325` feat(phase5): complete production engineering specifications, runbooks, and lifecycle tests

---

## 2. Repository Tree & Component Structure

The repository is organized as a unified monorepo with strict package boundaries:

```
interviewOS/
├── backend/                  # FastAPI Core API & Worker Services
│   ├── app/
│   │   ├── api/              # 20 API routers mounted at /api/v1
│   │   ├── core/             # Storage, Queue, Security, Bootstrap, Logging
│   │   ├── db/               # SQLAlchemy models and session factories
│   │   ├── repositories/     # Data access layer
│   │   ├── schemas/          # Pydantic v2 schemas
│   │   ├── services/         # Domain business logic (SM-2, matching, sandbox, solvers)
│   │   └── workers/          # Background task execution
│   ├── tests/                # 223 automated test cases
│   └── worker_settings.py    # ARQ worker settings
├── realtime-agent/           # Realtime Audio & WebSocket Orchestrator
│   ├── realtime_agent/
│   │   ├── app/              # FastAPI WebSocket server, protocol framing (>BBIdI)
│   │   ├── audio/            # Silero VAD, Faster-Whisper STT, Piper TTS
│   │   ├── coaching/         # Low-latency DSP metrics (WPM, filler, pause detection)
│   │   ├── interview/        # Interview policy, question generation, debrief
│   │   ├── scoring/          # Turn scoring, 5-tier claim grounding
│   │   └── session/          # Redis-backed distributed state machine
│   └── tests/                # 35 automated test cases
├── packages/
│   ├── ai-gateway/           # Praxis AI Gateway (provider boundary, retry, budgets)
│   │   ├── praxis_ai_gateway/
│   │   └── tests/            # 22 automated test cases
│   ├── config/               # Pydantic Settings, environment validation
│   ├── schemas/              # Shared data contracts
│   ├── types/                # Shared TypeScript types
│   └── ui/                   # Shared React/Tailwind design system components
├── supabase/
│   └── migrations/           # 31 SQL migration scripts (RLS, indexes, schemas)
├── infra/
│   ├── gcp/                  # GCP Terraform (Cloud Run, Cloud SQL, Memorystore, IAM)
│   ├── terraform/            # Root Terraform modules
│   └── bootstrap/            # GCS remote state bucket and KMS bootstrap
├── docker/
│   ├── Dockerfile.api        # Multi-stage production container for API
│   ├── Dockerfile.realtime   # Multi-stage production container for Realtime Agent
│   ├── Dockerfile.worker     # Multi-stage production container for ARQ worker
│   └── Dockerfile.sandbox    # Hardened candidate code execution sandbox
├── docs/                     # Production architecture, runbooks, specifications
│   └── audit/                # Phase 0 forensic audit artifacts
├── scripts/                  # Operational, diagnostic, and verification scripts
└── tests/                    # Monorepo cross-package integration & security tests
```

---

## 3. Dependency Lockfiles & Toolchain Verification

| Component | Management Tool | Lockfile / Pinned File | Status | Notes |
|---|---|---|---|---|
| **Python Monorepo** | `uv` / `pip` | `pyproject.toml`, `requirements-lock.txt`, `uv.lock` | **VERIFIED** | Python 3.11+ target, running under Python 3.13.7 |
| **Node.js Monorepo** | `pnpm` | `pnpm-lock.yaml`, `package.json`, `pnpm-workspace.yaml` | **VERIFIED** | Node v22.14.0, pnpm v10.6.2 |
| **Database Migrations** | Supabase CLI / psql | `supabase/migrations/*.sql` (31 files) | **VERIFIED** | Applied sequentially from scratch |
| **Terraform GCP** | Terraform | `infra/gcp/.terraform.lock.hcl`, `infra/terraform/.terraform.lock.hcl` | **VERIFIED** | Google provider 6.50.0 pinned |
| **Containers** | Docker | `docker-compose.yml`, `docker/Dockerfile.*` | **VERIFIED** | Pinned base images (`python:3.11-slim`, `node:20-alpine`) |

---

## 4. CI/CD Workflow Audit

- **Workflow File:** `.github/workflows/ci.yml` (418 lines)
- **Active Jobs:**
  1. `backend-tests`: Provisions PostgreSQL 17 + pgvector and Redis 7, applies all 31 migrations, verifies RLS enforcement, and runs `backend/tests` (223 tests).
  2. `lint-and-format`: Enforces `ruff` lint rules and type safety across all Python packages.
  3. `security-audit`: Runs `pip-audit`, `detect-secrets`, and boundary verification scripts (`scripts/check_gateway_boundary.py`, `scripts/check_no_fake_data.py`).
  4. `ai-gateway-tests`: Executes `packages/ai-gateway/tests` (22 tests).
  5. `realtime-tests`: Executes `realtime-agent/tests` (35 tests).
  6. `docker-build-verification`: Verifies multi-stage buildability of `Dockerfile.api`, `Dockerfile.realtime`, `Dockerfile.worker`, and `Dockerfile.sandbox`.
  7. `web-and-desktop-tests`: Runs Jest test suites for web and desktop applications.
- **Trigger Strategy:** Runs on push and pull-request targeting `main`. Concurrency cancellation enabled for superseded runs.
