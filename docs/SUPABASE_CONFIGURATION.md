# PRAXIS Supabase Configuration Guide

## 1. Project Topology & Environment Isolation

PRAXIS requires strict environment separation across distinct Supabase projects:

| Environment | Purpose | Supabase Project Ref | Database Target |
|---|---|---|---|
| **Local Development** | Developer workstation | Mock / Local container | `postgresql://localhost:5432/praxis` |
| **Staging** | CI / E2E automated testing | Dedicated Staging Project | Supabase Staging Pooler URL |
| **Production** | Live production traffic | Dedicated Production Project | Supabase Production Pooler URL |

> [!CRITICAL]
> Staging and Production **MUST** be separate Supabase projects. Never execute automated integration or staging tests against the production project.

### 1.1 Configured Supabase Project (InterviewOS)
- **Project Ref**: `rqbbfegkqmsvthdgoyqk`
- **Region**: Central EU (Frankfurt, `eu-central-1`)
- **Project URL**: `https://rqbbfegkqmsvthdgoyqk.supabase.co`
- **JWKS Endpoint**: `https://rqbbfegkqmsvthdgoyqk.supabase.co/auth/v1/.well-known/jwks.json`
- **Transaction Pooler (IPv4)**: `aws-1-eu-central-1.pooler.supabase.com:6543/postgres?pgbouncer=true`
- **Session Pooler (IPv4)**: `aws-1-eu-central-1.pooler.supabase.com:5432/postgres`
- **Direct Database Host (IPv6)**: `db.rqbbfegkqmsvthdgoyqk.supabase.co:5432/postgres`
- **Storage Bucket**: `documents` (Private, 10MB limit)

---

## 2. Authentication Architecture

### 2.1 Asymmetric Token Verification (RS256 / JWKS)
- **Primary Mechanism**: Access tokens issued by Supabase Auth are cryptographically verified using public keys retrieved from:
  ```
  ${SUPABASE_URL}/auth/v1/.well-known/jwks.json
  ```
- **Caching & Rotation**:
  - The key set is cached in Redis (`cache:jwks`) for `JWKS_CACHE_TTL_S` (3600 seconds).
  - When an incoming token has an unknown `kid` (indicating key rotation), the cache is bypassed and the JWKS is refreshed.
  - Forced refreshes are rate-limited by `JWKS_REFRESH_COOLDOWN_S` (60 seconds) to prevent Denial-of-Service attacks from invalid tokens.

### 2.2 Symmetric Token Verification (HS256 Fallback)
- For legacy Supabase projects utilizing symmetric keys, `SUPABASE_JWT_SECRET` is supported as a fallback.
- In production, if neither `SUPABASE_URL` nor `SUPABASE_JWT_SECRET` is configured, `Settings.validate_production` halts application boot immediately.

### 2.3 Verified Claims & RLS Context
- Only cryptographically verified claims reach the database layer.
- `backend/app/dependencies.py` extracts verified `claims` and invokes:
  ```sql
  SELECT set_config('request.jwt.claims', :claims_json, true);
  ```
- The transaction-local scope (`true`) prevents claim leakage across pooled connections.

---

## 3. Database & Connection Pooling

### 3.1 Extensions
- `vector`: Required for dense vector storage (`vector(384)`) and HNSW cosine distance indexing (`vector_cosine_ops`).

### 3.2 Connection Pooler Configuration
Supabase provides PgBouncer connection pooling. Cloud Run services connect through the pooler:
- **Pooler Port**: `6543` (transaction mode) or `5432` (transaction mode).
- **Client Setting**: `asyncpg` default prepared statement cache must be disabled (`statement_cache_size = 0`, `prepared_statement_cache_size = 0`) to prevent statement collisions between different physical backend connections.
- **Connection Sizing**:
  - Per instance: `DB_POOL_SIZE = 2`, `DB_MAX_OVERFLOW = 3` (maximum 5 connections per container).

### 3.3 Runtime Role: `praxis_app`
- Migration `20261004000001_praxis_app_role.sql` provisions the `praxis_app` role.
- Defined as `NOBYPASSRLS`, ensuring that no query executed by the application backend can circumvent tenant isolation policies.
- Application code never connects as `postgres` or `service_role`.

---

## 4. Supabase Storage Configuration

### 4.1 Storage Buckets
- **Bucket**: `documents`
- **Visibility**: **Private** (public read access disabled).
- **Allowed MIME Types**: `application/pdf`, `application/vnd.openxmlformats-officedocument.wordprocessingml.document`, `text/plain`.
- **Max File Size**: 10,485,760 bytes (10 MB).

### 4.2 Storage Access Policies
- Candidates can only upload to their own scoped prefix:
  `documents/{candidate_id}/{document_id}.pdf`
- Document downloads generate short-lived signed URLs (15-minute expiry) or stream through the authenticated API download endpoint.
