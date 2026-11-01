# PRAXIS InterviewOS — Data Retention & Account Deletion Specification

**Milestone**: Phase 4 — Enterprise Security Engineering  
**Branch**: `phase4-security`  
**Date**: 2026-11-01  
**Classification**: GDPR & PRIVACY DELETION SPECIFICATION  

---

## 1. Account Deletion Lifecycle (GDPR Article 17)

PRAXIS provides an irreversible, multi-store account deletion workflow (`DELETE /api/v1/auth/account`):

```
Client Issues DELETE /api/v1/auth/account
                     |
                     v
+=======================================================================+
| 1. Synchronous Endpoint Gate (backend/app/api/auth.py)                |
| - Verifies authenticated caller identity (auth.uid())                 |
| - Creates DeletionJob record (status='queued')                        |
| - Dispatches asynchronous worker job via ARQ                          |
| - Returns HTTP 202 Accepted with deletion_job_id                      |
+=======================================================================+
                     |
                     v
+=======================================================================+
| 2. Asynchronous Deletion Worker (backend/app/core/deletion.py)        |
|                                                                       |
| A. Database Cascade:                                                  |
|    - Deletes document_chunks, resume_claims, resume_versions, resumes  |
|    - Deletes session_turns, session_debriefs, sessions                |
|    - Deletes study_reviews, study_items                               |
|    - Deletes applications, projects, candidates, profiles             |
|                                                                       |
| B. Object Storage Cleanup:                                            |
|    - Enumerates and purges all blobs prefixed with {candidate_id}/    |
|                                                                       |
| C. Redis Cache Purge:                                                 |
|    - Deletes cached sessions, rate limit tokens, and RAG cache keys   |
|                                                                       |
| D. Verification & Status Update:                                      |
|    - Records summary of deleted row counts                            |
|    - Updates deletion_jobs status to 'completed'                      |
+=======================================================================+
```

---

## 2. Retention Schedules

| Data Entity | Maximum Retention Period | Automatic Expiration Mechanism |
| :--- | :--- | :--- |
| Auth JWT Access Tokens | 3600 seconds (1 hour) | Expire via `exp` claim |
| Rate Limiting Counters | 60 seconds | Redis key TTL |
| JWKS Public Key Cache | 3600 seconds | Redis key TTL |
| Deleted Account Records | 0 seconds post-deletion | Immediate worker purge |
| Operational Audit Logs | 90 days | Partitioned table archival |
