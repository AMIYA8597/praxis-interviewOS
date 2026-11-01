# PRAXIS Production Readiness Checklist (Phase 1)

**Status**: In Progress  
**Phase**: Phase 1 of 4 (Backend + Database)  
**Target Architecture**: Supabase (PostgreSQL + pgvector, Auth, Storage) + GCP Cloud Run (API, Realtime, Worker) + GCP Secret Manager + Memorystore Redis

---

## 1. Audit & Baseline Verification
- [x] Baseline CI reproduction and error recording (`docs/PHASE1_AUDIT.md`)
- [x] Living production readiness checklist initialized (`docs/PRODUCTION_READINESS.md`)

---

## 2. CI Breakers & Linting
- [x] Syntax/indentation error in `backend/tests/integration/test_rls_pool_leak.py` resolved (clean skip on non-postgres, 100% pass on Postgres)
- [x] Ruff target version and python requirement updated to `py311` in `pyproject.toml`
- [x] All 22 Ruff errors resolved across backend, realtime, and scripts
- [x] UTF-16 LE scripts re-encoded to UTF-8 without BOM (`doctor_env.py`, `_deprecated_apply_schema.py`)
- [x] Missing optional dependency guard added in `tests/integration/test_hybrid_mock.py`
- [x] **GATE 2**: `ruff check .` clean (0 errors) & 262/262 tests collected without errors

---

## 3. Configuration & Environment Model
- [x] Single typed settings source (`packages/config/settings.py`)
- [x] Connection pool defaults aligned with budget (`DB_POOL_SIZE=2`, `DB_MAX_OVERFLOW=3`)
- [x] Production settings fail closed at boot on invalid configuration (missing verifier, dev bypass, CORS wildcard, default creds)
- [x] Example environment files maintained without secrets (`.env.example`, `.env.staging.example`, `.env.production.example`)
- [x] Committed secrets scanning active in CI
- [x] **GATE 3**: Boot behavior with invalid vs valid environment verified

---

## 4. Database (Supabase PostgreSQL + pgvector)
- [x] Single source of truth established in `supabase/migrations/*.sql` (`backend/alembic/versions` confirmed retired)
- [x] All 31 migration filenames verified: zero duplicate version prefixes
- [x] Supabase connection pooler compatibility: asyncpg prepared statement cache disabled (`statement_cache_size=0`, `prepared_statement_cache_size=0`)
- [x] Least privilege: runtime connects as `praxis_app` (`NOBYPASSRLS`), no migrations ship hardcoded role passwords
- [x] Connection budget documented (`docs/DATABASE_CONNECTION_BUDGET.md`)
- [x] Disaster recovery & restore drill documented (`docs/DISASTER_RECOVERY.md`)
- [x] Fresh-DB migration clean and idempotent on live PostgreSQL instance (`python scripts/migrate.py` applied 31 migrations, 2nd run applied 0)
- [x] Schema inspection matches models: extensions, RLS + FORCE RLS on all tenant tables, HNSW indexes, FK cascades
- [x] **GATE 4**: Fresh-DB migrate clean + idempotent; full RLS suite passes on real Postgres

---

## 5. Auth & Authorization (RLS & Ownership Defense-in-Depth)
- [x] Cryptographic verification of Supabase access tokens (RS256 via JWKS, HS256 fallback)
- [x] RLS identity (`request.jwt.claims`) derived strictly from verified JWT
- [x] Verified JWT sets claims, forged JWT never sets claims (`test_rls_forged_jwt.py` passing)
- [x] Transaction-local claim isolation across pooled connections (`test_rls_pool_leak.py` passing)
- [x] Defense-in-depth: query-level candidate/tenant ownership on all scoped routes (no IDOR) (`test_authorization.py` passing)
- [x] Admin routes require verified admin role
- [x] **GATE 5**: Full RLS cross-tenant isolation proven on real Postgres instance (7/7 RLS tests passed in 1.02s)

---

