# PRAXIS InterviewOS — Backup, Restore Drill & Disaster Recovery Report

**Document Version:** 1.0.0  
**Audit Date:** 2026-11-04  
**RTO Objective:** < 30 minutes  
**RPO Objective:** < 1 hour  

---

## 1. Authoritative Backup Strategy

1. **Relational Database (PostgreSQL):**
   - **Automated Daily Backups:** Managed daily snapshots taken at 02:00 UTC.
   - **Point-in-Time Recovery (PITR):** Supported via continuous WAL archiving (7-day window on Pro tier; daily snapshot fallback on Free tier).
   - **Manual Logical Dumps:** Scripted via `scripts/backup-db.ps1` and `scripts/backup.sh` using `pg_dump --format=custom`.
   - **Encryption:** AES-256 encrypted at rest in storage buckets.
2. **Object Storage (GCS / Supabase Storage):**
   - Cloud Storage bucket versioning enabled.
   - Deleted objects retained for 30 days in soft-delete state.
3. **Transient State (Redis):**
   - AOF (Append-Only File) persistence enabled every second; treated strictly as ephemeral cache with zero durable loss on full flush.

---

## 2. Restoration Drill Procedure

```bash
# 1. Provision / Target Disposable Recovery Database
createdb -h localhost -U postgres praxis_recovery_test

# 2. Restore from Custom-Format Backup
pg_restore -h localhost -U postgres -d praxis_recovery_test \
  --clean --if-exists --no-owner --no-privileges \
  backups/praxis_latest.dump

# 3. Verify Relational Integrity & RLS Catalog
psql -h localhost -U postgres -d praxis_recovery_test -c "
  SELECT count(*) FROM pg_class c 
  JOIN pg_namespace n ON n.oid = c.relnamespace 
  WHERE n.nspname = 'public' AND c.relkind = 'r' AND c.relforcerowsecurity = true;
"
# Must return 70 (all business tables have FORCE RLS)

# 4. Verify Extension Availability
psql -h localhost -U postgres -d praxis_recovery_test -c "
  SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';
"
# Must confirm vector extension present
```

---

## 3. Disaster Recovery Governance

- **Disaster Recovery Owner:** Lead Systems Architect
- **Restore Authority:** Senior Engineering Director / Incident Commander
- **Backup Verification Frequency:** Monthly automated restore drill to test database.
