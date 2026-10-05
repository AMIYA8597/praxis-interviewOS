# PRAXIS Backup Strategy

## Database (Supabase PostgreSQL)

### Automated backups (Supabase managed)

| Plan | Backup Frequency | Retention | Point-in-Time Recovery |
|---|---|---|---|
| Free | Daily | 7 days | No |
| Pro | Daily | 30 days | Yes (PITR to any second in the window) |

**Recommendation**: Use Supabase Pro for staging and production to enable PITR.

### Manual backup script

`scripts/backup.sh` creates a `pg_dump` backup of the database.

```bash
# Manual backup (from a machine with psql access):
bash scripts/backup.sh
# Output: backup_YYYYMMDD_HHMMSS.sql.gz in ./backups/

# Upload to GCS (replace BUCKET):
gsutil cp ./backups/backup_*.sql.gz gs://praxis-backups-staging/database/
```

**Status**: Script exists. Scheduled execution via Cloud Scheduler is NOT yet provisioned.

### Backup schedule (target)

| Environment | Frequency | Retention | Method |
|---|---|---|---|
| Staging | Daily | 14 days | Supabase automated + manual script |
| Production | Continuous PITR | 30 days | Supabase Pro PITR |
| Production manual | Weekly | 90 days | `scripts/backup.sh` → GCS |

### GCS backup bucket (to be created)

```bash
gcloud storage buckets create gs://praxis-backups-staging \
  --project=praxis-staging \
  --location=us-central1 \
  --public-access-prevention
```

---

## Redis (Memorystore)

Redis is a **cache and job queue** — not a primary data store.

### What is in Redis

| Key pattern | Data | Durability requirement |
|---|---|---|
| `arq:queue` | Pending jobs | HIGH — job loss = missed processing |
| `arq:failed_jobs` | Failed jobs | MEDIUM — can be reconstructed from DB |
| `arq:in_progress` | In-flight jobs | LOW — recovered on worker restart |
| `jwks:cache` | JWKS keys | LOW — refreshed from Supabase on cache miss |
| `candidate:*` | Auth user→candidate cache | LOW — re-derived on miss |

**ARQ job durability**: ARQ uses Redis RPOPLPUSH for at-least-once delivery. In-flight jobs are re-queued if the worker crashes before acknowledgement. The database is the source of truth for completed job results.

### Redis backup

Memorystore BASIC tier: no persistence by default.  
Memorystore STANDARD tier: RDB snapshots available.

**Recommendation**: Use STANDARD tier for production with RDB persistence interval of 1 hour.

For staging, BASIC tier is acceptable since Redis data is expendable (jobs can be re-queued from the database).

---

## Application code

All code is in Git (GitHub). The Git repository is the authoritative backup of application code.

**No additional backup required.**

---

## Secrets

Secrets in Secret Manager retain all historical versions automatically. Version deletion requires explicit action.

**Rotate secrets on schedule**:
- Supabase service role key: every 90 days
- Fernet key: no rotation without coordinated re-encryption of stored data
- AI provider keys: rotate if exposed or on provider's recommended schedule

---

## Recovery Priority

| Asset | RPO | RTO | Recovery Method |
|---|---|---|---|
| PostgreSQL database | < 1 hour (Pro PITR) | < 30 min | Supabase PITR or restore from pg_dump |
| Redis | 0 (acceptable loss) | < 5 min | Restart; workers re-queue from DB state |
| Container images | 0 (git SHA is source of truth) | < 20 min | Re-build from git commit |
| Secrets | 0 (versioned in Secret Manager) | < 5 min | Re-read from Secret Manager |
| Application code | 0 (Git) | < 10 min | Re-deploy from git |

---

*Last updated: 2026-10-05*
