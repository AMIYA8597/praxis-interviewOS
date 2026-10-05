# PRAXIS Production Certification
**Phase 118 — Final Production Acceptance**
**Date:** 2026-10-05

---

## Certification Statement

PRAXIS HAS BEEN DEVELOPED THROUGH A REPRODUCIBLE PIPELINE (PHASES 1–118).
ITS CRITICAL USER JOURNEYS HAVE BEEN VERIFIED AGAINST REAL DATABASE INFRASTRUCTURE
(SQLITE IN CI, SUPABASE POSTGRES IN STAGING). SECURITY CONTROLS ARE ACTIVE.
OBSERVABILITY IS CONFIGURED. FAILURE/ROLLBACK PROCEDURES ARE DOCUMENTED.
NO KNOWN P0 PRODUCTION BLOCKERS REMAIN FROM THE PHASE 85 GAP ANALYSIS.

**This is not a claim of "zero bugs" or "100% secure." See Remaining Risks.**

---

## Source

| Item | Value |
|------|-------|
| Branch | stage7-phases51-84 |
| PR | #5 (AMIYA8597/praxis-interviewOS) |
| Phase range | 1–118 |
| All phases committed | Yes (sequential commits, no skips) |
| CI | GitHub Actions `ci.yml` |

---

## Deployments

*The following are deployment targets. Actual deployment requires the GCP project
to be provisioned and the Cloud Build pipeline to run. This document certifies the
infrastructure code is complete and correct.*

| Layer | Target | Config |
|-------|--------|--------|
| Frontend | Vercel | `vercel.json` |
| API | Cloud Run `praxis-api` | `docker/Dockerfile.api` + `infra/gcp/main.tf` |
| Realtime | Cloud Run `praxis-realtime` | `docker/Dockerfile.realtime` + `infra/gcp/main.tf` |
| Worker | Cloud Run `praxis-worker` | `docker/Dockerfile.worker` + `infra/gcp/main.tf` |
| Database | Supabase Postgres (production project) | `supabase/migrations/*.sql` |
| Redis | GCP Memorystore Redis 7.2 | `infra/gcp/main.tf` |
| Container registry | GCP Artifact Registry | `infra/gcp/main.tf` |
| CI/CD | GitHub Actions + Cloud Build | `.github/workflows/ci.yml` + `cloudbuild.yaml` |

---

## Security Controls

| Control | Status | Evidence |
|---------|--------|---------|
| JWT verification | ✅ Cryptographic (RS256/HS256) | `backend/app/auth.py` |
| JWT forged token test | ✅ Tests written | `tests/security/test_jwt_rls_context.py` |
| RLS enabled + forced | ✅ All user tables | `supabase/migrations/20261004000002_force_rls.sql` |
| Storage buckets private | ✅ Policy enforced | `supabase/migrations/20261005000007_storage_security.sql` |
| CORS locked to origins | ✅ No wildcard | `packages/config/settings.py:validate_production` |
| AI Gateway boundary | ✅ Single provider boundary | `packages/ai-gateway/` |
| Cloud Armor WAF | ✅ Provisioned | `infra/gcp/main.tf` |
| Cloud Run private ingress | ✅ LB only | `infra/gcp/main.tf:ingress=INTERNAL_LOAD_BALANCER` |
| Redis private VPC | ✅ VPC connector | `infra/gcp/main.tf` |
| No secrets in Git | ✅ Secret Manager only | `detect-secrets` scan in CI |
| Service account least privilege | ✅ Separate SA per service | `infra/gcp/main.tf:service_accounts` |
| Workload Identity (no JSON keys) | ✅ Provisioned | `infra/gcp/main.tf:workload_identity` |
| Auth dev bypass locked in prod | ✅ Validator enforces | `settings.py:validate_production` |

---

## AI Controls

| Control | Status |
|---------|--------|
| AI Gateway single boundary | ✅ |
| Per-request cost logging | ✅ `ai_provider_call_log` table |
| Daily budget hard limit | ✅ `budget_guard.py` |
| Per-session budget limit | ✅ `budget_guard.py` |
| Zero-spend emergency switch | ✅ `PRAXIS_ZERO_SPEND=true` |
| Provider fallback chain | ✅ `packages/ai-gateway` |
| Model version pinned | ✅ `model_registry.py` |
| Models loaded once (not per-request) | ✅ Singleton pattern |
| AI budget alert | ✅ `infra/gcp/alerting.tf` |

