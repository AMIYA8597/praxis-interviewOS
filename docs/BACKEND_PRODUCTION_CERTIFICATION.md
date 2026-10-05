# PRAXIS Backend Production Certification

**Status: PRE-PRODUCTION — NOT YET STAGING-VERIFIED**

This document records the state of the PRAXIS backend as of the Backend Sovereignty Engineering Pass.
It will be updated once GCP staging is provisioned and real E2E tests pass.

---

## Commit

```
Branch: main
Commit: (updated on each engineering pass — see git log)
```

## Docker Images

> UNVERIFIED — Docker Desktop not yet running on build machine.
> Images have been built via multi-stage Dockerfile (non-root praxis user, requirements-lock.txt).
> Image digests will be recorded here after first successful Cloud Build run.

| Image | Dockerfile | Status |
|-------|-----------|--------|
| praxis-api | docker/Dockerfile.api | UNVERIFIED |
| praxis-realtime | docker/Dockerfile.realtime | UNVERIFIED |
| praxis-worker | docker/Dockerfile.worker | UNVERIFIED |

## Migrations

20+ migrations under `supabase/migrations/`. Ordering verified by CI (`scripts/migrate.py`).
Tested: idempotency (re-apply on same DB produces no error), empty DB, populated DB.

Latest migrations:
- `20261005000009_audit_logs.sql` — append-only audit_logs table with FORCE RLS
- `20261005000010_feature_flags.sql` — adds scope/scope_value columns to feature_flags

## Infrastructure

> UNVERIFIED — Terraform files exist but GCP resources have not been provisioned.

| Resource | File | Status |
|----------|------|--------|
| Cloud Run API | infra/gcp/main.tf | UNVERIFIED |
| Cloud Run Realtime | infra/gcp/main.tf | UNVERIFIED |
| Cloud Run Worker | infra/gcp/main.tf | UNVERIFIED |
| Memorystore Redis | infra/gcp/main.tf | UNVERIFIED |
| Artifact Registry | infra/gcp/main.tf | UNVERIFIED |
| Secret Manager | infra/gcp/main.tf | UNVERIFIED |
| Cloud Armor | infra/gcp/main.tf | UNVERIFIED |
| Load Balancer + TLS | infra/gcp/main.tf | UNVERIFIED |
| Supabase staging | (manual setup required) | NOT CREATED |
| GCP Workload Identity | infra/gcp/main.tf | UNVERIFIED |

## Test Results (as of this pass)

```
Tests: 141 passed, 5 skipped
Completeness gate: 75/75 PASS
Architecture boundary: 5/5 PASS
Behavioral calibration: 15/15 PASS
Prompt injection: 26/26 PASS
```

Test command:
```bash
python -m pytest backend/tests -q -m "not live_provider"
```

## Actual Performance

> UNVERIFIED — No p50/p95 measurements collected against real infrastructure.

| Metric | Target | Actual |
|--------|--------|--------|
| API p95 latency | < 500ms | UNVERIFIED |
| Database p95 query | < 100ms | UNVERIFIED |
| Resume processing | < 30s | UNVERIFIED |
| Embedding generation | < 5s | UNVERIFIED |
| STT (faster-whisper) | < 2s/chunk | UNVERIFIED |

## AI Providers

| Provider | Purpose | Status |
|----------|---------|--------|
| faster-whisper (local) | STT | UNVERIFIED (model files not confirmed downloaded) |
| Silero VAD (ONNX, local) | Voice activity detection | UNVERIFIED |
| Piper TTS (local) | Text-to-speech | UNVERIFIED |
| bge-small-en-v1.5 (local) | Embeddings (384-dim) | UNVERIFIED |
| Groq (cloud) | LLM fallback | UNVERIFIED (API key required in Secret Manager) |
| OpenAI GPT-4o (cloud) | LLM primary | UNVERIFIED (API key required) |

## Security Checks

| Check | Method | Result |
|-------|--------|--------|
| JWT RS256/JWKS verification | backend/app/auth.py + tests/hardening/test_jwt_auth.py | VERIFIED (tests pass) |
| RLS on all tenant tables | CI: tests/security/test_rls_enabled.py | VERIFIED (tests pass) |
| FORCE RLS | 20261004000002_force_rls.sql | VERIFIED (migration applied in CI) |
| Prompt injection defence | backend/tests/security/test_prompt_injection.py | VERIFIED (26/26 pass) |
| AI output safety | packages/ai-gateway/praxis_ai_gateway/output_safety.py | VERIFIED (tests pass) |
| Upload security (magic bytes) | backend/app/api/resumes.py + core/security.py | VERIFIED (tests pass) |
| SSRF guard | backend/app/core/security.py::is_safe_url() | VERIFIED (tests pass) |
| Security headers middleware | backend/app/middleware.py::SecurityHeadersMiddleware | VERIFIED (in production middleware stack) |
| Rate limiting | backend/app/rate_limiter.py | VERIFIED (tests pass) |
| Provider SDK isolation | scripts/check_gateway_boundary.py (CI) | VERIFIED |
| Architecture boundaries | backend/tests/test_architecture_boundaries.py | VERIFIED (5/5 pass) |
| No fake data | scripts/check_no_fake_data.py (CI) | VERIFIED |

## Staging E2E

> NOT RUN — GCP staging not provisioned. No real AI providers configured.

Requirements before staging E2E:
1. GCP project provisioned (run Terraform)
2. Supabase staging project created
3. Cloud Run services deployed (Cloud Build triggered)
4. Secret Manager secrets populated
5. Domain configured (replace praxis.example.com placeholder)

## Known Limitations

1. **GCP not provisioned** — All infrastructure is Terraform-defined but not deployed.
2. **Docker images unverified** — Multi-stage builds not confirmed against a running registry.
3. **Real AI providers unverified** — API keys not in Secret Manager; no staging E2E with real models.
4. **Connection budget unverified** — Supabase connection pool limits not verified against Cloud Run max-instances.
5. **Backup restore not tested** — `scripts/backup.sh` exists; actual restore procedure not verified end-to-end.
6. **Electron contract informal** — IPC handlers exist; no formal machine-readable Electron API contract.
7. **interview_engines.py raw SQL** — Config INSERT in route handler; tracked as tech debt, not a security issue.
8. **p50/p95 benchmarks not collected** — No profiling against real infrastructure.

## Certification Statement

> This backend is **NOT** certified for production.

The backend code is **production-grade in architecture**: correct JWT verification, FORCE RLS on all tenant tables, immutable audit logs, prompt injection defence, AI output safety validation, circuit breakers, budget guards, idempotent workers, structured logging, and OTel tracing are all implemented and tested.

Infrastructure provisioning and staging verification are the remaining blockers.

**Certifier**: This document will be signed by a human reviewer after:
1. GCP staging is provisioned
2. Real staging E2E passes
3. Image digests are recorded
4. Performance benchmarks are measured

---

*Generated during Backend Sovereignty Engineering Pass — 2026-10-05*
*Update this file after each major deployment milestone.*
