# PRAXIS InterviewOS — Security Findings & OWASP API Top 10 Audit

**Audit Date:** 2026-11-04  
**Audit Standard:** OWASP API Security Top 10 (2023), CIS Benchmark principles, Least Privilege Database Access, Defense-in-Depth Isolation.  
**Automated Security Verification:** Verified by `tests/security/`, `backend/tests/security/`, `scripts/security/verify_security_configuration.py`, and `scripts/check_no_fake_data.py`.

---

## 1. OWASP API Security Top 10 Assessment Matrix

| OWASP Vulnerability | Risk Level | Defense Mechanism in PRAXIS | Verification Test / Evidence | Status |
|---|---|---|---|---|
| **API1:2023 Broken Object Level Authorization (BOLA)** | Critical | Strict user-level ownership checks (`verify_candidate_ownership`) on all entity routes (`/resumes/{id}`, `/jobs/{id}`, `/sessions/{id}`). Database enforces `FORCE RLS` on candidate tables. | `backend/tests/hardening/test_authorization.py` (cross-user access returns 404/403) | **MITIGATED & VERIFIED** |
| **API2:2023 Broken Authentication** | Critical | JWT signature, issuer, audience, and expiration verification. JWKS public keys cached in Redis with TTL. Forged JWTs cannot execute authenticated routes or set RLS claims. | `backend/tests/hardening/test_jwt_auth.py`, `backend/tests/security/test_rls_forged_jwt.py` | **MITIGATED & VERIFIED** |
| **API3:2023 Broken Object Property Level Authorization** | High | Pydantic v2 schemas reject unexpected/extra fields (`extra = "forbid"`). Sensitive internal fields (e.g. `is_admin`, `deleted_at`) cannot be mass-assigned. | `backend/tests/security/test_api_input_validation.py` | **MITIGATED & VERIFIED** |
| **API4:2023 Unrestricted Resource Consumption** | High | Redis sliding-window token bucket rate limiter (`RateLimitMiddleware`). File upload body limit (10 MB). Audio frames limited to 32ms chunks. LLM daily USD and token budgets. | `backend/app/rate_limiter.py`, `packages/ai-gateway/tests/test_budget.py` | **MITIGATED & VERIFIED** |
| **API5:2023 Broken Function Level Authorization** | High | Administrative routes (`/api/v1/admin/*`) require `require_admin` dependency which verifies membership in `admin_users` table. Normal candidates receive 403 Forbidden. | `backend/tests/security/test_admin_auth.py` | **MITIGATED & VERIFIED** |
| **API6:2023 Unrestricted Access to Sensitive Business Flows** | Medium | Sensitive actions (GDPR export, account deletion) are rate-limited to 1 request per 24 hours per candidate and logged to immutable audit ledger. | `backend/tests/api/test_exports.py`, `supabase/migrations/20261005000009_audit_logs.sql` | **MITIGATED & VERIFIED** |
| **API7:2023 Server-Side Request Forgery (SSRF)** | Critical | URL resolution checks destination IPs before establishing connections. Prohibits RFC 1918 private subnets, loopback (`127.0.0.1`), and cloud metadata (`169.254.169.254`). | `backend/tests/security/test_ssrf_defense.py` (5 tests passing) | **MITIGATED & VERIFIED** |
| **API8:2023 Security Misconfiguration** | Medium | Production security headers middleware enforces HSTS (`max-age=31536000`), CSP (`connect-src 'self' https: wss:; frame-ancestors 'none'`), `X-Content-Type-Options: nosniff`. | `scripts/security/verify_security_configuration.py` | **MITIGATED & VERIFIED** |
| **API9:2023 Improper Inventory Management** | Medium | Versioned `/api/v1` routes. OpenAPI schema verified automatically in CI against registered FastAPI routes. Deprecated endpoints removed. | `backend/tests/api/test_openapi_contract.py` | **MITIGATED & VERIFIED** |
| **API10:2023 Unsafe Consumption of APIs** | High | AI Gateway isolates all third-party LLMs. Output safety filters strip system prompt reflections and prompt injection attacks. Timeouts and circuit breakers bound external delays. | `packages/ai-gateway/praxis_ai_gateway/output_safety.py`, `backend/tests/security/test_prompt_injection.py` | **MITIGATED & VERIFIED** |

---

## 2. Secrets Management & Credential Hygiene

1. **Git Repository Hygiene:**
   - No plaintext API keys, JWT secrets, or cloud service account keys are committed to Git history or tracked files.
   - `.env` is ignored by `.gitignore` (`.gitignore:8`).
   - `.secrets.baseline` maintained using `detect-secrets`.
2. **Local Environment Findings:**
   - In local developer `.env`, `GOOGLE_API_KEY` was reported as revoked/leaked by the Google Generative Language API (HTTP 403 `PERMISSION_DENIED`).
   - Valid, active keys for OpenAI, Anthropic, and DeepSeek are present in developer configuration for paid tiers.
   - For zero-spend / free-tier mode, a fresh Groq API key or Gemini API key is required.
3. **Production Cloud Secret Architecture:**
   - In GCP staging and production, credentials are never read from disk or committed files.
   - Secrets are managed via Google Secret Manager (`infra/gcp/main.tf`):
     - `projects/${project_id}/secrets/database-url/versions/latest`
     - `projects/${project_id}/secrets/jwt-secret/versions/latest`
     - `projects/${project_id}/secrets/ai-provider-keys/versions/latest`
   - Cloud Run service accounts are granted `roles/secretmanager.secretAccessor` with least-privilege IAM bindings.

---

## 3. Sandboxed Untrusted Code Execution Security

- Candidate code execution is dispatched over HTTP/RPC to an isolated sandbox microservice container (`docker/Dockerfile.sandbox`).
- Security constraints verified by `backend/tests/services/test_coding_sandbox.py`:
  - **No Host Execution:** Never runs in API or Realtime agent processes.
  - **Environment Hygiene:** `os.environ` inside sandbox stripped of all application secrets (`DATABASE_URL`, `JWT_SECRET`, provider keys).
  - **Network Disabled:** Outbound network connections fail immediately (`socket.connect` raises `OSError` / `EPERM`).
  - **Execution Timeouts:** Infinite loops (`while True: pass`) terminated within 2 seconds.
  - **Fork Bomb & Process Limits:** Process spawning attempts are contained by Linux cgroups / ulimit.
  - **Memory Limits:** Memory bombs contained to 128 MB max heap allocation.
  - **Non-Root Execution:** Runs under unprivileged user (`nobody` / `appuser`). Base container filesystem mounted read-only.
