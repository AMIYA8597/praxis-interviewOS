# PRAXIS Backup Strategy
**Phase 97**

---

## Recovery Objectives

| Metric | Target | Achieved by |
|--------|--------|-------------|
| RPO (Recovery Point Objective) | 24h | Supabase daily backups |
| RTO (Recovery Time Objective) | 2h | Snapshot restore + redeploy |
| RPO (with PITR enabled) | 1 min | Supabase PITR (paid plan) |

---

## Backup Types

### 1. Supabase Automatic Backups
- **Frequency:** Daily (Supabase Pro plan)
- **Retention:** 7 days rolling
- **Format:** PostgreSQL snapshot
- **Location:** Supabase-managed (AWS S3, same region as project)
- **Access:** Supabase dashboard → Database → Backups → Download

**REQUIRED:** Use Supabase Pro plan ($25/month minimum). Free tier does not include backups.

### 2. Point-in-Time Recovery (PITR)
- **Available on:** Supabase Pro and above
- **Granularity:** 1-minute recovery points
- **Retention:** 7 days
- **Use when:** Data corruption, accidental deletion within past 7 days

Enable: Supabase dashboard → Database → Backups → Enable PITR

### 3. Off-Site Logical Export (ARQ scheduled job)
- **Frequency:** Weekly (Sunday 02:00 UTC)
- **Format:** pg_dump (plain SQL)
- **Destination:** GCS bucket `praxis-backups-{project-id}` (separate GCP project)
- **Retention:** 4 weekly backups (28 days)
- **Purpose:** Protection against Supabase-level incident; independent of Supabase

```python
# Implemented in backend/app/workers/backup_worker.py
# Job: export_database_to_gcs
# Idempotency key: backup_{date}
```

---

## Restore Procedure

### From Supabase snapshot

```
1. Supabase dashboard → Database → Backups
2. Select the backup point
3. Click "Restore" — this restores to the SAME project
   WARNING: This overwrites the current database. All data since the backup is lost.
4. Monitor restore progress in the Supabase dashboard
5. Run migrations (to verify they are idempotent and current)
6. Run smoke tests
7. Monitor application for 30 minutes
```

### From PITR

```
1. Supabase dashboard → Database → Backups → Point-in-time recovery
2. Select exact timestamp
3. Click "Restore"
4. Same verification steps as above
```

### From off-site pg_dump

```bash
# Restore to a fresh Supabase project
psql -h db.{project-ref}.supabase.co -U postgres -d postgres \
  < praxis_backup_2026_10_05.sql

# Run migrations to ensure schema is current
DATABASE_URL=<new-project-url> python scripts/migrate.py
```

---

## Backup Verification (Restore Drill)

**A backup that has never been restored is NOT considered verified.**

Restore drill procedure (quarterly):
1. Create a temporary Supabase project
2. Restore latest off-site pg_dump to it
3. Run `python scripts/migrate.py` against the restored project — must be no-op
4. Run the RLS security test suite against the restored project
5. Verify row count matches production (within expected delta)
6. Delete the temporary project

Drill frequency: **quarterly minimum, before major releases**.

---

## What Is Backed Up

✅ PostgreSQL user data (all tables)
✅ Supabase Storage file metadata (in Postgres)
✅ Authentication user records (in Postgres)

❌ Supabase Storage file objects (resumes, audio) — **not included in database backups**

### Storage Object Backup

Resume PDFs and documents must be backed up separately:

```bash
# Sync Supabase Storage objects to GCS (weekly, via worker)
# Implemented in backend/app/workers/backup_worker.py: backup_storage_objects
```

---

## Backup Monitoring

Alert when:
- Weekly pg_dump job fails (ARQ dead-letter + alert)
- Backup file size < 50% of previous week (anomaly detection)
- Restore drill has not been completed in > 90 days

---

## Data Retention Policy

| Data type | Retention |
|-----------|-----------|
| Session transcripts | Indefinite (candidate-owned) |
| Audio recordings | 30 days (auto-deleted by worker) |
| Resume files | Until candidate deletion request |
| AI provider logs | 90 days |
| Worker idempotency log | 7 days |
| Session state (Redis) | 2 hours TTL |
