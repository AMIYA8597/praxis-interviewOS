# Security Model

Canonical security model for the PRAXIS backend.
See also: `docs/THREAT_MODEL.md` (STRIDE analysis), `docs/BACKEND_SECURITY_MODEL.md` (implementation detail).

---

## Authentication

All API requests require a valid Supabase-issued JWT (RS256) in the `Authorization: Bearer` header.

**Verification path:** `backend/app/core/auth.py`
1. Extract `Authorization` header.
2. Decode JWT header to get `kid`.
3. Fetch matching public key from Supabase JWKS endpoint (cached 1 hour).
4. Verify RS256 signature + `exp` + `iss`.
5. Extract `sub` (user UUID) → propagate as `user_id`.

**Development bypass:** `AUTH_DEV_BYPASS=true` maps any bearer token to `AUTH_DEV_USER_ID`.
This flag is explicitly blocked in any environment where `APP_ENV != "development"`.

---

## Authorization

Authorization is enforced at two layers:

### Layer 1 — Application (FastAPI)

`get_current_candidate` dependency resolves the `candidates.id` for the authenticated `user_id`.
Every protected endpoint calls this dependency; any request without a valid JWT or without a
`candidates` row returns 401/403.

### Layer 2 — Database (PostgreSQL RLS)

Every table has `ENABLE ROW LEVEL SECURITY` + `FORCE ROW LEVEL SECURITY`.
Before each query, the `request.jwt.claims` setting is populated:

```python
await conn.execute(text("SELECT set_config('request.jwt.claims', :claims, true)"), {"claims": claims})
```

RLS policies use `auth.uid()` to extract the user UUID from the claims and restrict access
to rows owned by that user.

**FORCE ROW LEVEL SECURITY** ensures the restriction applies even to the table owner role.

---

## Secrets management

| Secret | Storage | Access method |
|--------|---------|---------------|
| Database URL | GCP Secret Manager | Loaded at Cloud Run startup |
| Supabase service key | GCP Secret Manager | Loaded at Cloud Run startup |
| LLM provider API keys | GCP Secret Manager | Loaded at startup via `settings.py` |
| Redis URL | GCP Secret Manager | Loaded at startup |
| GCS credentials | Workload Identity | No explicit key; service account impersonation |

No secrets are injected as environment variables in production Cloud Run configs.
`detect-secrets` baseline scan in CI prevents accidental secret commits.

---

## Network security

- **Cloud Armor WAF** on the external Application Load Balancer: adaptive protection + custom
  rate-limit rules.
- **Cloud Run ingress:** `INGRESS_TRAFFIC_ALL` for praxis-api/realtime (behind ALB);
  `INGRESS_TRAFFIC_INTERNAL_ONLY` for praxis-worker.
- **VPC peering:** Supabase PostgreSQL and Memorystore Redis are reachable only via private
  IP in the `praxis-network` VPC.
- **HTTPS only:** All external endpoints enforce TLS via the ALB. `SecurityHeadersMiddleware`
  sets `Strict-Transport-Security` (HSTS) on all responses.

---

## Container security

- Base image: `python:3.11.11-slim` (minimal attack surface).
- Non-root user `praxis` (uid=1000) runs all processes.
- ML model cache (`/app/.cache`) is pre-populated at build time and owned by `praxis`.
- No secrets in `ENV` directives or image layers.
- Docker images are immutable: tagged with git SHA + registry digest; no `:latest` deploys.

---

## Security headers

`SecurityHeadersMiddleware` (`backend/app/middleware.py`) sets on every response:

| Header | Value |
|--------|-------|
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` |
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` | `DENY` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Content-Security-Policy` | API-appropriate (no inline scripts) |
| `Permissions-Policy` | `camera=(), microphone=(), geolocation=()` |

---

## Rate limiting

`RateLimitMiddleware` (`backend/app/rate_limiter.py`) enforces per-IP and per-user limits
backed by Memorystore Redis. Limits are configurable via `settings.RATE_LIMIT_*`.

Cloud Armor provides a second layer of DDoS and rate protection at the load balancer.

---

## Input validation

- All request bodies are validated by Pydantic v2 models before reaching service logic.
- User-supplied text fed to LLMs is wrapped in `PromptBuilder.add_untrusted()` to prevent
  prompt injection (see `docs/THREAT_MODEL.md` R-002).
- File uploads are limited to `MAX_UPLOAD_BYTES` and validated for MIME type before storage.

---

## Audit trail

| Event | Table | Retention |
|-------|-------|-----------|
| Consent events | `privacy_events` | Permanent |
| AI model calls | `ai_call_log` | 90 days |
| Deletion jobs | `deletion_jobs` | Permanent |
| Worker dead letters | `failed_jobs` | 30 days |
| Export requests | `candidate_data_exports` | Until `expires_at` + 7 days |
