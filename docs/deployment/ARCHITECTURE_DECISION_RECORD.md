# PRAXIS InterviewOS — Architecture Decision Record (ADR-001)

**Title:** Authoritative Cloud Architecture, Database Authority & Service Topology  
**Date:** 2026-11-04  
**Status:** Approved & Certified  
**Deciders:** Lead Systems Architect, Security Officer, Antigravity Autonomous Agent  

---

## 1. Context & Problem Statement

PRAXIS InterviewOS is transitioning from release candidate verification to Google Cloud staging deployment. The deployment requires:
- Exactly one authoritative relational database per environment (no split-brain or duplicate business databases).
- An asynchronous queue and cache layer with durable failure recovery.
- Private object storage with expiring signed URLs for candidate documents.
- A clean, scalable microservice topology separating REST API, Realtime WebSockets, background workers, and isolated code execution.
- Strict cost safety, zero spend without authorization, and no vendor lock-in on the frontend.

---

## 2. Decision Summary

| Area | Decision | Primary Rationale |
|---|---|---|
| **Authoritative Database** | **Managed PostgreSQL (Supabase / Cloud SQL Standby)** | Existing PostgreSQL instance (`rqbbfegkqmsvthdgoyqk`) holds all 31 migrations, 70 RLS policies, and pgvector extension. Single source of truth. Zero split-brain. |
| **Transient Cache & Queue** | **Memorystore Redis 7 / Managed Redis** | Strictly ephemeral coordination (ARQ task queue, rate limiting, distributed locks, session state acceleration). Durable business truth stays in PostgreSQL. |
| **Object Storage** | **Google Cloud Storage (Private Buckets)** | Private bucket storage with 15-minute expiring signed URLs and object ownership validation. No raw binaries in database. |
| **Compute Topology** | **Cloud Run (API, Realtime, Worker, Sandbox)** | Serverless container execution with independent autoscaling, scale-to-zero in staging, and explicit max instances for hard cost caps. |
| **Code Sandbox** | **Hardened Non-Root Container without Egress** | Candidate-submitted code executes in an isolated environment (`praxis-sandbox`) with zero credentials and no network egress. |

---

## 3. Invariants & Guardrails

1. **Single Persistence Authority:** Cloud SQL and Supabase shall NEVER be run simultaneously as dual authoritative business databases. If Cloud SQL migration is authorized, Supabase becomes read-only and is decommissioned.
2. **Ephemeral Redis Guarantee:** If Redis is completely flushed or restarted, no committed candidate interviews, scores, resumes, or study cards shall be lost.
3. **Immutable Releases:** Release containers must be tagged with `${SHORT_SHA}` and deployed by immutable digest (`sha256:...`). The mutable `:latest` tag is prohibited.
4. **Least Privilege IAM:** Each Cloud Run service runs under its own dedicated Service Account with granular Secret Manager and storage permissions.
