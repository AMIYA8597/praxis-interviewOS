# PRAXIS Production Gap Analysis
**Phase 85 — Baseline Audit**
**Date:** 2026-10-05
**Branch audited:** stage7-phases51-84 (PR #5 vs main)

---

## Summary

Phases 1–84 have built all core product features. This document captures every gap that must
be resolved before the system can receive real user traffic in production.

---

## P0 BLOCKERS — Must fix before any production traffic

| ID | Area | Finding | Fix |
|----|------|---------|-----|
| P0-1 | Containers | No production Dockerfiles exist. `docker-compose.yml` only has dev services (postgres/redis/jaeger/worker). No `Dockerfile` for `praxis-api`, `praxis-realtime`, or `praxis-worker`. | Phase 89 |
| P0-2 | Cloud infra | No GCP infrastructure code exists (`infra/` directory absent). Cloud Run, Load Balancer, Artifact Registry, IAM, Memorystore all unprovisioned. | Phases 99–108 |
| P0-3 | Vercel | No `vercel.json`, no environment variable configuration, no production deployment record. | Phase 112–113 |
| P0-4 | Python lock | `backend/requirements.txt` pins direct deps but not transitive deps. No `uv.lock` or equivalent. CI installs arbitrary latest transitive packages. | Phase 88 |
| P0-5 | Next.js version | `next: 15.0.0` — this is a pre-release/early patch. Current stable is 15.3.x. Must upgrade. | Phase 87 |
| P0-6 | DB connection mode | No documented connection pool config for Cloud Run → Supabase. Cloud Run spins up many instances; misconfigured pooling causes connection exhaustion. | Phase 94 |
| P0-7 | Budget safety | No hard AI spend limits, no circuit breaker, no per-session token cap enforced in code. Runaway usage would spend money silently. | Phase 93 |
| P0-8 | Storage buckets | `supabase/migrations/20260907235803_storage_buckets.sql` creates buckets but public access policy not audited. Resume files must never be public. | Phase 96 |
| P0-9 | Realtime session state | `session_state_log` writes can silently fail; no session resumption across Cloud Run instances. Phase 103/104 must implement Redis-backed session coordination. | Phase 103–104 |
| P0-10 | API client | No unified typed API client in the Next.js app. Raw fetch scattered; auth token attachment inconsistent; no retry/timeout policy. | Phase 115 |

---

## P1 HIGH — Required before stable production

| ID | Area | Finding | Fix |
|----|------|---------|-----|
| P1-1 | GCP IAM | No service accounts defined. Default Compute Engine SA would be used. | Phase 100 |
| P1-2 | Artifact Registry | No private container registry. Images have no home. | Phase 101 |
| P1-3 | Realtime web client | No production WebSocket client with reconnect/backoff/state machine. | Phase 116 |
| P1-4 | Observability | OpenTelemetry configured in code but no Cloud Monitoring dashboards, no alerting rules. | Phases 110–111 |
| P1-5 | Desktop endpoints | Electron app uses localhost/mock fallbacks in production config path. | Phase 117 |
| P1-6 | AI model lifecycle | Models downloaded at runtime without pinned versions or checksums. Nondeterministic cold starts. | Phase 91 |
| P1-7 | Cloud Armor | No WAF/DDoS policy. Load balancer has no security policy attached. | Phase 109 |
| P1-8 | Worker reliability | ARQ jobs have no idempotency keys. Duplicate job execution possible on retry. | Phase 107 |
| P1-9 | GCP project separation | No staging vs production project separation documented or provisioned. | Phase 98 |
| P1-10 | Realtime image size | `torch`, `torchaudio`, `librosa`, `sounddevice` shipped in Cloud Run image. Server never captures audio; these add ~2 GB. | Phase 90 |

---

## P2 MEDIUM — Should fix for stable production

| ID | Area | Finding | Fix |
|----|------|---------|-----|
| P2-1 | Dependency audit | `pip-audit` not run in CI. Backend deps not audited for CVEs. | Phase 87 |
| P2-2 | pnpm audit | `pnpm audit` not run in CI. Frontend deps not scanned. | Phase 87 |
| P2-3 | Backup strategy | No RPO/RTO documented. No off-site export. Supabase free tier has no PITR. | Phase 97 |
| P2-4 | Release process | No documented development→PR→CI→staging→production→rollback process. | Phase 86 |
| P2-5 | Vercel environments | No preview/staging/production environment variable separation. | Phase 113 |
| P2-6 | Auth integration | Email verification, password reset, custom SMTP not verified for production. | Phase 114 |
| P2-7 | CORS | CORS origins not locked to production domains in backend settings. | Phase 102 |
| P2-8 | Redis direct VPC | Redis connection not through private VPC egress in GCP. | Phase 105 |
| P2-9 | Canary deployment | No canary traffic splitting strategy documented or implemented. | Phase 86 |
| P2-10 | DB migration safety | No pre-migration backup verification step, no staging gate. | Phase 94 |

---

## P3 LOW — Polish before GA

| ID | Area | Finding | Fix |
|----|------|---------|-----|
| P3-1 | Jaeger in compose | Dev `docker-compose.yml` uses `jaegertracing/all-in-one:latest` — not pinned. | Phase 89 |
| P3-2 | Runbook | No `PRODUCTION_RUNBOOK.md`. Ops procedures undocumented. | Phase 118 |
| P3-3 | Architecture doc | `docs/ARCHITECTURE.md` exists but predates phases 51–84 and GCP topology. | Phase 118 |
| P3-4 | Electron auto-update | No auto-update strategy configured for desktop builds. | Phase 117 |
| P3-5 | Log retention | No Cloud Logging retention policy. Default 30-day retention may be insufficient. | Phase 110 |
| P3-6 | Container image tag | `docker-compose.yml` worker build has no tag strategy. | Phase 89 |
| P3-7 | Test DB files | Leftover SQLite `.db` files committed to `realtime-agent/`. | Immediate cleanup |
| P3-8 | .env committed | `.env` file is committed to repo (contains real-looking values). Must verify it contains no real credentials. | Immediate audit |

---

## Current CI Status

- backend-tests: ⚠️ Intermittently failing (fixture column mismatches being fixed iteratively)
- frontend-checks: ✅ Passing
- secrets-scan: ✅ Passing

---

## Dependency Versions (as of audit)

| Package | Current | Action |
|---------|---------|--------|
| next | 15.0.0 | Upgrade to 15.3.x |
| react | ^19.0.0 | Keep (latest) |
| electron | ^33.0.0 | Keep (current) |
| fastapi | 0.110.0 | Upgrade to 0.115.x |
| uvicorn | 0.27.1 | Upgrade to 0.32.x |
| sqlalchemy | 2.0.27 | Upgrade to 2.0.36 |
| pydantic | 2.6.3 | Upgrade to 2.10.x |
| asyncpg | 0.29.0 | Keep (stable) |
| PyJWT | not pinned | Add explicit pin |
| cryptography | not pinned | Add explicit pin |
