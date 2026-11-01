# PRAXIS InterviewOS — Authoritative Environment & Configuration Inventory

**Document ID**: PROD-CONFIG-001  
**Milestone**: Phase 5 — Production Engineering  
**Primary Module**: `packages/config/settings.py` (Pydantic Settings v2)  
**Security Standard**: Strict Startup Validation, Zero Secrets in Client Bundles  
**Date**: 2026-11-01  
**Status**: Authoritative Configuration Matrix  

---

## 1. Classification & Scope Taxonomy

PRAXIS categorizes every configuration parameter into three operational zones:
1. **Public Client Variables**: Embedded in web or desktop frontend bundles (safe for client inspection).
2. **Server Environment Variables**: Injected at container runtime into Cloud Run or background workers.
3. **Secret Manager Secrets**: High-value credentials mounted securely from Google Cloud Secret Manager.

---

## 2. Comprehensive Configuration Matrix

| Variable Name | Scope | Storage Location | Default / Example | Purpose & Invariant |
| :--- | :--- | :--- | :--- | :--- |
| `APP_ENV` | Server | Runtime Env | `production` | Set to `development`, `staging`, or `production`. Disables dev bypasses. |
| `PORT` | Server | Runtime Env | `8000` (API) / `8080` | Port listened to by container instances. |
| `DATABASE_URL` | Server | Secret Manager | `postgresql+asyncpg://...` | Primary Supabase connection string (`sslmode=require`). |
| `DB_POOL_SIZE` | Server | Runtime Env | `2` | SQLAlchemy baseline pool size per container instance. |
| `DB_MAX_OVERFLOW` | Server | Runtime Env | `3` | SQLAlchemy burst connection allocation per instance. |
| `REDIS_URL` | Server | Secret Manager | `redis://10.0.0.4:6379/0` | Private VPC Memorystore Redis endpoint with AUTH. |
| `SUPABASE_URL` | Server / Web | Runtime / Secret | `https://xxxx.supabase.co` | Project URL used for JWKS discovery (`.well-known/jwks.json`). |
| `SUPABASE_ANON_KEY` | Public | Client Bundle | `eyJhbGci...` | Public client key for frontend auth sessions. |
| `SUPABASE_SERVICE_ROLE_KEY` | Server | Secret Manager | `eyJhbGci...` | Admin key for background workers. **NEVER** exposed to frontend. |
| `SUPABASE_JWT_SECRET` | Server | Secret Manager | `[32+ byte string]` | Shared secret for legacy symmetric HS256 tokens. |
| `JWT_AUDIENCE` | Server | Runtime Env | `authenticated` | Required audience claim in JWT. |
| `CORS_ALLOW_ORIGINS`| Server | Runtime Env | `https://praxis.domain.com` | Strict origin allowlist. `*` is strictly rejected in production. |
| `ENABLE_RATE_LIMIT`| Server | Runtime Env | `true` | Activates Redis sliding-window rate limiting. |
| `OPENAI_API_KEY` | Server | Secret Manager | `sk-or-v1-...` | OpenRouter / OpenAI API key for LLM inference. |
| `DEEPSEEK_API_KEY` | Server | Secret Manager | `sk-or-v1-...` | DeepSeek model routing key. |
| `GOOGLE_API_KEY` | Server | Secret Manager | `AIzaSy...` | Google Gemini 1.5 Pro inference key. |
| `NEXT_PUBLIC_API_URL`| Public | Web Bundle | `https://api.praxis.domain.com` | Base URL used by browser to reach FastAPI. |
| `NEXT_PUBLIC_WS_URL` | Public | Web Bundle | `wss://realtime.praxis.domain.com`| Base URL used by browser to reach WebSocket agent. |

---

## 3. Startup Configuration Validation Rules

At container boot, [`packages/config/settings.py`](file:///d:/work/interviewOS/packages/config/settings.py) executes automated invariant checks. If an invalid or dangerous configuration is detected, the process terminates immediately (`exit 1`) to fail closed:

1. **Production Dev Bypass Prohibition**:  
   If `APP_ENV == "production"` and `AUTH_DEV_BYPASS == true`, boot fails immediately:  
   `ValueError: AUTH_DEV_BYPASS is strictly prohibited in production`.
2. **Wildcard CORS Prohibition**:  
   If `APP_ENV == "production"` and `CORS_ALLOW_ORIGINS` contains `*`, boot fails immediately:  
   `ValueError: Wildcard CORS origin is forbidden in production`.
3. **Database URL Validation**:  
   If `DATABASE_URL` uses SQLite in production, boot fails:  
   `ValueError: SQLite is not permitted outside development environments`.
4. **Secret Zero-Leakage Invariant**:  
   Validation error messages log only the missing variable name; secret values are **never** echoed to stdout or stderr.
