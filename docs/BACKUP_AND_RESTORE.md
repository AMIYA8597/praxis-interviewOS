# PRAXIS InterviewOS — Backup, Disaster Recovery & Restoration Runbook

**Document Version:** 1.0.0  
**Scope:** PostgreSQL Relational Database, Memorystore Redis, Object Storage (GCS), and Point-In-Time Recovery (PITR).

---

## 1. Backup Architecture & Recovery Objectives

| Metric | Target Objective | Implementation Mechanism |
|---|---|---|
| **Recovery Point Objective (RPO)** | `< 5 minutes` | Cloud SQL Write-Ahead Log (WAL) archiving with Continuous Point-In-Time Recovery (7 days). |
| **Recovery Time Objective (RTO)** | `< 30 minutes` | Automated Terraform replacement instance + fast snapshot restoration. |
| **Logical Backup Frequency** | Daily at 02:00 UTC | Cloud Scheduler triggering Cloud Function executing `pg_dump -Fc` to private encrypted GCS bucket. |
| **Object Storage Redundancy** | 99.999999999% (11 9s) | Multi-regional Google Cloud Storage bucket with object versioning enabled. |

---

## 2. Automated Logical Backup Execution

### 2.1 Backup Script (`scripts/backup.sh` / `scripts/backup-db.ps1`)
The production backup pipeline executes:

```bash
#!/usr/bin/env bash
set -euo pipefail

BACKUP_DATE=$(date -u +"%Y%m%d_%H%M%SZ")
BACKUP_FILE="/tmp/praxis_backup_${BACKUP_DATE}.dump"
GCS_DESTINATION="gs://${BACKUP_BUCKET}/database/praxis_${BACKUP_DATE}.dump"

echo "==> Creating logical database dump..."
pg_dump \
  -h "${PGHOST}" \
  -U "${PGUSER}" \
  -d "${PGDATABASE}" \
  -F c \
  -b \
  -v \
  -f "${BACKUP_FILE}"

echo "==> Encrypting and uploading to GCS..."
gsutil cp "${BACKUP_FILE}" "${GCS_DESTINATION}"

echo "==> Cleaning local temporary dump..."
rm -f "${BACKUP_FILE}"

echo "Backup completed successfully: ${GCS_DESTINATION}"
```

---

## 3. Step-by-Step Disaster Recovery Runbook

### Scenario A: Accidental Data Corruption or Catastrophic Host Failure

1. **Step 1: Halt Application Ingress**
   Immediately scale Cloud Run API and Realtime services to 0 to prevent dirty writes during recovery:
   ```bash
   gcloud run services update praxis-api --min-instances 0 --max-instances 0 --region asia-south1
   gcloud run services update praxis-realtime --min-instances 0 --max-instances 0 --region asia-south1
   ```

2. **Step 2: Provision Fresh Target Database (if recreating from scratch)**
   ```bash
   cd infra/gcp
   terraform apply -target=google_sql_database_instance.postgres
   ```

3. **Step 3: Restore Database Dump**
   Retrieve the latest verified backup from the secure backup bucket:
   ```bash
   gsutil cp gs://${BACKUP_BUCKET}/database/praxis_latest.dump /tmp/restore.dump
   
   pg_restore \
     -h "${RESTORE_PGHOST}" \
     -U "${RESTORE_PGUSER}" \
     -d praxis \
     -v \
     --clean \
     --if-exists \
     --no-owner \
     /tmp/restore.dump
   ```

4. **Step 4: Verify Migration Parity & RLS Enforcement**
   Run the verification suite against the newly restored database:
   ```powershell
   python scripts/check_production_readiness.py
   python scripts/check_disaster_recovery.py
   ```
   Both checks must output `4/4 passed` and `RLS FORCE ACTIVE` on all 70 tables.

5. **Step 5: Resume Ingress & Validate Startup**
   Restore Cloud Run instance autoscaling:
   ```bash
   gcloud run services update praxis-api --min-instances 1 --max-instances 20 --region asia-south1
   gcloud run services update praxis-realtime --min-instances 1 --max-instances 20 --region asia-south1
   
   curl -fsS https://api.praxis.internal/health/startup
   ```
   The startup probe must return `{"status": "ready", "migrations_current": true}`.

---

## 4. Redis Transient Recovery

Redis contains purely transient data:
- WebSocket connection heartbeats.
- Audio frame client sequence numbers (`last_seq`).
- Rate limiting token buckets.
- ARQ queue job dispatch tokens.

If Redis crashes or Memorystore undergoes maintenance failover:
1. No persistent business data (candidates, resumes, turns, debriefs) is lost.
2. Active WebSockets automatically reconnect within the 30-second grace period.
3. The ARQ worker automatically re-establishes its pool connection and reclaims unacknowledged tasks via the PostgreSQL `failed_jobs` and `deletion_jobs` tables.
