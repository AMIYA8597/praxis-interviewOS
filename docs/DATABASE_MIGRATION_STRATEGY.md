# PRAXIS Database Migration Strategy

## 1. Authority & Migration Architecture

`supabase/migrations/*.sql` is the **single source of truth** for all database schema, indexes, functions, triggers, and Row-Level Security policies in the PRAXIS platform.

- **Alembic Reconciled & Retired**: Historical Alembic migrations in `backend/alembic/versions` are officially retired (`backend/alembic/versions/README.md` documents retirement). Alembic must never be used to introduce divergent schema definitions.
- **Zero Duplicate Version Prefixes**: All 31 migration files have verified unique, chronological timestamp prefixes.
- **Idempotency Guarantee**: Every migration is executed through `scripts/migrate.py`. Running migrations on a fresh database applies all 31 files; running a second time applies 0 migrations without raising errors or creating duplicates.

---

## 2. Chronological Migration Inventory

| Version Prefix | Migration File | Description & Domain |
|---|---|---|
| `20260907235759` | `local_auth_primitives.sql` | Mock Supabase `auth.users` table and schema for local/testing environments |
| `20260907235800` | `core_schema.sql` | Base schema: candidates, documents, jobs, interview sessions, turns |
| `20260907235801` | `pgvector_embeddings.sql` | pgvector extension, dense embeddings `vector(384)`, HNSW cosine index |
| `20260907235802` | `enable_rls_policies.sql` | Base RLS policies for candidates, documents, chunks, and sessions |
| `20260908000000` | `study_system.sql` | Study plans, SM-2 study items, review tracking, readiness snapshots |
| `20260908000001` | `migration_tracking.sql` | Migration status and timing instrumentation (`log_migration()`) |
| `20260908000002` | `session_debriefs.sql` | Session debrief metrics, strengths, weaknesses, and claim coverage |
| `20260908000003` | `turn_metrics.sql` | Turn-level audio and DSP metrics (WPM, filler rate, pauses) |
| `20260909000001` | `job_blueprints.sql` | Job blueprints, categorized requirements, and predicted evaluation topics |
| `20260910000001` | `resume_claims.sql` | Atomic resume claims, extraction confidence, and user verification flags |
| `20260911000001` | `audio_metadata.sql` | Audio file pointers, sample rate, duration, and storage references |
| `20260912000001` | `profiles_table.sql` | User profiles, notification flags, theme, and localized candidate preferences |
| `20260913000001` | `admin_users.sql` | Admin role table and permission enforcement function |
| `20260914000001` | `rate_limits.sql` | Database-backed rate limiting accounting and quota tracking |
| `20260915000001` | `feature_flags.sql` | Operational feature toggles with rollout percentages |
| `20260916000001` | `audit_logs.sql` | Administrative and security action auditing log table |
| `20260917000001` | `interview_engines.sql` | Behavioral, coding, and system design specialized engine state |
| `20260918000000` | `candidate_memory.sql` | Cross-session candidate intelligence and recurring weakness memory |
| `20260918000001` | `memory_embeddings.sql` | Vector index for semantic retrieval of candidate memory items |
| `20260919000001` | `preparation_engine.sql`| Personalized preparation plans and milestone tracking |
| `20260920000001` | `outreach_applications.sql` | Outreach drafts, recruiter contacts, and job application stages |
| `20260921000001` | `coding_sandbox.sql` | Execution logs and verification metrics for coding sandboxes |
| `20261001000001` | `fts_indexes.sql` | GIN indexes on full-text vectors for lexical document search |
| `20261002000001` | `fk_cascades.sql` | Explicit `ON DELETE CASCADE` on child tables linked to candidates |
| `20261003000001` | `foreign_key_indexes.sql`| Performance B-Tree indexes on all foreign key reference columns |
| `20261004000001` | `praxis_app_role.sql` | Least-privilege `praxis_app` (`NOBYPASSRLS`) database role |
| `20261004000002` | `force_rls.sql` | `FORCE ROW LEVEL SECURITY` applied across all tenant tables |
| `20261005000001` | `idempotency_keys.sql` | Background worker and API write idempotency tracking table |
| `20261005000002` | `quota_limits.sql` | Tier-based usage limits and subscription plan tracking |
| `20261005000009` | `audit_logs_v2.sql` | Extended audit logging with request correlation IDs and user agent |
| `20261005000010` | `feature_flags_v2.sql` | Feature flag overrides per candidate and environment |

---

## 3. Migration Runner (`scripts/migrate.py`) Implementation

### 3.1 Bootstrap Phase
Before executing migrations, `scripts/migrate.py` bootstraps the tracking infrastructure:
```sql
CREATE TABLE IF NOT EXISTS schema_migrations (
    version text PRIMARY KEY,
    applied_at timestamp with time zone DEFAULT now()
);
```
It immediately applies `20260908000001_migration_tracking.sql` to establish `migration_status` and the stored procedure `log_migration(version, name, execution_time_ms, status)`.

### 3.2 Adaptive SQL Parser (`adapt_sql`)
To support diverse development environments:
- Automatically detects whether `pgvector` is available (`CREATE EXTENSION IF NOT EXISTS vector`).
- If `pgvector` is present: executes HNSW vector indexing and cosine distance queries unchanged.
- If `pgvector` is absent (e.g. standard local Postgres without extension compiled): gracefully degrades `vector(384)` to `text` and removes `USING hnsw` without halting execution.

### 3.3 Transaction Boundary & Execution
Each migration file is executed inside its own dedicated atomic transaction:
```python
async with conn.transaction():
    await conn.execute(sql)
    await conn.execute("INSERT INTO schema_migrations (version) VALUES ($1)", version)
```
If a migration fails:
1. The transaction rolls back cleanly.
2. The failure duration and error are logged in `migration_status(status = 'failed')`.
3. Execution terminates immediately, leaving previous successful migrations intact.

---

## 4. Roll-Forward Recovery Policy

1. **Never Edit Applied Migrations**: Once a migration file has been applied to any staging or production database, it is immutable. Its contents, name, and checksum must not be modified.
2. **Forward-Only Corrections**: If an error is detected in an applied schema, author a new sequential migration (e.g. `20261006000001_fix_column_constraint.sql`) that performs `ALTER TABLE` to rectify the issue.
3. **Rollback Strategy**: Rollbacks are executed by applying compensating forward migrations rather than running destructive `DOWN` scripts.

---

## 5. Drift Detection & CI Validation

- In CI, `scripts/migrate.py` runs against a fresh database service.
- The step executes `scripts/migrate.py` a second time and asserts that zero migrations are applied:
  ```bash
  python scripts/migrate.py
  python scripts/migrate.py | tee /tmp/migrate-rerun.log
  if grep -q '^Applying ' /tmp/migrate-rerun.log; then
    echo "Migration runner is not idempotent!" && exit 1
  fi
  ```
- Startup health probe `/health/startup` validates at runtime that the count of applied records in `schema_migrations` matches the migration files present on disk.
