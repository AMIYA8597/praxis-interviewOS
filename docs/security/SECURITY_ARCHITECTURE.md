# PRAXIS InterviewOS — Security Architecture Specification

**Milestone**: Phase 4 — Enterprise Security Engineering  
**Branch**: `phase4-security`  
**Date**: 2026-11-01  
**Classification**: ENTERPRISE SECURITY ARCHITECTURE  

---

## 1. Architectural Defense-in-Depth

PRAXIS InterviewOS implements a multi-layered defense-in-depth model across five tiers:

```
[ Tier 1: Perimeter & Edge ]
  - Cloud Armor / Ingress Controller TLS termination (TLS 1.3 preferred)
  - Strict CORS policy (explicit domain allowlist, no wildcard with credentials)
  - HTTP Security Headers (HSTS, CSP, X-Frame-Options: DENY, nosniff)
  - Rate limiting (Redis token-bucket algorithm per IP and user ID)

[ Tier 2: Authentication & Identity ]
  - RS256 JWT validation against Supabase JWKS with public key caching
  - Strict algorithm restriction to RS256 (mitigates algorithm confusion / None attacks)
  - Session revocation and automatic token refresh via Supabase Auth
  - No client-controlled identity assertions (principal identity extracted from sub)

[ Tier 3: Multi-Tenant Isolation & Authorization ]
  - Application layer: Role and ownership checks on every route handler
  - Service layer: Candidate memory and session access scoped to tenant principal
  - Database layer: PostgreSQL Row Level Security (RLS) on 100% of public tables
  - Vector retrieval layer: Hybrid RAG queries filter strictly by candidate_id

[ Tier 4: Speech, Media & Processing Isolation ]
  - Realtime WebSocket framing (>BBIdI 18-byte big-endian header validation)
  - Bounded audio ring buffers (<30s turn audio per active connection)
  - Document parser memory and timeout limits (magic byte validation, 10MB ceiling)
  - Coding execution sandbox (ephemeral container, no network, read-only root FS)

[ Tier 5: Operational Telemetry & Incident Response ]
  - Structured audit logging (actor, action, target, timestamp, IP)
  - PII and credential scrubbing in logs and Sentry traces
  - Tamper-evident operational metrics and alert thresholds
```

---

## 2. Cryptographic Controls & Key Management

1. **Authentication Tokens**:
   - Signature: RS256 (Asymmetric RSA 2048-bit with SHA-256).
   - Validation: Public keys discovered dynamically via `/.well-known/jwks.json` and cached in memory with a 1-hour TTL.
2. **Transit Encryption**:
   - All client-to-server and inter-service HTTP traffic enforces TLS 1.2+ (TLS 1.3 default).
   - WebSocket audio transport enforces `wss://` in production.
3. **Data at Rest**:
   - PostgreSQL table storage and disk volumes encrypted using AES-256 (GCP managed keys).
   - Sensitive credentials (e.g. AI provider API keys) encrypted at rest or injected as environment variables via GCP Secret Manager.
