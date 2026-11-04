# PRAXIS InterviewOS — Database Initialization Report

**Document Version:** 1.0.0  
**Audit Date:** 2026-11-04  
**Database Target:** PostgreSQL 17+ with `pgvector`  
**Migration Engine:** Supabase CLI / Native PostgreSQL DDL  

---

## 1. Migration Sequence Audit

All 31 migrations in `supabase/migrations/` follow strict ISO timestamp ordering:

| Sequence | Migration Version | File Name | Core Entities / Functionality |
|---|---|---|---|
| 01 | `20260907235759` | `20260907235759_local_auth_primitives.sql` | `auth.users`, `auth.uid()`, PostgREST session simulation |
| 02 | `20260907235800` | `20260907235800_init_core_schema.sql` | `profiles`, `candidates`, `documents`, `jobs`, `practice_sessions` |
| 03 | `20260907235801` | `20260907235801_add_vector_indexes.sql` | `pgvector` extension, `vector(384)`, HNSW vector indexes |
| 04 | `20260907235802` | `20260907235802_enable_rls_policies.sql` | Baseline RLS policies for candidate ownership |
| 05 | `20260907235803` | `20260907235803_storage_buckets.sql` | Storage bucket permissions (`resumes`, `audio`) |
| 06 | `20260907235804` | `20260907235804_failed_jobs.sql` | Dead-letter queue persistence (`failed_jobs`) |
| 07 | `20260907235805` | `20260907235805_deletion_jobs.sql` | Asynchronous GDPR deletion tracking (`deletion_jobs`) |
| 08 | `20260908000000` | `20260908000000_job_processing_status.sql` | Asynchronous status tracking columns |
| 09 | `20260908000001` | `20260908000001_migration_tracking.sql` | Schema migration history ledger |
| 10 | `20260908000002` | `20260908000002_add_documents_bucket.sql` | Generic document bucket configuration |
| 11 | `20260918000000` | `20260918000000_add_missing_indexes.sql` | Foreign key performance indexes |
| 12 | `20260918000001` | `20260918000001_update_solver_results.sql` | LeetCode/Coding solver run structures |
| 13 | `20260919000000` | `20260919000000_extend_applications.sql` | Job application stage tracking |
| 14 | `20261004000000` | `20261004000000_reconcile_schema.sql` | Synchronizes relational constraints |
| 15 | `20261004000001` | `20261004000001_app_role.sql` | Grants for `praxis_app` non-superuser role |
| 16 | `20261004000002` | `20261004000002_force_rls.sql` | `ALTER TABLE ... FORCE ROW LEVEL SECURITY` across 70 tables |
| 17 | `20261005000001` | `20261005000001_question_bank.sql` | System design & coding question banks |
| 18 | `20261005000002` | `20261005000002_candidate_memory.sql` | Long-term candidate memory & weak areas |
| 19 | `20261005000003` | `20261005000003_adaptive_difficulty.sql` | Difficulty transition matrix & history |
| 20 | `20261005000004` | `20261005000004_interviewer_personality.sql`| Persona configurations & tone prompts |
| 21 | `20261005000005` | `20261005000005_session_analytics.sql` | Per-session aggregate speech & STAR metrics |
| 22 | `20261005000006` | `20261005000006_provider_observability.sql`| Circuit breaker audit & provider health |
| 23 | `20261005000007` | `20261005000007_storage_security.sql` | MIME validation & file path hashing |
| 24 | `20261005000008` | `20261005000008_worker_idempotency.sql`| ARQ job idempotency key store |
| 25 | `20261005000009` | `20261005000009_audit_logs.sql` | Immutable security audit log table |
| 26 | `20261005000010` | `20261005000010_feature_flags.sql` | Dynamic runtime feature flags |
| 27 | `20261005000011` | `20261005000011_coding_engine.sql` | Coding challenge test suites & constraints |
| 28 | `20261005000012` | `20261005000012_system_design_engine.sql`| 24-phase system design rubric schemas |
| 29 | `20261005000013` | `20261005000013_jd_preparation.sql` | JD requirement graphs & skill gap scores |
| 30 | `20261005000014` | `20261005000014_preparation_plans.sql` | Multi-day preparation schedule storage |
| 31 | `20261005000015` | `20261005000015_data_exports.sql` | GDPR export manifest & presigned download metadata |

---

## 2. Catalog Integrity Verification

1. **Foreign Key Integrity:** All relationships enforce `ON DELETE CASCADE` or `ON DELETE SET NULL` as specified in schema.
2. **70/70 FORCE RLS:** `test_all_tables_have_rls_enabled` dynamically inspects `pg_class.relrowsecurity` and `pg_class.relforcerowsecurity` confirming 100% enforcement across all business tables.
3. **Rollback Safety:** Rollforward and corrective migrations are used; existing migrations are never retroactively rewritten.
