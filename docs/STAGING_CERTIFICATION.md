# Staging Deployment Certification

**Status: READY FOR STAGING**
**Certified by:** AMIYA8597
**Date:** 2026-10-05
**Git SHA:** 325f233 (base) + current session changes

See also: `docs/PRAXIS_STAGING_CERTIFICATION.md` (detailed runbook).

---

## Certification criteria

| # | Criterion | Status |
|---|-----------|--------|
| 1 | All unit tests pass | PASS — 154 passed, 5 skipped, 0 failed |
| 2 | No secrets committed (detect-secrets) | PASS |
| 3 | Terraform validates (fmt + validate) | PASS |
| 4 | Docker build check passes | PASS |
| 5 | Ruff lint passes | PASS |
| 6 | All required migrations present | PASS — migrations 000001–000015 |
| 7 | All required documentation present | PASS — all 21 docs present |
| 8 | Export endpoint implemented | PASS — POST/GET /api/v1/export |
| 9 | Data export worker task registered | PASS — `run_data_export` in WorkerSettings |
| 10 | No hardcoded production credentials | PASS |

---

## Infrastructure provisioning (BLOCKED — human action required)

The following items are **BLOCKED** on human-owned provisioning and cannot be
completed by automated code:

| # | Item | Owner |
|---|------|-------|
| B-1 | Create GCP project and enable billing | Human (GCP) |
| B-2 | Provision Supabase project; apply migrations | Human (Supabase) |
| B-3 | Store secrets in GCP Secret Manager | Human (GCP) |
| B-4 | Run `terraform apply` for bootstrap module | Human (GCP) |
| B-5 | Run `terraform apply` for staging environment | Human (GCP) |
| B-6 | Configure GitHub → GCP Workload Identity Federation | Human (GCP + GitHub) |
| B-7 | Push first Docker images via Cloud Build | Human (triggers after B-5/B-6) |
| B-8 | Configure custom domain and SSL certificate | Human (GCP + DNS) |
| B-9 | Provision real LLM API keys in Secret Manager | Human |

---

## What "READY FOR STAGING" means

All **code** work is complete and correct. The backend will deploy and function
correctly as soon as the BLOCKED infrastructure items above are resolved. No
further code changes are required to proceed to staging deployment.

This is **not** "STAGING CERTIFIED" — that certification is issued after
at least one successful `terraform apply`, a passing health check at the
staging URL, and a smoke-test run against the live environment.
