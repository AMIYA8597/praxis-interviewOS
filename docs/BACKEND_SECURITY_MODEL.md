# PRAXIS Backend Security Model

This document describes the security controls implemented in the PRAXIS backend.
All claims reference concrete code in the repository — no aspirational or future items are included.

---

## 1. Authentication Flow

Authentication is stateless JWT verification. Supabase issues RS256 JWTs; the backend
verifies them on every request against the Supabase JWKS endpoint.

### Flow

```
Client → Bearer <JWT> in Authorization header
  → RateLimitMiddleware (Redis counter per user:IP)
  → CORSMiddleware
  → RequestIdMiddleware (assign/validate X-Request-ID)
  → SecurityHeadersMiddleware
  → FastAPI route handler
    → get_current_user dependency
      → Extract token from Authorization: Bearer <token>
      → Fetch JWKS from Supabase (cached in Redis)
      → Verify RS256 signature, exp, iat, sub, aud, iss
      → Return verified claims dict
    → get_current_candidate dependency
      → Resolve candidate row from claims["sub"]
      → Cache candidate in Redis (short TTL)
```

Key properties:
- Algorithm: RS256 only. No HS256 accepted.
- JWKS kid rotation: supported — the JWKS endpoint is fetched per-kid and cached.
- Required claims: `exp`, `iat`, `sub`, `aud`, `iss` — all validated.
- Dev bypass: when `AUTH_DEV_BYPASS=true` (never set in staging/production), every token
  maps to `AUTH_DEV_USER_ID`. This is logged at WARNING on startup.

### Session context for RLS

After JWT verification, `request.jwt.claims` is injected into the PostgreSQL session
via `SET LOCAL request.jwt.claims = '{"sub": "<uuid>"}'` before any query executes.
Supabase RLS policies read `auth.uid()` which resolves from this session variable.
Worker tasks replicate this via the `user_db_conn()` async context manager in
`backend/app/worker_tasks.py`.

---

## 2. Authorization

### Server-side ownership checks

No client-supplied IDs are trusted for ownership. All service functions resolve ownership
server-side:

```python
# Pattern in services — fetch row and verify ownership before returning
WHERE id = :id AND candidate_id = :candidate_id
```

The `get_current_candidate` dependency resolves the candidate from the verified JWT `sub`
and passes it down. Routes never accept a `candidate_id` from the request body for
ownership-sensitive operations.

### Admin role

Admin status is stored in the `admin_users` table. The `require_admin` dependency
(`backend/app/dependencies.py`) queries this table. All admin routes are gated by this
dependency. The database `is_admin()` SQL function (`security definer`) is used in RLS
policies for admin-only tables.

---

## 3. Row Level Security (RLS)

### FORCE RLS

Migration `20261004000002_force_rls.sql` applies `ALTER TABLE <t> FORCE ROW LEVEL SECURITY`
to every table in the `public` schema. This means even the table owner (application service
role) cannot bypass RLS without explicitly using `SET ROLE` — preventing accidental
privilege escalation from a misconfigured connection.

### Policy pattern

All tenant tables follow the ownership-chain pattern. Direct ownership:

```sql
-- profile-direct tables
create policy "candidates_select_own" on candidates
  for select using (profile_id = auth.uid());

-- candidate-scoped tables
create policy "documents_select_own" on documents
  for select using (
    candidate_id in (select id from candidates where profile_id = auth.uid())
  );
```

Deep-chain tables (second/third hop):

```sql
-- document_chunks → documents → candidates
create policy "document_chunks_select_own" on document_chunks
  for select using (
    document_id in (
      select id from documents where candidate_id in (
        select id from candidates where profile_id = auth.uid()
      )
    )
  );
```

### Special-case tables

| Table | Policy |
|---|---|
| `skills` | SELECT: public; INSERT/UPDATE/DELETE: `is_admin()` |
| `audit_logs` | SELECT: `is_admin()` only; no INSERT policy (server-side writes only) |
| `privacy_events` | SELECT: `is_admin()` only |
| `provider_health` | SELECT: public; mutations: `is_admin()` |
| `feature_flags` | SELECT: public; mutations: `is_admin()` |
| `admin_users` | SELECT: own row or admin; mutations: admin only |

Cross-tenant isolation is enforced by FORCE RLS. There are no policies granting cross-user
access on any tenant data table.

---

## 4. CSRF Stance

This API is Bearer-token-only. No cookie-based authentication is implemented.
CSRF attacks require the attacker to forge cookie credentials, which is impossible here.
The CORS configuration in `backend/app/main.py` restricts allowed origins and exposes
only `X-Request-ID` and `Retry-After` headers.

---

## 5. Prompt Injection Defence

### Input containment: PromptBuilder.add_untrusted()

All untrusted content (resume text, job descriptions, user input) is wrapped via
`PromptBuilder.add_untrusted(label, source, content)` before being sent to any LLM.
This wraps the content in XML-style delimiters:

```
<UNTRUSTED_DOCUMENT source="resume_upload" label="resume_text">
...content...
</UNTRUSTED_DOCUMENT>
```

The system prompt establishes that content inside these tags must be treated as data,
never as instructions.

### Output validation: output_safety.py

