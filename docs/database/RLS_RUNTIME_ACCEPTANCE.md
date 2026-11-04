# PRAXIS InterviewOS — Row-Level Security (RLS) Runtime Acceptance Report

**Document Version:** 1.0.0  
**Audit Date:** 2026-11-04  
**Audit Standard:** Runtime Context Switch & Multi-Tenant Isolation Testing  

---

## 1. RLS Enforcement Standard

Static counts of `FORCE ROW LEVEL SECURITY` are insufficient proof of isolation. PRAXIS executes dynamic runtime tests (`tests/security/test_rls_isolation.py`) validating cross-tenant security using real database sessions with simulated JWT claims:

```sql
SET ROLE authenticated;
SET request.jwt.claims TO '{"sub": "<user_id>", "role": "authenticated"}';
```

---

## 2. Dynamic Test Results

| Operation | Target Entity | Acting Role | Expected Result | Verified Result | Exit / Status |
|---|---|---|---|---|:---:|
| **SELECT** | `candidates` | User B on User A's record | 0 rows returned | 0 rows returned | **PASS** |
| **SELECT** | `candidate_projects` | User B on User A's record | 0 rows returned | 0 rows returned | **PASS** |
| **SELECT** | `practice_sessions` | User B on User A's record | 0 rows returned | 0 rows returned | **PASS** |
| **UPDATE** | `candidate_projects` | User B on User A's record | 0 rows affected | 0 rows affected | **PASS** |
| **DELETE** | `session_turns` | User B on User A's record | 0 rows affected | 0 rows affected | **PASS** |
| **INSERT** | `candidate_projects` | User B with User A's `candidate_id` | `InsufficientPrivilege` error | `psycopg2.errors.InsufficientPrivilege` | **PASS** |
| **SELECT** | `candidates` | User A on own record | 1 row returned | 1 row returned | **PASS** |
| **UPDATE** | `candidate_projects` | User A on own record | 1 row affected | 1 row affected | **PASS** |

---

## 3. Connection Pool RLS Context Leak Prevention

- **Problem:** Connection pooling can leave transaction-local session state (e.g. `request.jwt.claims`) attached to a connection reused by a different caller.
- **Solution:** Tested in `backend/tests/integration/test_rls_pool_leak.py`. PRAXIS uses transaction-scoped local settings (`SET LOCAL request.jwt.claims = ...`) which automatically clear upon transaction commit/rollback, and `DISCARD ALL` / pool reset hooks guarantee clean connections across callers.
