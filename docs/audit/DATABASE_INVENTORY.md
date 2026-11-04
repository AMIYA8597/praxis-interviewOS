# PRAXIS InterviewOS — Database & Data Architecture Inventory

**Audit Date:** 2026-11-04  
**Database Engine:** PostgreSQL 18.0 Native / Supabase Postgres  
**Total Tables in Public Schema:** 71  
**Tables with RLS Enabled & Forced:** 70 (All application tables; only internal `schema_migrations` tracking table excluded)  
**Total Migrations Applied:** 31  

---

## 1. Migration Ledger & Integrity Audit

| Migration Name | Scope / Target Domain | Security Controls | Integrity / FK Constraints |
|---|---|---|---|
| `20260907235759_local_auth_primitives.sql` | `auth.users`, `auth.jwt()` mocking functions | Schema isolation | Replaces Supabase Auth primitives in local DB |
| `20260907235800_init_core_schema.sql` | `profiles`, `candidates`, `resumes`, `jobs`, `sessions`, `turns` | Primary tables | `ON DELETE CASCADE` on all candidate foreign keys |
| `20260907235801_add_vector_indexes.sql` | HNSW cosine vector indexes on `document_chunks`, `job_requirements` | Read-only vector search | Requires `pgvector` extension |
| `20260907235802_enable_rls_policies.sql` | Initial RLS policies on candidate-scoped tables | `auth.uid() = profile_id` | Enforces tenant boundary |
| `20260907235803_storage_buckets.sql` | Storage bucket definitions (`resumes`, `audio`) | Public/private toggle | Cascades on bucket deletion |
| `20260907235804_failed_jobs.sql` | Dead-letter storage for unhandled worker errors | Worker ownership | Idempotency tracing |
| `20260907235805_deletion_jobs.sql` | GDPR account deletion job queues & statuses | Admin / system role | Cascading cleanup audit |
| `20260908000000_job_processing_status.sql` | Ingestion status enums (`PENDING`, `PARSING`, `INDEXED`) | Validation triggers | Prevents invalid transitions |
| `20260908000001_migration_tracking.sql` | `schema_migrations` ledger | Idempotent runs | Applied timestamping |
| `20260908000002_add_documents_bucket.sql` | Document storage bucket for reports and exports | Restricted access | Signed URL authorization |
| `20260918000000_add_missing_indexes.sql` | B-tree index creation on FKs (`candidate_id`, `session_id`) | Performance optimization | Non-locking index creation |
| `20260918000001_update_solver_results.sql` | Solver hints, OCR output, and candidate scratchpads | Session scoping | Turn-indexed results |
| `20260919000000_extend_applications.sql` | Application stages, notes, and company metadata | Profile ownership | Cascade on candidate delete |
| `20261004000000_reconcile_schema.sql` | Schema parity reconciliation between SQLAlchemy and SQL | Strict typing | Checks missing columns |
| `20261004000001_app_role.sql` | `praxis_app` database role definition | Principle of least privilege | Revokes superuser/admin grants |
| `20261004000002_force_rls.sql` | `ALTER TABLE ... FORCE ROW LEVEL SECURITY` across tables | Global bypass prevention | Ensures table owners obey RLS |
| `20261005000001_question_bank.sql` | Canonical questions, rubrics, variants, difficulty | Curated content | Versioned prompt rubrics |
| `20261005000002_candidate_memory.sql` | Persistent weaknesses, recurring mistakes, strengths | Candidate scoping | Prevents cross-candidate leaks |
| `20261005000003_adaptive_difficulty.sql` | Dynamic candidate topic mastery & skill progression | Turn-level updates | Bounded difficulty (1-5) |
| `20261005000004_interviewer_personality.sql`| Persona configurations (strict, supportive, probe) | System templates | Configurable tone and style |
| `20261005000005_session_analytics.sql` | Aggregate speech metrics, WPM, filler word density | Session scoping | Derived DSP signals |
| `20261005000006_provider_observability.sql`| AI Gateway provider token counts, latencies, fallbacks | Anonymized telemetry | Never stores raw prompts |
| `20261005000007_storage_security.sql` | Signed URL validation records and access logs | Short TTL tokens | Single-use download links |
| `20261005000008_worker_idempotency.sql` | ARQ job deduplication tokens and execution locks | Redis/PG coordination | Expiration & TTL cleanup |
| `20261005000009_audit_logs.sql` | Security events, auth failures, privilege escalations | Append-only store | Tamper-evident ledger |
| `20261005000010_feature_flags.sql` | Feature flags and per-candidate experimental toggles | Dynamic routing | Instant kill-switches |
| `20261005000011_coding_engine.sql` | LeetCode-style problems, hidden test cases, runs | Isolated sandbox refs | CPU/Memory limit rules |
| `20261005000012_system_design_engine.sql` | 24-phase scenarios, candidate diagrams, trade-offs | Session state | Node/Edge persistence |
| `20261005000013_jd_preparation.sql` | Parsed job blueprints, required skills, mappings | Extracted requirements | Weighting graphs |
| `20261005000014_preparation_plans.sql` | Personalized preparation schedules and milestones | Candidate progress | SM-2 integration |
| `20261005000015_data_exports.sql` | Export requests, status tracking, download expiration | GDPR compliance | Encrypted temporary archives |

