# PRAXIS InterviewOS — Data, Storage & Redis Security Specification

**Milestone**: Phase 4 — Enterprise Security Engineering  
**Branch**: `phase4-security`  
**Date**: 2026-11-01  
**Classification**: DATA STORAGE SECURITY AUDIT & SPECIFICATION  

---

## 1. PostgreSQL & pgvector Security

### 1.1 Row Level Security (RLS) Engine
- 100% of the 71 public relational tables enforce `ALTER TABLE <name> ENABLE ROW LEVEL SECURITY` and `ALTER TABLE <name> FORCE ROW LEVEL SECURITY`.
- The application sets tenant context on checked-out connection sessions (`SET LOCAL "request.jwt.claim.sub" = :user_id`), ensuring queries without explicit `WHERE` clauses cannot read or modify adjacent tenant records.
- Service role connections are strictly reserved for asynchronous maintenance jobs (e.g., GDPR deletion worker).

### 1.2 Transit & Volume Encryption
- Database connections enforce SSL/TLS (`sslmode=require` or `sslmode=verify-full`).
- PostgreSQL storage volumes use AES-256 transparent disk encryption.

---

## 2. Redis Cache & Worker Queue Security

1. **Network Boundary**: Redis runs on an isolated private VPC network (`10.0.0.0/16`) with zero public IP assignment or internet ingress.
2. **Access Control**: Authenticated via strong `REDIS_PASSWORD` with ACL support.
3. **Key Namespace Isolation**:
   - Rate limiting: `rate_limit:{ip|user_id}:{window}`
   - JWKS Cache: `cache:jwks` (TTL 3600s)
   - Realtime Session State: `realtime:session:{id}` (TTL 7200s)
   - ARQ Background Queue: `arq:queue`
4. **Data Minimization**: No raw candidate audio samples or unencrypted API keys are ever persisted in Redis.

---

## 3. Object Storage Security (GCS / S3 / Supabase Storage)

1. **Private Buckets**: `resumes` and `audio_recordings` buckets are private-by-default with public access prevention enabled.
2. **Short-Lived Signed URLs**: Pre-signed URLs for resume download or audio playback have an expiration ceiling of 15 minutes.
3. **Tenant Prefixing**: Every object path strictly prefixes the candidate UUID: `{candidate_id}/resumes/{document_id}/{filename}`.
