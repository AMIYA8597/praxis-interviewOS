# PRAXIS Backend Deployment

This document covers the three production Docker images, the Cloud Build CI/CD pipeline,
GCP infrastructure topology, and operational guidance for deployments.

---

## 1. Docker Images

Three images are maintained in `docker/`. All use Python 3.11.11-slim, multi-stage builds,
`requirements-lock.txt` for deterministic dependencies, and run as the non-root `praxis`
user.

| Image | Dockerfile | Serves | Port |
|---|---|---|---|
| `praxis-api` | `docker/Dockerfile.api` | FastAPI REST API | 8000 |
| `praxis-realtime` | `docker/Dockerfile.realtime` | WebSocket / realtime audio | 8080 |
| `praxis-worker` | `docker/Dockerfile.worker` | ARQ task queue workers | — |

### Build stages (all three images)

1. **deps** — Install build tools, copy `requirements-lock.txt`, create venv, install all deps.
2. **source** — Copy `packages/`, application code, install as editable packages.
3. **production** — Runtime-only system packages, copy venv + source from prior stages,
   drop to `praxis` user.

The build context is the repository root (required because `backend/` depends on
`packages/config` and `packages/ai-gateway`).

### Image-specific notes

**praxis-api** (`docker/Dockerfile.api`):
- Includes `tesseract-ocr` for document parsing.
- CMD: `uvicorn backend.app.main:app --workers 1 --timeout-graceful-shutdown 30`
- HEALTHCHECK: `GET /health` every 30s, 60s start period.

**praxis-realtime** (`docker/Dockerfile.realtime`):
- Includes `torch==2.5.1+cpu`, `torchaudio`, `faster-whisper==1.1.0`, `silero-vad==5.1.2`,
  `onnxruntime==1.20.1`, `librosa`, `ffmpeg`.
- Does NOT include `sounddevice`/`pyaudio` — the server receives audio bytes from clients,
  it does not capture audio locally.
- Models baked at build time to avoid cold-start downloads:
  `WhisperModel('base.en', ...)` and `silero_vad.load_silero_vad()` run during `docker build`.
- `cpu_idle = false` in Terraform: realtime instances stay warm for low audio latency.

**praxis-worker** (`docker/Dockerfile.worker`):
- Includes `sentence-transformers==3.3.1` and `torch==2.5.1+cpu` for local embeddings.
- Includes `tesseract-ocr` for document parsing.
- No HTTP server; connects to Redis and runs ARQ worker loop.

---

## 2. Cloud Build CI/CD

Pipeline: `cloudbuild.yaml` (repository root). Triggered on push to `main`.

### Substitutions

| Variable | Description | Example |
|---|---|---|
| `_REGION` | GCP region | `us-central1` |
| `_REGISTRY` | Artifact Registry path | `us-central1-docker.pkg.dev/${PROJECT_ID}/praxis` |
| `_IMAGE_TAG` | Image tag | `${SHORT_SHA}` (git short SHA) |
| `_STAGING_API_URL` | Staging health check URL | Set by Cloud Build trigger |

### Pipeline steps

1. **build-api, build-realtime, build-worker** — Parallel builds using `--cache-from :latest`.
2. **push-api, push-realtime, push-worker** — Push tagged images to Artifact Registry.
3. **deploy-staging-api/realtime/worker** — `gcloud run deploy` to `praxis-staging` project.
4. **staging-smoke-test** — `GET ${STAGING_API_URL}/health` must return HTTP 200.
5. **tag-latest** — Tags all three images as `:latest` after smoke test passes.

Machine: `E2_HIGHCPU_8`. Timeout: 3600s. Logging: `CLOUD_LOGGING_ONLY`.

---

## 3. GCP Infrastructure (Terraform)

Source: `infra/gcp/main.tf`. Not yet provisioned — all infrastructure is defined but
GCP projects have not been created. See capability matrix for verification status.

### Services provisioned

| Resource | Type | Notes |
|---|---|---|
| VPC | `google_compute_network` | Per-environment private network |
| Serverless VPC connector | `google_vpc_access_connector` | Cloud Run → Redis private access |
| Memorystore Redis | `google_redis_instance` | REDIS_7_2, BASIC tier, 1GB default |
| Artifact Registry | `google_artifact_registry_repository` | Docker format, shared across environments |
| Cloud Run API | `google_cloud_run_v2_service` | Internal LB ingress |
| Cloud Run Realtime | `google_cloud_run_v2_service` | Internal LB ingress, 3600s timeout |
| Global HTTPS LB | URL map + NEG + SSL cert | api.domain → API, realtime.domain → Realtime |
| Cloud Armor | `google_compute_security_policy` | Rate limit 100 req/60s/IP, SQLi + XSS rules |
| Secret Manager | (referenced in containers) | All secrets as env vars |
| IAM service accounts | Per-service + deployer | Least-privilege bindings |
| Workload Identity | GitHub Actions OIDC | No long-lived key files |

