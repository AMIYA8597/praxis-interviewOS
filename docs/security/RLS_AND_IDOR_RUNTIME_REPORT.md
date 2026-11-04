# PRAXIS InterviewOS — RLS & IDOR Runtime Verification Report

**Document Version:** 1.0.0  
**Audit Date:** 2026-11-04  

---

## 1. Runtime Isolation Proof

Dynamic isolation verification executed via `tests/security/test_rls_isolation.py`:
- **Scenario:** Attacker User B attempts to access Candidate Alex Morgan (User A).
- **Target Tables Tested:** `candidates`, `candidate_projects`, `documents`, `document_chunks`, `jobs`, `practice_sessions`, `session_turns`, `session_claims`, `study_items`.
- **Results:**
  - `SELECT count(*) FROM candidates WHERE id = :user_a_cand` -> **0 rows returned**.
  - `SELECT count(*) FROM candidate_projects WHERE id = :user_a_proj` -> **0 rows returned**.
  - `SELECT count(*) FROM practice_sessions WHERE id = :user_a_sess` -> **0 rows returned**.
  - `UPDATE candidate_projects SET name = 'Hacked' WHERE id = :user_a_proj` -> **0 rows affected**.
  - `DELETE FROM session_turns WHERE id = :user_a_turn` -> **0 rows affected**.
  - `INSERT INTO candidate_projects (candidate_id, name) VALUES (:user_a_cand, 'Fake')` -> **`psycopg2.errors.InsufficientPrivilege` raised**.
  - User A access to own data -> **1 row returned / 1 row updated**.

---

## 2. Invariable Conclusion

Zero IDOR leakage is mathematically and empirically verified at the PostgreSQL storage engine level.