## 6. API Completeness & Contract
- [x] Architecture boundaries green (`scripts/check_gateway_boundary.py` PASS)
- [x] Prompt construction boundary green (`scripts/check_prompt_construction_boundary.py` PASS)
- [x] No fabricated data gate green (`scripts/check_no_fake_data.py` PASS)
- [x] Backend completeness gate green (`scripts/check_backend_completeness.py` 75/75 PASS)
- [x] Committed OpenAPI spec generated and verified against live routes (`docs/openapi.json`)
- [x] Uniform error envelope (`code`, `message`, `request_id`, `retryable`)
- [x] **GATE 6**: Backend completeness + boundary checks + OpenAPI contract verification complete

---

## 7. Workers & Realtime Service
- [x] ARQ worker entrypoint and job wrapper with exponential backoff and idempotency (`backend/worker_settings.py`)
- [x] Worker HTTP health endpoint on `$PORT` (`/health/live`, `/health/ready`, `/health`)
- [x] Graceful SIGTERM shutdown handler
- [x] Redis TLS (`rediss://`) compatibility
- [x] Realtime state machine protocol (`realtime-agent/tests` 30 passed)
- [ ] **GATE 7**: Live worker health endpoint answers and recovers interrupted jobs on live Redis

---

## 8. Backend Security Baseline
- [x] Rate limiting middleware on sensitive routes (`backend/app/rate_limiter.py`)
- [x] File upload validation (MIME type, size, path traversal prevention)
- [x] SSRF guard on outbound requests
- [x] Security headers middleware (HSTS, X-Content-Type-Options, Referrer-Policy)
- [x] Prompt injection defense and output safety validation
- [x] Isolated execution sandbox for untrusted code
- [x] **GATE 8**: Security test suite passing (84/84 passing)

---

## 9. Observability
- [x] Structured JSON logging with correlation IDs (`request_id`, `trace_id`, `user_id`, `session_id`)
- [x] Sensitive credential / PII filtering in logging configuration (tokens, secrets, passwords, emails, phones, SSNs)
- [x] Health endpoints (`/health/live`, `/health/ready`, `/health/startup`)
- [x] Protected metrics endpoint (`/metrics` with Basic Auth / Bearer token, public unauthenticated scrape rejected with 401)
- [x] OpenTelemetry tracing bootstrap wired
- [x] **GATE 9**: Correlated JSON logs, PII masking, health endpoints, and protected metrics verified

---

## 10. Containers & Build
- [x] `docker/Dockerfile.api` multi-stage build, non-root user (uid 10001), healthcheck, OCI labels
- [x] `docker/Dockerfile.realtime` multi-stage build, non-root user (uid 10001), healthcheck, OCI labels
- [x] `docker/Dockerfile.worker` multi-stage build, non-root user (uid 10001), healthcheck, OCI labels
- [x] `docker/Dockerfile.sandbox` multi-stage build, non-root user (uid 10001), healthcheck, OCI labels
- [ ] **GATE 10**: All 4 images build from root and pass healthchecks on Docker host

---

## 11. Infrastructure as Code (Terraform)
- [x] `terraform fmt -check -recursive infra/` (clean)
- [x] `infra/bootstrap` initialized and validated (`terraform validate` PASS)
- [x] `infra/gcp` initialized and validated (`terraform validate` PASS)
- [ ] Terraform plan review against staging GCP project
- [ ] **GATE 11**: All IaC formatted, validated, and planned with no unexpected destroys

---

## 12. CI/CD Pipeline
- [x] Unmasked gates in `.github/workflows/ci.yml` (all 4 container builds + security suites)
- [x] Cloud Build pipeline (`cloudbuild.yaml`) with immutable digest tagging
- [ ] Full end-to-end CI pipeline green on GitHub Actions
- [ ] **GATE 12**: Automated build, test, and digest deployment ready

---

## 13. Staging Deployment & Verification
- [ ] Migrations applied to staging Supabase instance
- [ ] End-to-end journey executed via `scripts/clients/praxis_client.py`
- [ ] Failure drills executed and documented
- [ ] Performance baselines recorded (p50/p95 latency)
- [ ] **GATE 13**: Staging verification complete

---

## 14. Certification & Report
- [x] Staging certification document initialized (`docs/PRAXIS_STAGING_CERTIFICATION.md`)
- [ ] Final sign-off upon completion of all live infrastructure gates
- [ ] **FINAL GATE**: Phase 1 green across all gates
