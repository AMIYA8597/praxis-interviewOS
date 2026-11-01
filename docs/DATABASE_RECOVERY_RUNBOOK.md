# PRAXIS Database Recovery Runbook

**Service**: Supabase PostgreSQL (Managed Infrastructure)  
**Target RTO (Recovery Time Objective)**: < 1 hour  
**Target RPO (Recovery Point Objective)**: < 1 hour (Continuous WAL archiving)  
**Audience**: DevOps, SRE, and Backend On-Call Engineers  

---

## 1. Failure Scenarios & Recovery Procedures

### Scenario 1: Connection Pool Exhaustion (`sorry, too many clients already`)

**Symptoms**:
- API requests fail with HTTP 503 `OperationalError: remaining connection slots are reserved for non-replication superuser connections` or `sorry, too many clients already`.
- Cloud Monitoring alerts trigger on `db_connection_pool_saturation > 90%`.

**Diagnosis**:
1. Check active client connections on Supabase Dashboard -> Database -> Connections.
2. Query active connection counts by application name:
   ```sql
   SELECT application_name, count(*) 
   FROM pg_stat_activity 
   WHERE state = 'active' 
   GROUP BY application_name;
   ```

**Immediate Mitigation**:
1. Verify Cloud Run scaling instances:
   ```bash
   gcloud run services describe praxis-api --region asia-south1 --format="value(status.traffic)"
   ```
2. Verify application connection settings against [DATABASE_CONNECTION_BUDGET.md](file:///d:/work/interviewOS/docs/DATABASE_CONNECTION_BUDGET.md):
   - `DB_POOL_SIZE` must be set to `2`.
   - `DB_MAX_OVERFLOW` must be set to `3`.
3. If non-pooler connections were accidentally used: update `DATABASE_URL` in Secret Manager to the Supabase transaction pooler URL (`pooler.supabase.com`, port `6543` or `5432` with transaction mode).
4. Terminate orphaned idle transactions:
   ```sql
   SELECT pg_terminate_backend(pid) 
   FROM pg_stat_activity 
   WHERE state = 'idle in transaction' 
     AND state_change < now() - INTERVAL '5 minutes';
   ```

---

### Scenario 2: Failed or Partially Applied Database Migration

**Symptoms**:
- `/health/startup` probe returns HTTP 503 `Pending database migrations` or `schema_migrations unqueryable`.
- Migration step in CI or deployment fails with a SQL syntax or constraint violation error.

**Diagnosis**:
1. Inspect `migration_status` table to identify the failed file and error message:
   ```sql
   SELECT version, name, execution_time_ms, status 
   FROM migration_status 
   WHERE status = 'failed' 
   ORDER BY executed_at DESC 
   LIMIT 1;
   ```
2. Check `schema_migrations` to see the last cleanly applied version:
   ```sql
   SELECT version, applied_at FROM schema_migrations ORDER BY version DESC LIMIT 5;
   ```

**Recovery Procedure**:
1. Because `scripts/migrate.py` wraps each file in an atomic transaction (`async with conn.transaction():`), the failed migration rolled back completely.
2. Do **NOT** edit the failed file if it was already applied to other environments.
3. Write a forward-correction migration file with the next sequential timestamp.
4. Run `python scripts/migrate.py` against the staging database to confirm clean application.
5. Deploy the updated code to Cloud Run.

---

### Scenario 3: Accidental Data Deletion or Table Corruption (PITR Recovery)

**Symptoms**:
- Severe data corruption or accidental tenant record deletion caused by human error or script misconfiguration.

**Recovery Procedure via Supabase Point-in-Time Recovery (PITR)**:
1. Open Supabase Management Dashboard -> Settings -> Backups -> Point in Time Recovery.
2. Identify the exact UTC timestamp immediately prior to the corrupting event (e.g. `2026-11-01T11:45:00Z`).
3. **DO NOT restore in-place over the active production database**:
   - Provision a fresh temporary Supabase recovery instance.
   - Restore the PITR snapshot to the temporary instance.
4. Verify table integrity on the restored instance:
   ```bash
   psql "$RECOVERY_DATABASE_URL" -c "SELECT count(*) FROM candidates; SELECT count(*) FROM documents;"
   ```
5. Export only the affected tables/rows from the recovery database:
   ```bash
   pg_dump "$RECOVERY_DATABASE_URL" --data-only --table=candidates --table=documents -f recovery_data.sql
   ```
6. Import the extracted records into the active database inside a controlled maintenance window:
   ```bash
   psql "$PRIMARY_DATABASE_URL" -f recovery_data.sql
   ```
7. Verify candidate access and confirm RLS policies are functioning as expected.

---

### Scenario 4: PgBouncer Prepared Statement Cache Conflict

**Symptoms**:
- Application crashes with `DuplicatePreparedStatementError` or `prepared statement "..." already exists`.

**Cause**:
- Asyncpg prepared statement caching enabled while connecting through a transaction-mode PgBouncer pooler.

**Verification & Fix**:
- Inspect `backend/app/db/session.py`. Ensure `connect_args` includes:
  ```python
  connect_args = {
      "statement_cache_size": 0,
      "prepared_statement_cache_size": 0,
  }
  ```
- If running sync tools (alembic / psycopg2), verify that pgbouncer transaction mode does not attempt multi-statement server-side named cursors.
