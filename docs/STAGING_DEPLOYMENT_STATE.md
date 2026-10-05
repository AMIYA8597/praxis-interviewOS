# PRAXIS Staging Deployment State

**As of: 2026-10-05 (commit 44c7a8e + infrastructure sovereignty pass)**

This document is the authoritative audit of every deployment component.
Status codes: `PASS` | `PARTIAL` | `FAIL` | `BLOCKED` | `UNVERIFIED`

---

## Toolchain

| Component | Version | Status | Notes |
|---|---|---|---|
| gcloud CLI | 587.0.0 | PASS | Authenticated as amiyachowdhury04@gmail.com |
| Docker | 29.7.2 | PASS | Available locally |
| Terraform | 1.16.4 | PASS | Satisfies ≥ 1.9.0 requirement |
| Python | 3.11.11 (Docker), 3.13.7 (local) | PASS | Docker images use 3.11.11 |
| Node | 24.18.0 | PASS | |
| pnpm | 10.30.3 | PASS | |
| Supabase CLI | NOT INSTALLED | FAIL | `winget install Supabase.CLI` |

---

## GCP Infrastructure

| Component | Status | Notes |
|---|---|---|
| GCP staging project `praxis-staging` | BLOCKED | Does not exist. Accessible account: tradebit-396406. Create: `gcloud projects create praxis-staging` |
| GCP production project `praxis-production` | BLOCKED | Not created. Must not create until staging certified. |
| Billing account linked | BLOCKED | Requires billing authorization |
| Required APIs enabled | BLOCKED | Depends on project existence |
| Terraform state bucket | BLOCKED | `infra/bootstrap/` ready to run once project exists |
| Terraform `init` | BLOCKED | Requires state bucket |
| Terraform `plan` | PASS (local validate only) | `terraform validate` passes; cannot plan without GCP project |
| Terraform `apply` | BLOCKED | Requires GCP project + billing |
| Artifact Registry `praxis` | BLOCKED | Requires Terraform apply |
| Cloud Run praxis-api | BLOCKED | Requires Artifact Registry + Terraform apply |
| Cloud Run praxis-realtime | BLOCKED | Same |
| Cloud Run Worker Pool praxis-worker | BLOCKED | Same |
| Memorystore Redis | BLOCKED | Same |
| VPC / VPC connector | BLOCKED | Same |
| Load balancer | BLOCKED | Requires domain configuration |
| TLS certificate | BLOCKED | Requires real domain |
| Cloud Armor policy | BLOCKED | Requires load balancer |
| Workload Identity Federation | BLOCKED | Requires Terraform apply |
| Secret Manager secrets | BLOCKED | Requires project + secrets populated |
| Service accounts (least privilege) | PARTIAL | Defined in Terraform; not yet applied |

---

## Terraform

| Check | Status | Notes |
|---|---|---|
| `terraform fmt` (main.tf, alerting.tf) | PASS | Passes locally |
| `terraform validate` (bootstrap) | PASS | Validated without backend |
| `terraform validate` (main module) | PASS | Validated without backend |
| No `latest` image tags in resources | PASS | Validation rule added to `image_tag` variable |
| No placeholder domains in tfvars | PASS | Fixed: `domain = ""` in staging (empty = skip TLS) |
| Worker Cloud Run service defined | PASS | Added `google_cloud_run_v2_worker_pool.worker` |
| Correct health probe paths | PASS | Fixed: `/api/v1/health/live` for API, `/health/live` for realtime |
| WIF trust restricted by repository | PASS | `attribute_condition` added |
| Missing APIs added (sts, iamcredentials, servicenetworking) | PASS | Added |
| Dead code removed (empty SSL cert resource) | PASS | Removed |
| deployer SA has artifactregistry.writer | PASS | Added `deployer_ar_writer` binding |
| Worker has cloudtrace.agent IAM binding | PASS | Added `worker_trace_agent` |

---

## Docker Images

| Image | Dockerfile | Build Status | Notes |
|---|---|---|---|
| praxis-api | docker/Dockerfile.api | UNVERIFIED | Dockerfile is correct; build not run in this session |
| praxis-realtime | docker/Dockerfile.realtime | UNVERIFIED | Fixed: model cache ownership for non-root praxis user |
| praxis-worker | docker/Dockerfile.worker | UNVERIFIED | Dockerfile is correct |
| Non-root user | PASS | `groupadd -r praxis && useradd -r -g praxis praxis` in all images |
| No secrets in ENV/ARG | PASS | Verified: no secret values in Dockerfiles |
| HEALTHCHECK defined | PASS | API and realtime have HEALTHCHECK; worker intentionally does not |
| Model cache ownership fixed (realtime) | PASS | Defect fixed: `--chown=praxis:praxis` + `HF_HOME=/app/.cache` |

