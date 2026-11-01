# Phase 1: Audit & CI Reproduction Report

**Date**: 2026-11-01  
**Branch**: `phase1-backend-db`  
**Environment**: Windows, Python 3.11.11, PostgreSQL 18 (local instance), Redis (inactive)

---

## 1. Directory Tree Overview

```text
backend/
├── alembic/
├── app/
│   ├── api/
│   ├── core/
│   ├── db/
│   ├── repositories/
│   ├── schemas/
│   ├── services/
│   └── workers/
├── core/
├── models/
├── services/
└── tests/
    ├── api/
    ├── evaluation/
    ├── hardening/
    ├── integration/
    ├── rag/
    ├── security/
    └── services/

realtime-agent/
├── realtime_agent/
│   ├── app/
│   │   ├── audio/
│   │   ├── coaching/
│   │   ├── interview/
│   │   ├── scoring/
│   │   └── session/
│   ├── core/
│   └── main.py
└── tests/
    └── integration/

packages/
├── ai-gateway/
│   ├── praxis_ai_gateway/
│   │   ├── providers/
│   │   ├── schemas/
│   │   ├── transcription/
│   │   └── vision/
│   └── tests/
├── config/
│   └── settings.py
├── schemas/
├── types/
└── ui/

supabase/migrations/
├── 20260907235759_local_auth_primitives.sql
├── 20260907235800_init_core_schema.sql
├── ... (31 migration files total)
└── 20261005000015_data_exports.sql

scripts/
├── check_backend_completeness.py
├── check_gateway_boundary.py
├── check_no_fake_data.py
├── check_prompt_construction_boundary.py
├── migrate.py
└── ...

.github/workflows/
└── ci.yml
```

---

## 2. CI Reproduction Test Matrix

| Component / Test Suite | Command | Status | Exact Error / Output Summary |
|---|---|---|---|
| **Ruff Linter** | `ruff check .` | **FAIL** | 22 errors on main (`IndentationError` in `test_rls_pool_leak.py`, F401 unused imports in 9 files, F821 `anext` undefined in `test_rls_forged_jwt.py`, UTF-16 LE encoding on `doctor_env.py` and `_deprecated_apply_schema.py`). |
| **Migrations Idempotency** | `python scripts/migrate.py` (Run 1 & 2) | **FAIL** | `Failed to connect to database: role "USER" does not exist` (connecting to `localhost:5432/praxis` via unconfigured placeholder `DATABASE_URL`). |
| **No Fake Data Gate** | `python scripts/check_no_fake_data.py` | **PASS** | `OK – no fake/hardcoded production data detected.` |
| **Gateway Boundary** | `python scripts/check_gateway_boundary.py` | **PASS** | `Gateway boundary check passed: No direct provider SDK imports found outside the providers layer.` |
| **Prompt Construction** | `python scripts/check_prompt_construction_boundary.py` | **PASS** | `Prompt construction boundary check passed: No suspicious inline prompt construction found.` |
| **Backend Completeness** | `python scripts/check_backend_completeness.py` | **PASS** | `Results: 75/75 passed \| 0 required failure(s). PASS – all required backend capabilities are present.` |
| **RLS Security Suite** | `pytest -x -v tests/security/test_rls_enabled.py tests/security/test_rls_isolation.py backend/tests/security/test_rls_isolation.py backend/tests/security/test_rls_storage.py backend/tests/integration/test_rls_bypass.py` | **FAIL** | `psycopg2.OperationalError: connection to server at "localhost" (::1), port 5432 failed: FATAL: role "USER" does not exist` in `test_rls_enabled.py`. |
| **Backend Test Suite** | `pytest backend/tests/ -q -rs -m "not live_provider"` | **FAIL** | `ERROR collecting tests/integration/test_rls_pool_leak.py: IndentationError: unexpected indent (line 10)`. |
| **AI Gateway Tests** | `pytest packages/ai-gateway/tests/ -q -rs -m "not live_provider"` | **PASS** | `19 passed in 6.63s` |
| **Realtime Agent Tests** | `pytest realtime-agent/tests/ -q -rs -m "not live_provider"` | **PASS** | `30 passed, 2 deselected in 10.31s` |
| **Top-level Integration Tests** | `pytest tests/ -q -rs -m "not live_provider"` | **FAIL** | `ModuleNotFoundError: No module named 'sentence_transformers'` while importing `tests/integration/test_hybrid_mock.py`. |

---

## 3. Detailed Component Failures & Root Causes

### 1. `backend/tests/integration/test_rls_pool_leak.py`
- **Error**: `IndentationError: unexpected indent` at line 10.
- **Cause**: Malformed `pytestmark` skip condition leftover near top of file:
  ```python
  pytestmark = pytest.mark.asyncio

      not os.environ.get("DATABASE_URL"),
  )
  ```
- **Fix Required**: Cleanly define `pytestmark` with `pytest.mark.skipif(not is_real_postgres(os.environ.get("DATABASE_URL")), reason="Requires real PostgreSQL")` and async test marker.

### 2. Ruff Linter Errors (22 on main)
- **F821 `anext` Undefined**: Python 3.10+ built-in `anext` flagged because Ruff target version and Python requirements are unset or defaulting to older Python in `pyproject.toml`.
  - Fix: Set `target-version = "py311"` and `requires-python = ">=3.11"` in `pyproject.toml`.
- **F401 Unused Imports**:
  - `backend/app/sandbox_service.py`: `typing.Optional`, `fastapi.HTTPException`, `fastapi.status`
  - `backend/tests/api/test_exports.py`: `unittest.mock.patch`, `pytest`
  - `backend/tests/security/test_prompt_injection.py`: `pytest`, `SafetyReport`
  - `backend/tests/security/test_rls_forged_jwt.py`: `sqlalchemy.text`
  - `backend/tests/services/test_coding_sandbox.py`: `os`
  - `realtime-agent/tests/test_audio_protocol.py`: `pytest`, `create_app`, `TestClient`, `jwt`
  - `scripts/benchmark_whisper_rtf.py`: `os`
  - `scripts/check_backend_completeness.py`: `os`
  - `scripts/clients/praxis_client.py`: `sys`, `pathlib.Path`
- **Non-UTF-8 Encoding**:
  - `scripts/doctor_env.py` and `scripts/_deprecated_apply_schema.py` saved with UTF-16 LE BOM. Must be resaved as UTF-8 without BOM.
- **Exclusion of Non-repo Worktrees**:
  - Exclude `.claude` worktree artifacts from Ruff checking in `pyproject.toml`.

### 3. Database & Migrations Environment
- **Error**: `role "USER" does not exist` connecting to `postgresql://USER:PASSWORD@localhost:5432/praxis`.
- **Cause**: Local `.env` contains placeholder credentials:
  - `DATABASE_URL=postgresql://USER:PASSWORD@localhost:5432/praxis`
  - `REDIS_URL=redis://localhost:6379/0` (Redis service not running on port 6379)
  - `SUPABASE_URL=`, `SUPABASE_ANON_KEY=`, `SUPABASE_SERVICE_ROLE_KEY=`, `SUPABASE_JWT_SECRET=` are empty.
  - Local PostgreSQL on port 5432 is PostgreSQL 18 without the `vector` extension (`pgvector`).
