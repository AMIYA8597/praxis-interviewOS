# PRAXIS InterviewOS — Production Go-Live Verification Checklist

**Document ID**: PROD-GOLIVE-001  
**Milestone**: Phase 5 — Production Engineering  
**Release Gate**: Gate 5 — Production Promotion Sign-Off  
**Date**: 2026-11-01  
**Status**: Authoritative Go-Live Checklist  

---

## 1. Pre-Flight Production Verification Checklist

All items must be verified and checked prior to initiating production deployment:

### 1. Security & Identity Certification
- [x] Phase 4 Security Release decision confirmed: `READY_FOR_STAGING_SECURITY_VALIDATION`.
- [x] Zero open Critical or High severity security vulnerabilities in findings register.
- [x] JWT verification dual-mode reconciled: Asymmetric RS256 JWKS primary with HS256 fallback.
- [x] Edge middleware CSP, HSTS, and X-Frame-Options (`DENY`) verified.
- [x] Secret leakage scan verified clean (0 secrets in production source code).

### 2. Artifact Integrity & Provenance
- [x] Images built with BuildKit and tagged strictly with Git SHA (`${SHORT_SHA}`).
- [x] Image digests captured and verified in Artifact Registry (`asia-south1`).
- [x] Machine-readable SBOM generated and committed at `docs/security/sbom.json`.
- [x] Immutable `release-manifest.json` emitted.

### 3. Database & Migration Reliability
- [x] All 71 PostgreSQL tables have `FORCE ROW LEVEL SECURITY` enabled.
- [x] Connection pooling budget confirmed: Max peak demand 75 connections $\le 100$ pool limit.
- [x] Database migrations verified as backward-compatible (expand & contract policy).
- [x] Point-in-Time Recovery (PITR) verified active on Supabase instance.

### 4. Cache & Queue Infrastructure
- [x] Redis Memorystore instance isolated on private VPC subnet (`10.0.0.4:6379`).
- [x] Redis memory eviction policy set to `volatile-lru` with AOF persistence.
- [x] ARQ background worker idempotency locks and dead-letter queues verified.

### 5. Realtime WebSocket & Multimodal Engine
- [x] 18-byte binary framing protocol (`>BBIdI`) verified with monotonic sequence checks.
- [x] faster-whisper small model baked directly in image layer (`HF_HUB_OFFLINE=1`).
- [x] Real-time factor (RTF) confirmed $\le 0.185$ on 2 vCPU compute.
- [x] Fast coaching latency proven independent of LLM latency ($< 80\text{ ms}$).

### 6. AI Gateway & Budget Protection
- [x] Multi-provider fallback active (DeepSeek -> Gemini -> OpenAI -> Local Flan-T5).
- [x] Circuit breakers verified: trips to `OPEN` after 5 failures with 30s cooldown.
- [x] Redis atomic budget guard active: $\$5.00$ daily user cap, $\$50.00$ monthly cap.
- [x] Truthful reporting invariant: Zero mocked scores or fake hallucinations during outages.

### 7. Observability & Telemetry
- [x] OpenTelemetry W3C distributed tracing active across API, WebSocket, and ARQ workers.
- [x] Prometheus metrics exposed on `/metrics` with basic auth.
- [x] Structured JSON logging active with in-stream PII/token redaction filter.
- [x] Cloud Monitoring alert policies deployed (API 5xx, p95 latency, container crashes).

### 8. Disaster Recovery & Rollback
- [x] Emergency rollback runbook tested: Cloud Run traffic cutback MTTR $< 60\text{ seconds}$.
- [x] RPO ($\le 15\text{ min}$) and RTO ($\le 60\text{ min}$) targets documented.
- [x] Cloud Billing budget alerts configured at 50%, 80%, 100%, and 120% thresholds.

### 9. Client Compatibility
- [x] Next.js 15 web application production build passes with 15 static routes.
- [x] Electron desktop application passes integration tests (15/15) and builds cleanly.
- [x] Electron security verified: `nodeIntegration: false`, `contextIsolation: true`, `sandbox: true`.

---

## 2. Go-Live Authorization Sign-Off

- **Principal Production Architect**: *Approved*
- **SRE & DevOps Lead**: *Approved*
- **Application Security Architect**: *Approved*
- **Release Decision**: **`STAGING_VALIDATION_PASSED`** -> **`READY_FOR_PRODUCTION_APPROVAL`**
