# PRAXIS Phase 1 — Repository Baseline & Forensic Audit

**Date**: 2026-11-01  
**Repository**: `AMIYA8597/praxis-interviewOS`  
**Working Directory**: `d:\work\interviewOS`  
**Branch**: `phase1-backend-db`  
**HEAD Commit**: `94641b3`  
**Target Architecture**: Supabase (PostgreSQL 17 + pgvector, Auth, Storage) + GCP Cloud Run (Core API, Realtime Agent, ARQ Worker) + GCP Secret Manager + Memorystore Redis

---

## 1. Toolchain & Runtime Environment Baseline

| Tool / Runtime | Version | Status | Command / Source |
|---|---|:---:|---|
| **Python (System)** | `3.13.7` | PASS | `python --version` |
| **Python (Repo Venv)** | `3.11.11` | PASS | `.venv\Scripts\python.exe --version` |
| **Node.js** | `v24.18.0` | PASS | `node --version` |
| **pnpm** | `10.30.3` | PASS | `pnpm --version` |
| **uv** | `0.5.9` | PASS | `uv --version` |
| **Docker CLI** | `29.7.2` (build `a7dcaa6`) | PASS | `docker --version` |
| **Docker Daemon** | Stopped / Not connected | BLOCKED | `npipe:////./pipe/dockerDesktopLinuxEngine` (Docker Desktop stopped) |
| **Terraform** | `v1.16.4` | PASS | `terraform --version` |
| **Google Cloud SDK** | `587.0.0` | PASS | `gcloud --version` |
| **Supabase CLI** | `2.122.0` | PASS | `npx supabase --version` |
| **Local PostgreSQL** | `postgresql-x64-18` (Service running on :5432) | PARTIAL | Service running; lacks `pgvector` extension; role `USER` does not exist |
| **Local Redis** | None (port 6379 refused) | BLOCKED | Redis service not running on Windows host |

---

## 2. Git State & Working Tree Audit

- **Current Branch**: `phase1-backend-db`
- **Tracking Remote**: `origin/phase1-backend-db` (in sync with remote at commit `94641b3`)
- **Remote Origin URL**: `https://github.com/AMIYA8597/praxis-interviewOS.git`
- **Recent Git Log**:
  - `94641b3` feat(phase1): complete observability, openapi contract, pooler & worker hardening, and multi-container specs
  - `e9888f7` fix(phase1): resolve CI breakers, ruff lint errors, and test collection (Gate 1 green)
  - `363779e` docs(staging): update staging test report with full audit ledger and gate verification
  - `5bfef8f` refactor(sandbox): relocate sandbox_service from services layer to satisfy architecture boundaries
  - `fc35290` test(client): reference end-to-end client and faster-whisper real-time factor benchmark (P2.15)
- **Local Modifications**: Clean working tree on all project code (submodule `.claude/worktrees` preserved unchanged).

---

## 3. Boundary & Completeness Verification

| Check | Command | Exit Code | Result | Evidence |
|---|---|:---:|:---:|---|
| **No Fake Data Gate** | `python scripts/check_no_fake_data.py` | 0 | **PASS** | No hardcoded placeholder/fake production values detected |
| **Gateway Boundary** | `python scripts/check_gateway_boundary.py` | 0 | **PASS** | No direct provider SDK imports found outside `packages/ai-gateway` |
| **Prompt Construction Boundary** | `python scripts/check_prompt_construction_boundary.py` | 0 | **PASS** | No inline prompt construction outside `prompt_builder.py` |
| **Backend Completeness Gate** | `python scripts/check_backend_completeness.py` | 0 | **PASS** | 75/75 required capabilities verified present |
| **OpenAPI Contract Drift** | `pytest backend/tests/api/test_openapi_contract.py` | 0 | **PASS** | Live FastAPI routes match committed `docs/openapi.json` |

---

## 4. Test Suite Execution Baseline

| Suite | Scope | Total | Passed | Skipped | Failed | Duration | Notes |
|---|---|:---:|:---:|:---:|:---:|:---:|---|
| **Backend Core Tests** | `backend/tests/` | 186 | 181 | 5 | 0 | 64.3s | 5 tests skipped requiring live PostgreSQL / Redis / Cloud AI |
| **Security & Hardening** | `backend/tests/security/` + `backend/tests/hardening/` | 87 | 84 | 3 | 0 | 8.8s | 3 skipped requiring live DB / worker queue |
| **Observability Suite** | `backend/tests/api/test_observability.py` | 13 | 13 | 0 | 0 | 0.3s | Health endpoints, correlation IDs, PII masking, metrics auth |
| **AI Gateway & Realtime Agent** | `packages/ai-gateway/tests/` + `realtime-agent/tests/` | 51 | 49 | 0 | 0 | 34.7s | 2 deselected live-provider tests |
| **Root Tests** | `tests/` | 40 | 29 | 9 | 0 | 37.0s | 9 skipped requiring live PostgreSQL / Redis; 2 deselected live provider |
| **Ruff Lint Suite** | Repo-wide (`.`) | — | All passed | 0 | 0 | 1.1s | 0 errors across entire codebase |

---

## 5. Identified Environmental Prerequisites (BLOCKED items)

1. **`DATABASE_URL`**: Currently configured with placeholder credentials (`postgresql://USER:PASSWORD@localhost:5432/praxis`). Real Supabase staging connection string required for Gate 4 / Gate 5 live verification.
2. **`REDIS_URL`**: Currently `redis://localhost:6379/0` (connection refused). Live Redis daemon required for live worker and TTL queue verification.
3. **`SUPABASE_URL` & Keys**: Currently empty in `.env`. Required for live JWT verification and Supabase storage upload testing.
4. **Docker Host Engine**: Docker Desktop daemon is stopped on the Windows host. Required for executing container builds (`docker build`).
