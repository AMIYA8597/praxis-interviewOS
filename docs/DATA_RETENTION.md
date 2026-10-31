# Data Retention Policy

Defines how long each category of data is kept and when it is deleted.

Last reviewed: 2026-10-05

---

## Default retention periods

| Data category | Default retention | Configurable? | Enforcement |
|---------------|------------------|---------------|-------------|
| Session transcripts (`transcript_segments`) | 365 days | Yes, per-user `data_retention_days` | `purge_expired_retention_data` ARQ cron (daily at 03:00 UTC) |
| Uploaded documents (`documents` + GCS blobs) | 365 days | Yes | Same cron |
| AI call logs (`ai_call_log`) | 90 days | No | Separate cron (planned) |
| Worker dead letters (`failed_jobs`) | 30 days | No | Separate cron (planned) |
| `worker_idempotency_log` (completed) | 7 days | No | Noted in migration; cron (planned) |
| Export files (`candidate_data_exports`) | 24 hours (signed URL) | No | `run_data_export` sets `expires_at`; auto-expire logic in `GET /export/{id}` |
| Privacy events (`privacy_events`) | Permanent | No | Never purged (regulatory) |
| Deletion jobs (`deletion_jobs`) | Permanent | No | Never purged (regulatory) |
| Account data (all tables) | Until explicit deletion | — | `delete_candidate_account_job` |

---

## Per-user retention configuration

Candidates can configure their personal retention window via `user_settings.data_retention_days`.

| Value | Effect |
|-------|--------|
| `NULL` (default) | Uses system default (365 days for transcripts/documents) |
| 0 | Immediate deletion not supported; minimum 7 days enforced |
| 1–36500 | Data older than N days is deleted by the nightly cron |

The setting is honoured by `purge_expired_retention_data` in `backend/app/worker_tasks.py`.

---

## Account deletion (erasure request)

`DELETE /api/v1/candidates/me` initiates an async deletion job.
The `DeletionService` (`backend/app/core/deletion.py`) deletes:

1. All GCS blobs owned by the candidate (document uploads, export files).
2. All database rows across all tables (cascaded via foreign keys).
3. The `candidates` row itself.

A `deletion_jobs` record is retained permanently as a GDPR erasure audit trail.
A `privacy_events` row is inserted with `event_type = 'account_deleted'`.

Supabase Auth user deletion must be performed separately via the Supabase Admin API
(BLOCKED — requires provisioned Supabase project).

---

## Cron schedule

| Job | Schedule | Purpose |
|-----|----------|---------|
| `purge_expired_retention_data` | Daily 03:00 UTC | Transcript + document purge |
| `cleanup_old_sessions` | Every 15 min | Abandon stalled sessions |

---

## BLOCKED

- `ai_call_log` auto-purge cron: defined by policy; cron job not yet registered
  (table exists, `created_at` index exists).
- `failed_jobs` auto-purge cron: same status.
- `worker_idempotency_log` auto-purge: noted in migration; cron job pending.

These do not affect staging readiness but should be added before production launch.
