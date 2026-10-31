# Threat Model

STRIDE-based threat model for the PRAXIS backend.
Scope: Cloud Run v2 services (praxis-api, praxis-realtime, praxis-worker),
Supabase PostgreSQL (pgvector), Memorystore Redis, GCS, Cloud Armor WAF.

Last reviewed: 2026-10-05

---

## Trust boundaries

```
Internet → Cloud Armor WAF → External ALB → Cloud Run (praxis-api)
                                           → Cloud Run (praxis-realtime)  [WebSocket]
                                           → Cloud Run (praxis-worker)    [internal only]

praxis-api ──────► Supabase PostgreSQL  [private VPC peering]
                ► Memorystore Redis     [private VPC]
                ► GCS                  [VPC-SC service perimeter]
                ► GCP Secret Manager   [Workload Identity]
                ► AI Gateway (external LLM providers)  [HTTPS, credential in Secret Manager]
```

---

## STRIDE analysis

### Spoofing

| Threat | Asset | Mitigation | Status |
|--------|-------|-----------|--------|
| JWT forgery | All API endpoints | RS256 JWKS verification via Supabase Auth; key rotation handled by Supabase | IMPLEMENTED |
| Internal service impersonation | Worker → API calls | Workers use Workload Identity; no API keys in env vars | IMPLEMENTED |
| GitHub Actions impersonation | Cloud Build + GCS state | WIF trust scoped to `repo:AMIYA8597/praxis-interviewOS:ref:refs/heads/main` | IMPLEMENTED |

### Tampering

| Threat | Asset | Mitigation | Status |
|--------|-------|-----------|--------|
| Data tampering across tenants | PostgreSQL rows | RLS + FORCE ROW LEVEL SECURITY on all tables; JWT claims propagated via `set_config` | IMPLEMENTED |
| Redis queue poisoning | ARQ job queue | Redis is VPC-internal; no public access | IMPLEMENTED |
| GCS object tampering | Uploaded resumes, exports | Signed URLs have per-operation permissions; bucket has no public IAM | IMPLEMENTED |
| Container image tampering | Cloud Run deployments | Immutable SHA digests; no `:latest` deploys; Artifact Registry is private | IMPLEMENTED |
| Terraform state tampering | GCS state bucket | Bucket locked to WIF principal; versioning enabled | IMPLEMENTED |

### Repudiation

| Threat | Asset | Mitigation | Status |
|--------|-------|-----------|--------|
| Unattributed AI calls | LLM provider usage | Every call logs `user_id` in `ai_call_log`; `RoutingContext.user_id` is required | IMPLEMENTED |
| Unattributed data deletion | `deletion_jobs` table | `deletion_jobs` retains audit record; `privacy_events` logs consent events | IMPLEMENTED |

### Information Disclosure

| Threat | Asset | Mitigation | Status |
|--------|-------|-----------|--------|
| Cross-tenant data leak | pgvector embeddings | RLS + `candidate_id` filter on all retrieval queries | IMPLEMENTED |
| Secret exposure via env vars | Provider API keys | All secrets from GCP Secret Manager at runtime; no secrets in container env | IMPLEMENTED |
| Stack traces in API errors | All endpoints | `register_exception_handlers` maps exceptions to safe error messages; debug=False | IMPLEMENTED |
| Prompt injection leaking system prompt | LLM endpoints | `PromptBuilder.add_untrusted()` isolates all user content; system prompt does not contain secrets | IMPLEMENTED |
| Export file accessible by wrong user | `/export` endpoint | `candidate_id` scoped export records; RLS on `candidate_data_exports` | IMPLEMENTED |

### Denial of Service

| Threat | Asset | Mitigation | Status |
|--------|-------|-----------|--------|
| API flooding | All endpoints | `RateLimitMiddleware` per-IP + per-user; Cloud Armor WAF layer-7 rules | IMPLEMENTED |
| File upload bomb | `POST /resumes` | `MAX_UPLOAD_BYTES` enforced before storage; 413 on oversize | IMPLEMENTED |
| Redis queue saturation | ARQ worker | Worker pool `max_jobs` setting; dead-letter queue prevents infinite retries | IMPLEMENTED |
| LLM token abuse | AI gateway | `zero_spend_mode` for worker jobs; per-user `RoutingContext` for throttling | IMPLEMENTED |

### Elevation of Privilege

| Threat | Asset | Mitigation | Status |
|--------|-------|-----------|--------|
| Container escape | Cloud Run VMs | Non-root `praxis` user (uid 1000) in Docker; read-only filesystem where possible | IMPLEMENTED |
| SSRF via JD URL | Job analysis | Raw JD text only — no URL-fetch functionality | N/A |
| DB privilege escalation | Supabase service_role | `service_role` used only by ARQ workers for admin ops; API uses anon/auth JWT | IMPLEMENTED |

---

## Security controls summary

| Control | Where | Notes |
|---------|-------|-------|
| JWT RS256 verification | `backend/app/core/auth.py` | JWKS cached; RS256 |
| RLS + FORCE RLS | All 30+ tables | Policies in `supabase/migrations/` |
| Secret Manager secrets | `packages/config/settings.py` | No env-var secrets in production |
| Cloud Armor WAF | `infra/gcp/main.tf` | Layer-7 rules; adaptive protection |
| `detect-secrets` scan | `.github/workflows/ci.yml` | Blocks commits with detected secrets |
| SBOM | CI pipeline | Generated on every push to main (see CI workflow) |
| Security headers | `SecurityHeadersMiddleware` | HSTS, CSP, X-Frame-Options, etc. |

---

## Out of scope

- Client-side (browser/mobile) security — handled by the UI team.
- Supabase Auth service internals — managed by Supabase.
- GCP IAM outside the described service accounts — managed by GCP org admin.
