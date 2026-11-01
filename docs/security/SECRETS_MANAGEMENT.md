# PRAXIS InterviewOS — Secrets Management & Credential Governance

**Milestone**: Phase 4 — Enterprise Security Engineering  
**Branch**: `phase4-security`  
**Date**: 2026-11-01  
**Classification**: SECRETS GOVERNANCE REPORT  

---

## 1. Secrets Management Invariants

1. **Zero Hardcoded Secrets in Git**: No production passwords, API keys, service role keys, or private certificates are committed to the repository.
2. **Environment Separation**: Local development utilizes `.env.local` (git-ignored); staging and production environments inject secrets via Google Cloud Secret Manager.
3. **No Service Keys in Frontend**: Public variables in `apps/web` are restricted strictly to `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY`. Supabase `SERVICE_ROLE_KEY` is never exposed to client bundles.

---

## 2. Production Secret Inventory & Access Matrix

| Secret Identifier | Secret Manager Name | Consumer Service | Access Policy |
| :--- | :--- | :--- | :--- |
| `DATABASE_URL` | `praxis-database-url` | Backend API, Workers | `roles/secretmanager.secretAccessor` |
| `REDIS_PASSWORD` | `praxis-redis-password` | Backend API, Realtime Agent, Workers | `roles/secretmanager.secretAccessor` |
| `SUPABASE_JWT_SECRET` | `praxis-supabase-jwt-secret` | Backend API, Realtime Agent | `roles/secretmanager.secretAccessor` |
| `OPENAI_API_KEY` | `praxis-openai-api-key` | AI Gateway, Workers | `roles/secretmanager.secretAccessor` |
| `GOOGLE_API_KEY` | `praxis-google-api-key` | AI Gateway, Workers | `roles/secretmanager.secretAccessor` |
| `DEEPSEEK_API_KEY` | `praxis-deepseek-api-key` | AI Gateway | `roles/secretmanager.secretAccessor` |

---

## 3. Secret Leakage Prevention & Scanning

- **Automated Gitleaks / Secret Scan**: Continuous scanning for API key signatures in CI pipelines.
- **Log Sanitization Middleware**: Outbound logs filter authorization headers, access tokens, and API key prefixes (`sk-`, `AIzaSy`).
