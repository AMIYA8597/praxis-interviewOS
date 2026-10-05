# PRAXIS Staging Certification

**Status: PRE-CERTIFICATION — Infrastructure not yet provisioned**

This document tracks staging certification state. It will be updated to CERTIFIED
after all BLOCKED items are resolved and real E2E verification completes.

---

## Certification Levels Used

| Symbol | Meaning |
|---|---|
| PASS | Verified working |
| PASS_WITH_LIMITATION | Working with documented limitation |
| FAIL | Failed; must be resolved before certification |
| BLOCKED | Cannot complete without external prerequisite |
| UNVERIFIED | Not yet tested |
| NOT_APPLICABLE | Not relevant to this deployment |

---

## Infrastructure

| Area | Status | Evidence / Notes |
|---|---|---|
| GCP staging project | BLOCKED | `praxis-staging` does not exist. Requires billing authorization. |
| Terraform state bucket | BLOCKED | Depends on project existence. `infra/bootstrap/` ready. |
| Terraform validate | PASS | `terraform validate` passes for both bootstrap and main module. |
| Artifact Registry | BLOCKED | Requires Terraform apply. |
| VPC + VPC connector | BLOCKED | Requires Terraform apply. |
| Memorystore Redis | BLOCKED | Requires Terraform apply. |
| Cloud Run praxis-api | BLOCKED | Requires images + Terraform apply. |
| Cloud Run praxis-realtime | BLOCKED | Requires images + Terraform apply. |
| Cloud Run praxis-worker | BLOCKED | Requires images + Terraform apply. |
| Load Balancer | BLOCKED | Requires domain. `domain = ""` skips cert creation. |
| TLS certificate | BLOCKED | Requires real domain ownership. |
| Cloud Armor | BLOCKED | Requires load balancer. |

---

## Images

| Image | Status | Notes |
|---|---|---|
| praxis-api built | UNVERIFIED | Docker available; build not run in this session. |
| praxis-realtime built | UNVERIFIED | Defect fixed: model cache ownership for non-root user. |
| praxis-worker built | UNVERIFIED | |
| No secrets in images | PASS | Verified by audit; no secret values in Dockerfiles or ENV. |
| Non-root user | PASS | All images use `USER praxis`. |
| Immutable SHA tag | PASS | Validation rule in Terraform rejects mutable tags. |

---

## Database

| Check | Status | Evidence |
|---|---|---|
| 20+ migrations | PASS | `supabase/migrations/` has 20+ files. |
| Migration idempotency | PASS | CI runs migrations twice; second run is no-op. |
| RLS enabled (all tables) | PASS | CI: test_rls_enabled.py — 6/6 pass. |
| FORCE RLS | PASS | Migration 20261004000002_force_rls.sql. |
| Real Supabase staging | BLOCKED | Requires Supabase staging project creation. |
| Multi-user RLS isolation | BLOCKED | Requires real staging database. |

---

## Application Tests

| Suite | Status | Count | Command |
|---|---|---|---|
| Backend unit/integration | PASS | 146 pass, 5 skip | `pytest backend/tests -m "not live_provider"` |
| Architecture boundaries | PASS | 5/5 | `pytest backend/tests/test_architecture_boundaries.py` |
| Completeness gate | PASS | 75/75 | `python scripts/check_backend_completeness.py` |
| Behavioral calibration | PASS | 15/15 | `pytest backend/tests/evaluation/` |
| Prompt injection | PASS | 26/26 | `pytest backend/tests/security/test_prompt_injection.py` |
| RLS enabled | PASS | 6/6 | `pytest tests/security/test_rls_enabled.py` |
| Gateway boundary | PASS | — | `python scripts/check_gateway_boundary.py` |
| No fake data | PASS | — | `python scripts/check_no_fake_data.py` |

---

## Skipped Tests (re-evaluation)

| Test | Reason Skipped | Infrastructure Required | Now Executable? |
|---|---|---|---|
| `test_rls_pool_leak.py` | Requires live DATABASE_URL | Real PostgreSQL with role "USER" | No — requires Supabase staging |
| `test_rls_isolation.py` (backend) | Requires live DATABASE_URL | Real PostgreSQL + two test users | No — requires Supabase staging |
| `test_rls_storage.py` | Requires live Supabase Storage | Supabase staging project | No |
| `test_rls_bypass.py` (integration) | Requires live DATABASE_URL | Real PostgreSQL | No |
| (1 more from ai-gateway) | Requires real provider API key | GROQ_API_KEY or OPENAI_API_KEY | No |

