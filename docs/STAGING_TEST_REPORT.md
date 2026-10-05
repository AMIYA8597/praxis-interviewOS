# PRAXIS Staging Test Report

**Date: 2026-10-05**  
**Commit: 44c7a8e + infrastructure sovereignty pass**

---

## Test Environment Labels

| Label | Description |
|---|---|
| UNIT | Pure unit test, no I/O |
| INTEGRATION | Tests multiple components together with real DB/Redis |
| LOCAL_E2E | End-to-end with local Docker stack |
| MOCKED_PROVIDER | Uses mock/fake AI provider |
| REAL_PROVIDER | Requires real API key to a live provider |
| REAL_SUPABASE | Requires real Supabase project |
| REAL_REDIS | Requires real Redis instance |
| REAL_CLOUD_RUN | Requires deployed Cloud Run |
| REAL_WEBSOCKET | Requires deployed realtime service |
| REAL_AI | Requires live AI provider |

---

## Test Results

| Test Suite | Type | Command | Environment | Result | Count | Evidence |
|---|---|---|---|---|---|---|
| Backend unit/integration | UNIT + INTEGRATION | `pytest backend/tests -m "not live_provider"` | Local CI (PostgreSQL + Redis) | **PASS** | 146/146 | CI: backend-tests job |
| Architecture boundaries | UNIT | `pytest backend/tests/test_architecture_boundaries.py` | Local | **PASS** | 5/5 | |
| Completeness gate | UNIT | `python scripts/check_backend_completeness.py` | Local | **PASS** | 75/75 | |
| Behavioral calibration | UNIT | `pytest backend/tests/evaluation/test_behavioral_calibration.py` | Local | **PASS** | 15/15 | |
| Prompt injection | UNIT | `pytest backend/tests/security/test_prompt_injection.py` | Local | **PASS** | 26/26 | |
| RLS enabled | INTEGRATION | `pytest tests/security/test_rls_enabled.py` | Local CI (PostgreSQL) | **PASS** | 6/6 | |
| Gateway boundary | UNIT | `python scripts/check_gateway_boundary.py` | Local | **PASS** | — | |
| No fake data | UNIT | `python scripts/check_no_fake_data.py` | Local | **PASS** | — | |
| Ruff lint | STATIC | `ruff check .` | Local CI | **PASS** | — | |
| pip-audit | STATIC | `pip-audit` (High/Critical only) | Local CI | **PASS** | — | |
| Terraform fmt | STATIC | `terraform fmt -check -recursive infra/` | Local | **PASS** | — | |
| Terraform validate (bootstrap) | STATIC | `terraform validate` | Local | **PASS** | — | |
| Terraform validate (main) | STATIC | `terraform validate` | Local | **PASS** | — | |
| Secret scan | STATIC | `detect-secrets scan` | Local CI | **PASS** | — | |
| test_rls_pool_leak.py | INTEGRATION (REAL_SUPABASE) | `pytest backend/tests/integration/test_rls_pool_leak.py` | Requires DATABASE_URL | **SKIPPED** | 1 | Skip: no live DATABASE_URL |
| test_rls_isolation.py | INTEGRATION (REAL_SUPABASE) | `pytest backend/tests/security/test_rls_isolation.py` | Requires DATABASE_URL | **SKIPPED** | 2 | Skip: no live DATABASE_URL |
| test_rls_storage.py | INTEGRATION (REAL_SUPABASE) | `pytest backend/tests/security/test_rls_storage.py` | Requires Supabase | **SKIPPED** | 1 | Skip: no Supabase staging |
| test_rls_bypass.py | INTEGRATION (REAL_SUPABASE) | `pytest backend/tests/integration/test_rls_bypass.py` | Requires DATABASE_URL | **SKIPPED** | 1 | Skip: no live DATABASE_URL |
| Live AI provider test | REAL_AI | `pytest -m live_provider` | Requires API keys | **SKIPPED** | — | Skip: no keys configured |
| Docker build praxis-api | BUILD | `docker build -f docker/Dockerfile.api --target production .` | Local Docker | **UNVERIFIED** | — | Not run in this session |
| Docker build praxis-realtime | BUILD | `docker build -f docker/Dockerfile.realtime --target production .` | Local Docker | **UNVERIFIED** | — | Not run; defect fixed this session |
| Docker build praxis-worker | BUILD | `docker build -f docker/Dockerfile.worker --target production .` | Local Docker | **UNVERIFIED** | — | Not run |
| Smoke test | REAL_CLOUD_RUN | `python scripts/smoke_test.py` | Staging Cloud Run | **BLOCKED** | — | GCP project not provisioned |
| Multi-user RLS | REAL_SUPABASE | Custom staging script | Staging Supabase | **BLOCKED** | — | Staging Supabase not created |
| WebSocket E2E | REAL_WEBSOCKET | `wss://realtime/ws/{session}` | Staging Cloud Run | **BLOCKED** | — | Cloud Run not deployed |
| Full interview E2E | REAL_CLOUD_RUN + REAL_AI | manual/scripted | Staging | **BLOCKED** | — | All infrastructure blocked |
| Load test (100 users) | REAL_CLOUD_RUN | locust or similar | Staging | **BLOCKED** | — | |
| Failure injection | REAL_CLOUD_RUN | manual | Staging | **BLOCKED** | — | |
| Backup restore | REAL_SUPABASE | `scripts/backup.sh` + restore | Staging | **BLOCKED** | — | |

---

## Summary

| Result | Count |
|---|---|
| PASS | 14 |
| SKIPPED (documented reason) | 5 |
| UNVERIFIED (local docker build) | 3 |
| BLOCKED (requires infrastructure) | 9 |
| FAIL | 0 |

**No test failures.** All BLOCKED items require human-provisioned infrastructure (GCP project, Supabase staging, domain).

---

*Last updated: 2026-10-05*