### Cloud Run scaling parameters (Terraform defaults)

| Service | Min instances | Max instances | CPU | Memory | Notes |
|---|---|---|---|---|---|
| praxis-api | 1 | 10 | 1000m | 512Mi | `cpu_idle = true` |
| praxis-realtime | 1 | 5 | 2000m | 2Gi | `cpu_idle = false` (always-on) |
| praxis-worker | Not in Terraform yet | — | — | — | Worker pool not yet defined in IaC |

### Database connection budget

Cloud Run can scale concurrently. Supabase enforces connection limits.

Formula: `max_instances × connections_per_instance × service_count ≤ Supabase pool size`

| Tier | Pool size |
|---|---|
| Supabase Free | 60 connections |
| Supabase Pro | 200 connections |

With Terraform defaults (api max=10, realtime max=5) and 2 connections per instance:
- API: 10 × 2 = 20
- Realtime: 5 × 2 = 10
- Worker (assumed 5 max): 5 × 2 = 10
- Total: ~40 — fits on Supabase Free tier with headroom.

If scaling to api max=20, realtime max=10, worker max=5:
- Total: 20×2 + 10×2 + 5×2 = 70 — requires Supabase Pro (200 connections).

**Recommendation**: use PgBouncer (Supabase built-in transaction pooler) to reduce
direct connection count before scaling beyond Free tier.

---

## 4. Environment Variables and Secrets

All secrets come from Secret Manager — no `.env` files in production.
Secrets are mounted as env vars in the Cloud Run container spec via `secret_key_ref`.

Secrets defined in `infra/gcp/main.tf`:

| Secret name | Used by | Purpose |
|---|---|---|
| `praxis-database-url` | api, realtime, worker | Supabase connection string |
| `praxis-redis-url` | api, realtime | Memorystore Redis URL |
| `praxis-supabase-url` | api | Supabase project URL for JWKS |
| `praxis-supabase-anon-key` | api | Supabase anon key |

Additional provider API keys (`GROQ_API_KEY`, `OPENAI_API_KEY`, etc.) should be added
as separate secrets and mounted identically.

---

## 5. Staging vs. Production Separation

| Aspect | Staging | Production |
|---|---|---|
| GCP project | `praxis-staging` | `praxis-production` |
| Supabase project | Separate | Separate |
| Redis | Separate Memorystore | Separate Memorystore |
| Secret Manager | Per-project | Per-project |
| Terraform tfvars | `environments/staging/terraform.tfvars` | `environments/production/terraform.tfvars` |
| Deployed by | Cloud Build on push to `main` | Manual promotion or separate trigger |

Staging is deployed automatically after every merge to `main`. Production promotion
requires explicit `gcloud run services update-traffic` or a manual Cloud Build trigger.

---

## 6. Migration Safety

Migrations run from `supabase/migrations/`. They are applied before deploying a new
revision to ensure the old revision can still serve traffic during cutover.

**Strategy: expand/contract**
1. Expand: add new columns/tables (backwards-compatible). Deploy new revision.
2. Contract: remove old columns/tables only after old revision is retired.

Never add NOT NULL columns without defaults in a single migration — this locks the table.
Use `ADD COLUMN ... DEFAULT <value>` followed by a separate `ALTER COLUMN ... SET NOT NULL`
after backfill.

---

## 7. Rollback

### Cloud Run revision rollback

```bash
# List revisions
gcloud run revisions list --service praxis-api --region us-central1

# Roll back to a previous revision (100% traffic)
gcloud run services update-traffic praxis-api \
  --region us-central1 \
  --to-revisions praxis-api-<prev-revision>=100
```

Rollback is independent per service. The API, realtime, and worker services can be
rolled back independently without affecting each other.

### Frontend rollback

Vercel deployments are rolled back independently via the Vercel dashboard or CLI.
The backend and frontend are versioned independently.

### Database rollback

There is no automated schema rollback. See `BACKEND_DISASTER_RECOVERY.md` for restore
procedures. Schema rollback requires a manual reverse migration script.
