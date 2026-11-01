# PRAXIS InterviewOS — Tenant Isolation Test Matrix

**Milestone**: Phase 4 — Enterprise Security Engineering  
**Branch**: `phase4-security`  
**Date**: 2026-11-01  
**Classification**: REGRESSION TEST MATRIX  

---

## 1. Test Methodology

The tenant isolation test harness creates two completely independent test identities:
- **Candidate Alice (`alice_id = uuid4()`)**
- **Candidate Bob (`bob_id = uuid4()`)**

Alice creates a full set of candidate resources: profile, target roles, resume documents, extracted claims, practice sessions, session turns, debriefs, job applications, and study items. Bob then attempts unauthorized operations against Alice's resources across REST API, WebSocket transport, background workers, and direct database queries.

---

## 2. Test Execution Matrix

| Test ID | Operation Attempted by Bob | Target Resource of Alice | Expected Result | Actual Code / Behavior | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `ISO-01` | `GET /candidates/me` | Alice's Candidate Profile | Returns Bob's profile only | Auth principal derives from token `sub` | **PASS** |
| `ISO-02` | `GET /sessions/{alice_id}` | Alice's Mock Session | HTTP 404 (Not Found) | Scoped to `candidate_id = bob_id` | **PASS** |
| `ISO-03` | `GET /sessions/{alice_id}/turns` | Alice's Spoken Audio Turns | HTTP 404 (Not Found) | Scoped to `candidate_id = bob_id` | **PASS** |
| `ISO-04` | `GET /sessions/{alice_id}/debrief`| Alice's Debrief & Scores | HTTP 404 (Not Found) | Debrief bound to session ownership | **PASS** |
| `ISO-05` | `POST /sessions/{alice_id}/end` | Conclude Alice's Session | HTTP 404 (Not Found) | Rejects state change on non-owned session | **PASS** |
| `ISO-06` | `GET /resumes/{alice_id}` | Alice's Resume Document | HTTP 404 (Not Found) | Scoped to `candidate_id = bob_id` | **PASS** |
| `ISO-07` | `GET /resumes/{alice_id}/facts` | Alice's Document Claims | HTTP 404 (Not Found) | Nested endpoint checks parent ownership | **PASS** |
| `ISO-08` | `POST /resumes/{alice_id}/facts/{id}/confirm` | Confirm Alice's Fact | HTTP 404 (Not Found) | Rejects claim verification tampering | **PASS** |
| `ISO-09` | `PATCH /projects/{alice_id}` | Modify Alice's Project | HTTP 404 (Not Found) | Project update scoped to owner | **PASS** |
| `ISO-10` | `DELETE /projects/{alice_id}` | Delete Alice's Project | HTTP 404 (Not Found) | Deletion query returns 0 rows affected | **PASS** |
| `ISO-11` | `GET /sessions` | Alice's Session History | Returns `[]` (Empty List) | List query filters by Bob's candidate ID | **PASS** |
| `ISO-12` | `GET /resumes` | Alice's Uploaded Resumes | Returns `[]` (Empty List) | List query filters by Bob's candidate ID | **PASS** |
| `ISO-13` | `POST /sessions` with `job_id = alice_job` | Link Alice's Target Job | HTTP 404 (Not Found) | Rejects cross-tenant job linking | **PASS** |
| `ISO-14` | Connect WebSocket `/ws/sessions/{alice_id}` | Alice's Live Speech Stream | HTTP 403 / Close 4003 | WebSocket checks session candidate_id | **PASS** |
| `ISO-15` | Hybrid RAG retrieval query | Alice's Project Embeddings | Returns 0 Alice chunks | Vector search SQL filters `candidate_id` | **PASS** |
| `ISO-16` | Direct SQL query without `WHERE` filter | 71 PostgreSQL Tables | Returns 0 Alice rows | PostgreSQL RLS filters by session JWT | **PASS** |

---

## 3. Automated Test Evidence
- REST API Isolation: `backend/tests/hardening/test_authorization.py` (100% passing).
- Database RLS Isolation: `backend/tests/security/test_rls_isolation.py` and `backend/tests/integration/test_rls_bypass.py`.
- RAG Vector Isolation: `packages/ai-gateway/tests/test_hybrid_retrieval.py` and `backend/tests/security/test_rag_isolation.py`.