All 5 skips are legitimate — they require live infrastructure not yet provisioned. None are hiding real failures.

---

## Security

| Check | Status | Evidence |
|---|---|---|
| JWT RS256/JWKS | PASS | Unit tests: test_jwt_auth.py |
| Prompt injection defence | PASS | 26/26 tests |
| AI output safety | PASS | output_safety.py + tests |
| SSRF guard | PASS | test_ssrf.py passes |
| Security headers | PASS | middleware.py — verified in tests |
| Rate limiting | PASS | rate_limiter.py — verified in tests |
| No hardcoded secrets | PASS | Audit + detect-secrets scan |
| WIF trust restriction | PASS | attribute_condition added to Terraform |
| Cloud Armor WAF | BLOCKED | Requires GCP project |
| Staging penetration test | BLOCKED | Requires deployed staging |

---

## Observability

| Check | Status | Notes |
|---|---|---|
| Prometheus metrics endpoint | PASS | /metrics — 16 counters/histograms |
| Structured logging (JSON) | PASS | JSON format in staging/production APP_ENV |
| Request ID propagation | PASS | RequestIdMiddleware + X-Request-ID header |
| OTel tracing | PASS_WITH_LIMITATION | Code exists; not connected to real GCP Cloud Trace yet |
| Cloud Monitoring dashboards | BLOCKED | Requires GCP project |
| Alerting policies | BLOCKED | Requires GCP project |

---

## Performance

| Metric | Target | Actual | Status |
|---|---|---|---|
| API p95 latency | < 500ms | UNVERIFIED | BLOCKED — no deployed staging |
| DB query p95 | < 100ms | UNVERIFIED | BLOCKED |
| Resume processing | < 30s | UNVERIFIED | BLOCKED |
| STT per chunk | < 2s | UNVERIFIED | BLOCKED |
| WebSocket cold connect | < 5s | UNVERIFIED | BLOCKED |

---

## AI Providers

| Check | Status | Notes |
|---|---|---|
| Budget guard | PASS | Tests pass with mock provider |
| Circuit breaker | PASS | Tests pass |
| Output safety | PASS | output_safety.py + tests |
| Real Groq/OpenAI staging | BLOCKED | API keys not in Secret Manager |
| Provider fallback chain | PASS | Unit tests with mock providers |

---

## CI/CD

| Check | Status | Notes |
|---|---|---|
| GitHub Actions CI pass | PASS | 146 tests, all checks green |
| Cloud Build trigger configured | BLOCKED | Requires GCP project |
| Smoke test script | PASS | scripts/smoke_test.py — no hardcoded URLs |
| Release manifest generator | PASS | scripts/generate_release_manifest.py |
| Immutable image tagging | PASS | tag-latest removed from Cloud Build |
| Rollback procedure documented | PASS | docs/PRODUCTION_RUNBOOK.md |

---

## Known Limitations

1. **GCP not provisioned** — All infrastructure is Terraform-defined and validated but not deployed. All BLOCKED items depend on this.
2. **Supabase staging not created** — RLS certification against real database pending.
3. **No real domain** — TLS cert and Cloud Armor not testable until domain is configured.
4. **Docker images not built** — Dockerfiles are correct; actual build verification requires CI run after Artifact Registry exists.
5. **AI providers unconfigured** — No API keys in Secret Manager; real AI acceptance blocked.
6. **Performance unverified** — No p50/p95 measurements; staging must be deployed first.
7. **Load testing not run** — Requires deployed staging environment.

---

## Certification Gate

Staging is **NOT certified** until all of the following are PASS or PASS_WITH_LIMITATION:

- [ ] GCP project provisioned and Terraform applied
- [ ] Docker images built, pushed, and digests recorded
- [ ] Supabase staging project created and migrations applied
- [ ] Multi-user RLS isolation test passes against real Supabase
- [ ] All 3 Cloud Run services start and pass health checks
- [ ] Smoke test passes against real staging URLs
- [ ] At least one real AI provider acceptance test passes
- [ ] No P0 or P1 failures remain

---

## Certifier Sign-off

This document will be signed by a human reviewer after the above gate passes.

```
Certifier: ___________________________
Date: ___________________________
Commit: ___________________________
API digest: ___________________________
Realtime digest: ___________________________
Worker digest: ___________________________
```

---

*Generated: 2026-10-05 — Infrastructure Sovereignty Pass*
*Update after each major deployment milestone.*