---

## 2. Table Ownership, Sensitivity & Retention Summary

| Category | Representative Tables | Row Security | Retention / Deletion Policy |
|---|---|---|---|
| **Identity & Candidate Profile** | `profiles`, `candidates`, `candidate_skills`, `candidate_experiences`, `candidate_projects` | `FORCE RLS` (`auth.uid() = profile_id`) | Cascading delete on user account deletion |
| **Resume & Provenance** | `resumes`, `document_chunks`, `extracted_claims`, `candidate_evidence` | `FORCE RLS` (`auth.uid() = profile_id`) | Cascading delete; files purged from object storage |
| **Job Intelligence** | `jobs`, `job_blueprints`, `job_requirements`, `applications` | `FORCE RLS` (`candidate_id` / `profile_id`) | Retained with application lifecycle |
| **Interview Sessions & Audio** | `practice_sessions`, `session_events`, `session_turns`, `turn_scores`, `transcript_segments` | `FORCE RLS` (`candidate_id` -> `profile_id`) | Retained until candidate deletion; audio chunks scrubbed |
| **Evaluation & Claims** | `answer_evaluations`, `session_claims`, `session_debriefs`, `communication_metrics` | `FORCE RLS` (`candidate_id` -> `profile_id`) | Strictly linked to session; permanent provenance audit |
| **Curated Question Bank** | `question_bank`, `question_variants`, `question_rubrics` | `FORCE RLS` (Read allowed for authenticated, write admin only) | Permanent system content; versioned |
| **Study & Learning Loop** | `study_cards`, `study_card_reviews`, `candidate_memory`, `candidate_weaknesses` | `FORCE RLS` (`candidate_id` -> `profile_id`) | SM-2 review history; deleted on account termination |
| **Security & Operational Logs** | `audit_logs`, `provider_usage_logs`, `failed_jobs`, `worker_idempotency_keys` | `FORCE RLS` (Admin only; read-only for auditors) | 90-day rolling partition; zero PII |

---

## 3. Database Security Controls Audit

1. **FORCE ROW LEVEL SECURITY:**
   - 70 out of 70 business tables enforce `FORCE ROW LEVEL SECURITY`. Even table owners and superusers cannot accidentally bypass candidate isolation policies when executing app queries.
2. **Cascading Integrity:**
   - All foreign keys between parent (`profiles` / `candidates` / `practice_sessions`) and child records enforce `ON DELETE CASCADE`.
   - Verified via `scripts/check_disaster_recovery.py` and `tests/integration/test_deletion_cascade.py`.
3. **App Role Isolation:**
   - In production, connections use the dedicated `praxis_app` database role (`supabase/migrations/20261004000001_app_role.sql`) which possesses only `SELECT`, `INSERT`, `UPDATE`, `DELETE` grants on public tables, preventing schema alterations or privilege escalation.
