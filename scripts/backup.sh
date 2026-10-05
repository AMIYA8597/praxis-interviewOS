#!/usr/bin/env bash
# PRAXIS Database Backup Script
#
# Creates a logical dump of the Supabase-hosted PostgreSQL database to GCS.
# Designed to run from a Cloud Run job or Cloud Build step.
#
# Required environment variables:
#   SUPABASE_DB_URL     — postgres:// connection string (from Secret Manager)
#   GCS_BACKUP_BUCKET   — GCS bucket name, e.g. praxis-backups-production
#   APP_ENV             — staging | production (used in the backup filename)
#
# Optional:
#   RETAIN_DAYS         — delete backups older than N days (default: 30)
#
# Usage (local, with gcloud auth):
#   SUPABASE_DB_URL="..." GCS_BACKUP_BUCKET="praxis-backups-staging" APP_ENV=staging ./scripts/backup.sh
#
# Restore procedure:
#   1. Download: gsutil cp gs://$GCS_BACKUP_BUCKET/<filename> /tmp/praxis-backup.sql.gz
#   2. Decompress: gunzip /tmp/praxis-backup.sql.gz
#   3. Restore:  pg_restore --clean --if-exists -d "$SUPABASE_DB_URL" /tmp/praxis-backup.sql
#               OR psql "$SUPABASE_DB_URL" < /tmp/praxis-backup.sql  (for plain format)
#   4. Verify:  psql "$SUPABASE_DB_URL" -c "SELECT count(*) FROM candidates;"
#
# RPO target: 24 hours (daily scheduled backup)
# RTO target: < 2 hours (restore + smoke test on a clean database)
set -euo pipefail

: "${SUPABASE_DB_URL:?SUPABASE_DB_URL must be set}"
: "${GCS_BACKUP_BUCKET:?GCS_BACKUP_BUCKET must be set}"
: "${APP_ENV:?APP_ENV must be set}"

RETAIN_DAYS="${RETAIN_DAYS:-30}"
TIMESTAMP=$(date -u +"%Y%m%dT%H%M%SZ")
FILENAME="praxis-${APP_ENV}-${TIMESTAMP}.sql.gz"
TMPFILE=$(mktemp /tmp/praxis-backup-XXXXXX.sql.gz)

echo "[backup] Starting backup of ${APP_ENV} database → gs://${GCS_BACKUP_BUCKET}/${FILENAME}"

# ── Dump ──────────────────────────────────────────────────────────────────────
pg_dump \
    --format=plain \
    --no-password \
    --no-owner \
    --no-acl \
    --quote-all-identifiers \
    "${SUPABASE_DB_URL}" \
  | gzip -9 > "${TMPFILE}"

DUMP_SIZE=$(du -sh "${TMPFILE}" | cut -f1)
echo "[backup] Dump complete. Size: ${DUMP_SIZE}"

# ── Upload ────────────────────────────────────────────────────────────────────
gsutil -q cp "${TMPFILE}" "gs://${GCS_BACKUP_BUCKET}/${FILENAME}"
echo "[backup] Uploaded to gs://${GCS_BACKUP_BUCKET}/${FILENAME}"

# ── Cleanup local temp ────────────────────────────────────────────────────────
rm -f "${TMPFILE}"

# ── Prune old backups ─────────────────────────────────────────────────────────
CUTOFF=$(date -u -d "${RETAIN_DAYS} days ago" +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null \
         || date -u -v-${RETAIN_DAYS}d +"%Y-%m-%dT%H:%M:%SZ")  # macOS fallback

echo "[backup] Pruning backups older than ${RETAIN_DAYS} days (before ${CUTOFF})..."
gsutil ls "gs://${GCS_BACKUP_BUCKET}/praxis-${APP_ENV}-*.sql.gz" 2>/dev/null \
  | while read -r uri; do
      # Extract timestamp from filename: praxis-production-20260901T120000Z.sql.gz → 20260901T120000Z
      ts=$(basename "${uri}" | sed 's/praxis-[^-]*-\([0-9T]*Z\).sql.gz/\1/')
      # Convert yyyymmddThhmmssZ → yyyy-mm-ddThh:mm:ssZ for comparison
      ts_fmt="${ts:0:4}-${ts:4:2}-${ts:6:2}T${ts:9:2}:${ts:11:2}:${ts:13:2}Z"
      if [[ "${ts_fmt}" < "${CUTOFF}" ]]; then
          echo "[backup] Deleting old backup: ${uri}"
          gsutil -q rm "${uri}"
      fi
  done

echo "[backup] Done. Backup stored as: gs://${GCS_BACKUP_BUCKET}/${FILENAME}"
