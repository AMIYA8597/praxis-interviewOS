# PRAXIS InterviewOS — Queue & Worker Deployment Decision

**Document Version:** 1.0.0  
**Audit Date:** 2026-11-04  

---

## 1. Asynchronous Workload Assessment

PRAXIS InterviewOS executes several long-running and asynchronous tasks:
1. **Resume Processing & OCR:** Parsing PDF/DOCX, running Tesseract OCR, extracting structured claims.
2. **Dense Vector Embeddings & Indexing:** Generating 384-dimensional dense vectors using BGE-small-en-v1.5 and writing to PostgreSQL `vector(384)` columns.
3. **Session Debrief Generation:** Aggregating speech metrics, STAR answers, claim grounding results, and LLM rubric scores into relational tables.
4. **GDPR Account Deletion:** Cascading deletion of candidate entities across 10+ tables and purging GCS blobs.
5. **GDPR Data Archive Export:** Compiling candidate data into encrypted ZIP files.
6. **Study Card SM-2 Maintenance:** Scheduling spaced-repetition reviews.

---

## 2. Deployment Pattern Evaluation

| Model | Description | Pros | Cons | Decision |
|---|---|---|---|---|
| **Cloud Run Service (Always-On Consumer)** | Persistent container running `python -m arq backend.worker_settings.WorkerSettings` with HTTP health probe on 8080. | Low latency; instant job processing; handles bursts; simple connection pooling. | Incurs idle container compute (mitigated with 1 instance in staging). | **SELECTED FOR STAGING & PROD** |
| **Cloud Run Jobs (One-off Execution)** | Ephemeral tasks triggered per job. | Scale-to-zero when no jobs exist. | Cold-start latency (10-30s) unacceptable for real-time debrief generation. | **REJECTED FOR QUEUE; RESERVED FOR DB MIGRATIONS** |

---

## 3. Worker Invariants & Failure Resilience

1. **Idempotency:** All ARQ jobs use idempotency keys recorded in `worker_idempotency` table to prevent duplicate execution during network retries.
2. **Crash Recovery:** Unfinished jobs are requeued with exponential backoff; dead-letter jobs are moved to `failed_jobs` table for inspection.
3. **Graceful Drain:** Upon receiving `SIGTERM`, workers complete the active job before cleanly closing database and Redis connection pools.
