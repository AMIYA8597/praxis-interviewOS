# PRAXIS InterviewOS — Authorization & Multi-Tenant Isolation Specification

**Milestone**: Phase 4 — Enterprise Security Engineering  
**Branch**: `phase4-security`  
**Date**: 2026-11-01  
**Classification**: AUTHORIZATION & TENANT ISOLATION REPORT  

---

## 1. Multi-Layered Authorization Architecture

Tenant boundary enforcement in PRAXIS operates across three independent architectural layers:

```
[ LAYER 1: API Route Dependencies ]
  - get_current_user / get_current_candidate extracts principal 'sub' strictly from verified RS256 JWT.
  - No client-controlled header (e.g. X-Candidate-ID) can override the authenticated identity.

[ LAYER 2: Service & Data Repository Scoping ]
  - Every data query passes candidate_id = current_candidate["id"] explicitly to service methods.
  - Foreign resources return HTTP 404 (not found) rather than HTTP 403, preventing existence discovery.

[ LAYER 3: PostgreSQL Row Level Security (RLS) ]
  - 100% of the 71 public relational tables have RLS enabled (FORCE ROW LEVEL SECURITY).
  - PostgreSQL evaluates auth.uid() = candidate_id / profile_id at the database storage engine.
```

---

## 2. Row Level Security (RLS) Policy Governance

### 2.1 Table Inventory & Coverage
- Total Relational Tables: **71 public tables** (including `candidates`, `resumes`, `sessions`, `session_turns`, `session_debriefs`, `study_items`, `documents`, `job_postings`, `audit_logs`).
- RLS Policy Coverage: **100%**.
- Connection Pool Isolation: Connection pooling sets local session variables (`SET LOCAL "request.jwt.claim.sub" = :user_id`) during query execution and resets on checkout return (`DISCARD ALL` or `RESET ALL`), preventing connection pool tenant bleed.

### 2.2 Security Definer & RPC Governance
- Functions: `SECURITY DEFINER` is strictly prohibited on user-callable RPC endpoints unless explicitly constrained with a fixed `SET search_path = public, pg_temp` and internal authorization validation.
- Views: All views inherit caller permissions (`security_invoker = true`) to prevent RLS bypass.

---

## 3. Horizontal & Vertical Privilege Escalation Defenses

1. **Horizontal Escalation (Candidate A vs. Candidate B)**:
   - When Candidate B queries `/sessions/{alice_session_id}`, the service executes `SELECT * FROM sessions WHERE id = :id AND candidate_id = :bob_id`.
   - The query returns empty, causing a clean HTTP 404 response. Bob cannot determine whether the session ID exists.
2. **Vertical Escalation (Candidate vs. Administrator)**:
   - Administrative endpoints (`/api/v1/admin/*`) require the `is_admin` claim or verified role in `auth.users.app_metadata`.
   - Regular candidates calling administrative endpoints receive immediate HTTP 403 Forbidden.