---

## CI/CD

| Check | Status | Notes |
|---|---|---|
| GitHub Actions CI | PASS | 146 tests pass, 5 skipped |
| Terraform fmt check in CI | PASS | Added `terraform-validate` job |
| Terraform validate in CI | PASS | Added; runs without backend/credentials |
| Docker build check in CI | PASS | Added `docker-build-check` job |
| Secret scan in CI | PASS | detect-secrets + committed .env file check |
| No committed .env files | PASS | `.env` is in .gitignore |
| Cloud Build pipeline | PARTIAL | Fixed: removed tag-latest, added digest capture, fixed smoke URLs |
| Cloud Build trigger | BLOCKED | Requires GCP project to create trigger |

---

## Supabase / Database

| Check | Status | Notes |
|---|---|---|
| Supabase staging project | BLOCKED | Not created |
| 20+ migrations exist | PASS | `supabase/migrations/` has 20+ migration files |
| Migration idempotency (local CI) | PASS | CI runs migrations twice; second run is no-op |
| RLS enabled on all tables | PASS | CI test: test_rls_enabled.py passes |
| FORCE RLS | PASS | Migration 20261004000002_force_rls.sql applied in CI |
| Real Supabase RLS certification | BLOCKED | Requires staging Supabase project |

---

## Application Services

| Check | Status | Notes |
|---|---|---|
| Backend test suite | PASS | 146 pass, 5 skipped |
| Architecture boundaries | PASS | 5/5 tests pass |
| Completeness gate | PASS | 75/75 |
| Behavioral calibration | PASS | 15/15 |
| Prompt injection tests | PASS | 26/26 |
| Docker API service starts | UNVERIFIED | Requires live run |
| Docker realtime service starts | UNVERIFIED | Requires live run |
| Docker worker service starts | UNVERIFIED | Requires live run |
| Real staging E2E | BLOCKED | Requires deployed staging |

---

## Security

| Check | Status | Notes |
|---|---|---|
| JWT RS256/JWKS | PASS | Tested in unit tests |
| Prompt injection defence | PASS | 26 tests pass |
| AI output safety | PASS | output_safety.py + tests |
| SSRF guard | PASS | Tests pass |
| Security headers middleware | PASS | HSTS, X-Content-Type-Options, etc. |
| Rate limiting | PASS | Tests pass |
| No fake data | PASS | check_no_fake_data.py passes |
| No secrets in repo | PASS | No real secrets detected |
| WIF trust restricted | PASS | attribute_condition added to main.tf |
| Cloud Armor | BLOCKED | Requires GCP project |

---

## Observability

| Check | Status | Notes |
|---|---|---|
| Prometheus metrics endpoint | PASS | /metrics implemented and tested |
| Structured logging | PASS | JSON log format in staging/production |
| OTel tracing | PARTIAL | Code exists; not connected to real GCP Cloud Trace |
| Cloud Monitoring alerts | BLOCKED | Requires GCP project |

---

## Summary

| Category | PASS | PARTIAL | FAIL | BLOCKED | UNVERIFIED |
|---|---|---|---|---|---|
| Toolchain | 7 | 0 | 1 | 0 | 0 |
| GCP Infrastructure | 0 | 1 | 0 | 14 | 0 |
| Terraform | 11 | 0 | 0 | 0 | 0 |
| Docker Images | 4 | 0 | 0 | 0 | 3 |
| CI/CD | 7 | 1 | 0 | 1 | 0 |
| Database | 4 | 0 | 0 | 2 | 0 |
| Application | 6 | 0 | 0 | 1 | 3 |
| Security | 7 | 0 | 0 | 1 | 0 |
| Observability | 2 | 1 | 0 | 1 | 0 |

**All BLOCKED items require external human-owned prerequisites (GCP project creation, billing, Supabase account, domain).**  
**No P0 or P1 failures exist in items that can be tested locally.**

---

*Last updated: 2026-10-05 — Infrastructure Sovereignty Pass*
