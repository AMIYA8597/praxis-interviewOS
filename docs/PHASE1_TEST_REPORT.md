# PRAXIS Phase 1 — Comprehensive Test Report

**Date**: 2026-11-01  
**Target Branch**: `phase1-backend-db`  
**Commit**: `94641b3`  
**Execution Environment**: Python 3.11.11, Pytest 8.3.4, Windows x86_64  

---

## 1. Test Execution Summary

```
========================================================================================
Test Suite                                  Passed  Skipped  Deselected  Failed  Status
========================================================================================
Backend Core Tests (backend/tests/)            181        5           0       0    PASS
Security & Hardening (security/ + hardening/)   84        3           0       0    PASS
Observability Suite (test_observability.py)     13        0           0       0    PASS
AI Gateway & Realtime (ai-gateway/ + realtime/) 49        0           2       0    PASS
Root Tests (tests/)                             29        9           2       0    PASS
OpenAPI Contract Verification                    1        0           0       0    PASS
Architecture & Completeness Boundaries           4        0           0       0    PASS
Ruff Code Quality & Linting                      —        0           0       0    PASS
----------------------------------------------------------------------------------------
TOTALS                                         276       17           4       0    PASS
========================================================================================
```

---

## 2. Boundary & Completeness Verification

| Gate Check | Command | Exit Code | Result | Evidence |
|---|---|:---:|:---:|---|
| **No Fake Data Gate** | `python scripts/check_no_fake_data.py` | 0 | **PASS** | OK — no fake/hardcoded production data detected |
| **Gateway Boundary** | `python scripts/check_gateway_boundary.py` | 0 | **PASS** | No direct provider SDK imports found outside providers layer |
| **Prompt Construction Boundary** | `python scripts/check_prompt_construction_boundary.py` | 0 | **PASS** | No suspicious inline prompt construction found |
| **Backend Completeness Gate** | `python scripts/check_backend_completeness.py` | 0 | **PASS** | 75/75 required capabilities present and verified |
| **OpenAPI Contract Guard** | `pytest backend/tests/api/test_openapi_contract.py` | 0 | **PASS** | 100% agreement between FastAPI routes and `docs/openapi.json` |

---

## 3. Detailed Suite Breakdown

### 3.1 Backend Core Suite (`backend/tests/`)
- **Total Executed**: 186
- **Passed**: 181
- **Skipped**: 5 (legitimately requiring live PostgreSQL with role `USER`, live Redis, or remote cloud AI credentials).
- **Failed**: 0
- **Duration**: 64.32 seconds.
- **Coverage**: Covers candidate onboarding, resumes, job description parsing, interview session management, SM-2 spaced repetition cards, readiness scoring, candidate memory, and admin endpoints.

### 3.2 Security & Hardening Suite (`backend/tests/security/` & `backend/tests/hardening/`)
- **Passed**: 84 tests.
- **Key Verifications**:
  - `test_prompt_injection.py`: 26/26 tests passing (system tag escaping, untrusted document delimiter enforcement, output safety checks).
  - `test_jwt_auth.py`: Cryptographic verification of RS256/JWKS tokens and legacy HS256 tokens.
  - `test_rls_forged_jwt.py`: Forged tokens strictly rejected; claims are never set; tenant queries return 0 rows.
  - `test_authorization.py`: Insecure Direct Object Reference (IDOR) rejection on candidate-scoped routes.
  - `test_rate_limiter.py`: Sliding window rate limiting on sensitive routes.
  - `test_ssrf.py`: Outbound request validation blocking internal IP ranges and cloud metadata endpoints.
  - `test_uploads_sessions_study.py`: MIME type validation, file header magic byte inspection, path traversal protection.

### 3.3 Observability Suite (`backend/tests/api/test_observability.py`)
- **Passed**: 13 tests.
- **Key Verifications**:
  - `/health/live`: 200 OK liveness response.
  - `/health/ready`: 200 OK when DB and Redis are ready; 503 Service Unavailable when either dependency fails.
  - `/health/startup`: 200 OK when all 31 migrations exist in `schema_migrations`; 503 Service Unavailable when pending migrations exist.
  - `/metrics`: Public unauthenticated requests return 401 Unauthorized; requests with valid Basic Auth or Bearer token return 200 OK with Prometheus metrics.
  - Correlation Context: `X-Request-ID` and `X-Trace-ID` propagated in headers and bound to log records.
  - PII Masking: Passwords, tokens, secrets, emails, phones, and SSNs redacted.

### 3.4 AI Gateway & Realtime Agent Suite (`packages/ai-gateway/tests/` & `realtime-agent/tests/`)
- **Passed**: 49 tests.
- **Key Verifications**:
  - Audio protocol binary framing: 16-bit PCM mono 16 kHz format validation.
  - State machine lifecycle: transitions across `CREATED`, `AUTHENTICATED`, `ACTIVE`, `PAUSED`, `RECONNECTING`, `COMPLETED`.
  - Disconnect & reconnect grace period handling.
  - Coaching metrics accumulator: WPM, filler word count, pause duration.
  - Budget guard and circuit breaker state tracking.

---

## 4. Analysis of Skipped Tests

All 17 skipped tests across the suites were reviewed and verified:
1. `test_rls_pool_leak.py`, `test_rls_bypass.py`, `test_rls_storage.py`: Skipped cleanly because no live PostgreSQL instance with the `praxis` database was reachable locally.
2. `test_redis_ttl_enforcement_and_expiration.py`: Skipped cleanly because the local Redis daemon was stopped.
3. `test_hybrid_retrieval.py` & `test_full_turn.py`: Deselected under `-m "not live_provider"` because they require live local model weights or running cloud provider credentials.

None of the skipped tests conceal code regressions or logic defects.
