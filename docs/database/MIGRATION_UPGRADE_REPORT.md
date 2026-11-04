# PRAXIS InterviewOS — Migration Upgrade & Data Preservation Report

**Document Version:** 1.0.0  
**Audit Date:** 2026-11-04  

---

## 1. Migration Upgrade Invariants

1. **Non-Destructive DDL:** Migrations use additive patterns (`ADD COLUMN IF NOT EXISTS`, `CREATE TABLE IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`) to prevent failure when re-run.
2. **Data Relationship Preservation:** Verified that upgrading schemas from Phase 1 through Phase 5 preserves existing candidate profiles, resume chunks, sessions, and study items without data corruption.
3. **Cascading Deletion Integrity:** Verified via `tests/integration/test_deletion_cascade.py` that cascading foreign keys maintain referential integrity when accounts are deleted, preventing orphan child records.
4. **Idempotent Application:** Supabase migration tracking (`schema_migrations`) guarantees that each migration script executes exactly once.
