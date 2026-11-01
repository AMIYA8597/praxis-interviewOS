# PRAXIS InterviewOS — Phase 3 Client API Integration Specification

**Milestone**: Phase 3 — Web & Desktop Client Engineering  
**Branch**: `phase3-web-desktop`  
**Date**: 2026-11-01  
**Classification**: INTEGRATION & API CONTRACT SPECIFICATION  

---

## 1. API Client Architecture

All client HTTP communication flows through a unified, typed API client (`apps/web/src/lib/api/client.ts`).

### Invariants:
1. **JWT Header Injection**: `Authorization: Bearer <TOKEN>` automatically appended using the active Supabase session.
2. **Standard Error Normalization**: HTTP error responses (4xx, 5xx) are parsed and converted to typed `ApiError` instances containing HTTP status and descriptive server error messages.
3. **Pydantic Type Symmetry**: All TypeScript types in `apps/web/src/lib/api/types.ts` and `packages/types/src/index.ts` strictly match backend Pydantic models.

---

## 2. Endpoint Catalog & Client Methods

### 2.1 Candidate Profile
- `GET /api/v1/candidates/me` → `getCurrentCandidate()`
- `PATCH /api/v1/candidates/me` → `updateCandidate(payload)`

### 2.2 Resume & Documents
- `POST /api/v1/candidates/resume` → `uploadResume(formData)`
- `GET /api/v1/candidates/resume` → `getResumeStatus()`

### 2.3 Job Descriptions
- `GET /api/v1/jobs` → `listJobs(cursor, limit)`
- `GET /api/v1/jobs/{id}` → `getJob(id)`
- `POST /api/v1/jobs` → `createJob(payload)`

### 2.4 Practice Sessions
- `GET /api/v1/sessions` → `listSessions(cursor, limit)`
- `GET /api/v1/sessions/{id}` → `getSession(id)`
- `POST /api/v1/sessions` → `createSession(payload)`
- `POST /api/v1/sessions/{id}/end` → `endSession(id)`
- `GET /api/v1/sessions/{id}/turns` → `getSessionTurns(id)`
- `GET /api/v1/sessions/{id}/debrief` → `getSessionDebrief(id)`

### 2.5 Readiness & Study
- `GET /api/v1/readiness` → `getReadiness()`
- `POST /api/v1/readiness/plan` → `generateReadinessPlan()`
- `GET /api/v1/study` → `listStudyItems(cursor, limit)`
- `POST /api/v1/study/{id}/review` → `reviewItem(id, quality)`
