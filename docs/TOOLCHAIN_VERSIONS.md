# PRAXIS Toolchain Versions

Recorded: 2026-10-05. Re-run `scripts/record_toolchain_versions.sh` after upgrades.

## Detected (this machine)

| Tool | Version | Required | Notes |
|---|---|---|---|
| gcloud CLI | 587.0.0 | ≥ 450 | `gcloud --version` |
| Docker | 29.7.2 | ≥ 24.0 | `docker --version` |
| Terraform | 1.16.4 | ≥ 1.9.0 | `terraform --version` |
| Python | 3.13.7 | 3.11.x production | Local dev uses 3.13; Docker images use 3.11.11 |
| Node.js | 24.18.0 | ≥ 20 | `node --version` |
| pnpm | 10.30.3 | ≥ 9.0 | `pnpm --version` |
| Supabase CLI | NOT INSTALLED | ≥ 1.0 | `winget install Supabase.CLI` |
| git | 2.51.0 | ≥ 2.30 | `git --version` |

## Docker image base versions

| Image | Base | Python |
|---|---|---|
| praxis-api | python:3.11.11-slim | 3.11.11 |
| praxis-realtime | python:3.11.11-slim | 3.11.11 |
| praxis-worker | python:3.11.11-slim | 3.11.11 |

## Key Python dependencies (pinned in requirements-lock.txt)

| Package | Pinned Version | Purpose |
|---|---|---|
| fastapi | 0.115.x | HTTP framework |
| sqlalchemy | 2.0.x | ORM (async) |
| asyncpg | 0.30.x | Postgres async driver |
| arq | 0.26.x | ARQ task queue |
| redis | 5.x | Redis client |
| pydantic | 2.x | Validation |
| prometheus_client | 0.25.0 | Metrics |
| faster-whisper | 1.1.0 | STT (realtime) |
| silero-vad | 5.1.2 | VAD (realtime) |
| torch | 2.5.1+cpu | ML (realtime/worker) |
| sentence-transformers | 3.3.1 | Embeddings (worker) |

## Cloud Build machine type

`E2_HIGHCPU_8` — 8 vCPU, required for parallel Docker builds.

## GCP provider pinned in Terraform

```hcl
google      = "~> 6.14"
google-beta = "~> 6.14"
```

## Notes

- Production Docker images use Python 3.11.11 (not the local 3.13.7) for stability.
- The `requirements-lock.txt` pins all transitive dependencies. CI installs from this file.
- Supabase CLI is required for migration deployment; install before running `supabase db push`.