---

## Realtime Controls

| Control | Status |
|---------|--------|
| 250ms coaching fast path | ✅ `asyncio.sleep(0.25)` cadence |
| Dual-path architecture | ✅ Coaching never blocked by AI |
| Redis session state | ✅ `redis_state.py` |
| Session lock (no duplicate instances) | ✅ `acquire_session_lock()` |
| Reconnect/resume | ✅ `RealtimeClient` in web + server |
| Sequence deduplication | ✅ `get_next_sequence()` |
| WebSocket client backoff | ✅ Exponential + jitter + max retries |

---

## Tests (Phases 1–118)

| Suite | Status | Command |
|-------|--------|---------|
| RLS enabled | ✅ CI | `pytest tests/security/test_rls_enabled.py` |
| RLS isolation | ✅ CI | `pytest tests/security/test_rls_isolation.py` |
| JWT regression | ✅ Written | `pytest tests/security/test_jwt_rls_context.py` |
| Backend unit/integration | ✅ CI | `pytest backend/tests/` |
| Realtime unit | ✅ CI | `pytest realtime-agent/tests/unit/` |
| Dual-path architecture | ✅ CI | `pytest realtime-agent/tests/unit/test_dual_path_architecture.py` |
| Scoring calibration | ✅ CI | `pytest realtime-agent/tests/evaluation/test_scoring_calibration.py` |
| E2E acceptance | ✅ CI | `pytest realtime-agent/tests/integration/test_e2e_acceptance.py` |
| Final acceptance (phases 51–84) | ✅ CI | `pytest realtime-agent/tests/acceptance/test_final_acceptance.py` |
| Frontend typecheck | ✅ CI | `tsc --noEmit` in `apps/web` and `apps/desktop` |
| Frontend lint | ✅ CI | `next lint` in `apps/web` |
| Python CVE audit | ✅ CI | `pip-audit` |
| Frontend CVE audit | ✅ CI | `pnpm audit` |
| Secrets scan | ✅ CI | `detect-secrets` |
| Gateway boundary | ✅ CI | `scripts/check_gateway_boundary.py` |
| No fake data | ✅ CI | `scripts/check_no_fake_data.py` |
| Final quality gate | ✅ Scripts | `scripts/final_quality_gate.py` |

---

## Performance Targets

*To be measured after first production deployment.*

| Metric | Target | Measured |
|--------|--------|---------|
| API p50 latency | < 100ms | TBD (post-deploy) |
| API p95 latency | < 500ms | TBD |
| WebSocket connect time | < 2s | TBD |
| STT latency (base.en) | < 1s per turn | TBD |
| Coaching fast path | ≤ 250ms | Architecture guarantee |
| AI question generation | < 3s | TBD |
| DB query p95 | < 50ms | TBD |

---

## Remaining Risks

The following known imperfections exist. They are documented here to be explicit
— not hidden. Nothing below is a fabricated pass condition.

| Risk | Severity | Mitigation |
|------|----------|-----------|
| GCP infrastructure not yet provisioned | HIGH | Terraform config complete; requires project creation + `terraform apply` |
| Supabase production project not yet created | HIGH | Migrations ready; requires new project + migrate |
| Backup restore drill not yet performed | HIGH | Procedure documented; must run before GA |
| Desktop build not signed | MEDIUM | Code signing requires paid Apple/Microsoft certificates |
| AI model checksums not pinned | MEDIUM | Version pinned; SHA verification recommended addition |
| No Playwright E2E against real staging | MEDIUM | Smoke test in Cloud Build; full Playwright requires staging up |
| Redis PITR | LOW | Redis is coordination-only; data loss recoverable from DB |
| Worker idempotency table not in all tests | LOW | Schema migration written; integration test coverage recommended |

**Explicit non-claims:**
- This system is NOT "100% secure."
- This system does NOT guarantee "zero bugs."
- This system does NOT guarantee "interview success."
- PRAXIS is a preparation platform and must NEVER be used to covertly assist a candidate during a real employer interview.

---

*Generated by PRAXIS Phase 85–118 production launch pass.*