`packages/ai-gateway/praxis_ai_gateway/output_safety.py` validates every non-streaming
LLM response before it reaches the application layer. Checks run in the `GatewayRouter`
after a successful provider call.

Four check categories:
1. **Echo-injection detection** — output must not contain prompt delimiter markers such as
   `<UNTRUSTED_DOCUMENT`, `<TRUSTED_CONTEXT`, or `CRITICAL SECURITY INSTRUCTION:`. Any
   match raises `ECHO_INJECTION_MARKER` (error severity).
2. **Injection attempt phrases** — patterns like "ignore all previous instructions",
   "reveal your system prompt", "you are now DAN" are flagged as `INJECTION_ATTEMPT_IN_OUTPUT`.
3. **Score range checks** — numeric fields matching `score$`, `confidence$`, `wpm$`, etc.
   must fall within declared bounds (e.g. confidence in [0,1], score in [0,10]).
4. **Required field completeness** — structured outputs must contain all declared required
   fields; missing fields raise `MISSING_REQUIRED_FIELD`.

Safety violations are logged at WARNING level with violation codes. Violations do not abort
the response by default (to prevent a single adversarial resume from killing a session),
but `assert_safe()` can be called to raise `ValueError` when hard-failing is appropriate.

---

## 6. Upload Security

`backend/app/core/security.py` implements two checks:

**Magic byte validation** (`validate_file_magic_bytes`):
- PDF: header must start with `%PDF-` (bytes `25 50 44 46 2D`)
- DOCX: header must start with `PK\x03\x04` (ZIP signature)
- Any other header raises HTTP 400 — file extension is never trusted alone.

**MIME type check**: the reported MIME type is cross-checked against the magic bytes result.

**Size check**: files exceeding `settings.MAX_UPLOAD_BYTES` are rejected before storage
(enforced in `service.upload_resume` before the storage write).

---

## 7. SSRF Guard

`backend/app/core/security.py` exposes `is_safe_url(url: str) -> bool`:

- Resolves hostname to IP via `socket.gethostbyname`
- Blocks private IP ranges (`ip.is_private`)
- Blocks loopback (`ip.is_loopback`)
- Blocks the GCP/AWS/Azure metadata endpoint `169.254.169.254` explicitly
- Returns `False` on any resolution error

Any outbound HTTP call to user-supplied URLs must pass `is_safe_url` before proceeding.

---

## 8. Security Headers Middleware

`backend/app/middleware.SecurityHeadersMiddleware` sets the following headers on every
response (including error responses, because it is the outermost middleware):

| Header | Value | Notes |
|---|---|---|
| `X-Content-Type-Options` | `nosniff` | Always |
| `X-Frame-Options` | `DENY` | Always |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Always |
| `Permissions-Policy` | `camera=(), microphone=(), geolocation=()` | Always |
| `X-XSS-Protection` | `0` | Modern recommendation: disable legacy filter |
| `Strict-Transport-Security` | `max-age=63072000; includeSubDomains` | staging + production only |

HSTS is intentionally omitted in `development` to avoid locking out local HTTP debugging.
No Content-Security-Policy is set here — this is a JSON API; the frontend owns its own CSP.

---

## 9. Rate Limiting

`backend/app/rate_limiter.RateLimitMiddleware` applies Redis-backed per-minute counters.

**Identifier**: `<user_sub>:<client_ip>` when a valid Bearer token is present; `<client_ip>`
otherwise. The JWT is decoded *without* signature verification for identifier extraction
only — cryptographic verification still happens in `get_current_user`. A forged `sub` in an
unverified token shares the bucket with the source IP so it cannot drain another user's limit.

**Per-route limits**:

| Route prefix | Tokens/minute | Notes |
|---|---|---|
| `/api/v1/auth/signup` | 5 | Anti-abuse |
| `/api/v1/resumes` | 10 | Upload throttle |
| `/api/v1/jobs/analyze` | 10 | AI call throttle |
| `/api/v1/health` | 120 | Probe-friendly |
| (default) | 60 | All other routes |

Redis failures cause the middleware to **fail open** (pass the request through). The
`Retry-After: 60` header is returned on 429 responses.

---

## 10. Audit Logs

The `audit_logs` table captures security-relevant actions. Schema:

```sql
create table audit_logs (
  id uuid primary key,
  profile_id uuid references profiles(id) on delete set null,
  action text not null,   -- e.g. "user_banned", "account_deletion_queued"
  resource text,          -- e.g. "profiles/<uuid>"
  details jsonb,
  created_at timestamptz not null default now()
);
```

RLS policy: `SELECT` granted to `is_admin()` only. No `INSERT` RLS policy — only
server-side code writes to this table. There is no `updated_at` trigger; the table is
append-only by design.

Currently audited events: `user_banned` (via `POST /admin/users/ban`).

---

## 11. AI Output Safety (summary)

See Section 5. The `output_safety.py` module exports:
- `validate_text_output(text) -> SafetyReport`
- `validate_structured_output(data, required_fields) -> SafetyReport`
- `assert_safe(report)` — raises `ValueError` on error violations

All validators are synchronous and designed to complete in under 1 ms. They are called
in `GatewayRouter.route()` after every non-streaming structured or text generation call.
Prometheus counter `praxis_ai_output_safety_violations_total{code=...}` is incremented
per violation code when the Prometheus integration is wired in.
