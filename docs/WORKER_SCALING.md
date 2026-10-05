# PRAXIS Worker Scaling

## Architecture

Workers use ARQ (Async Redis Queue) backed by Redis. Each worker instance runs a continuous event loop, polling the ARQ queue and executing jobs concurrently up to `WORKER_MAX_JOBS`.

**Cloud Run Worker Pool** does NOT auto-scale. Instance count is fixed at `worker_instance_count` in Terraform. Scale by changing this variable and re-applying.

---

## Job types and their resource profiles

| Job Type | CPU | Memory | AI | DB | Typical Duration |
|---|---|---|---|---|---|
| resume_parse | Medium | Medium | Yes (embeddings + LLM) | Yes | 10–30s |
| jd_parse | Medium | Low | Yes (LLM) | Yes | 5–15s |
| embed_document | Medium | High (model load) | Yes (embeddings) | Yes | 2–10s |
| debrief_generate | High | Medium | Yes (LLM) | Yes | 15–60s |
| study_generate | Medium | Medium | Yes (LLM) | Yes | 10–30s |
| account_delete | Low | Low | No | Yes | 5–30s |
| export_generate | Low | Medium | No | Yes | 5–20s |

---

## Sizing rationale

**Staging:** `worker_instance_count = 1`
- Staging has low traffic
- 1 instance × 5 concurrent jobs = 5 simultaneous operations
- DB connections: 5 per instance = 5 total (within Supabase free tier budget)

**Production:** `worker_instance_count = 2`
- 2 instances × 10 concurrent jobs = 20 simultaneous operations
- DB connections: 10 per instance × 2 = 20 total
- AI throughput: 2 instances split the Groq/OpenAI rate limit
- Redis connections: 2 instances × 5 connections = 10 total

---

## Scaling triggers

Scale `worker_instance_count` when:

| Signal | Scale action |
|---|---|
| ARQ queue depth > 50 for > 5 min | +1 instance |
| ARQ queue depth > 200 | +2 instances |
| Job latency p95 > 2× SLA | +1 instance |
| CPU utilization < 30% for 30 min | -1 instance |
| Worker instance crashes repeatedly | Investigate before scaling up |

---

## Monitoring queue depth

ARQ does not provide a built-in Prometheus metric. Monitor via:

```python
# In worker health check or custom metric publisher:
import arq
from arq.connections import ArqRedis

async def queue_depth(redis: ArqRedis) -> int:
    info = await redis.info()
    # ARQ queue key: arq:queue
    return await redis.llen("arq:queue")
```

Publish this as `praxis_worker_queue_depth` Prometheus gauge (see `backend/app/api/metrics.py`).

---

## Graceful shutdown

ARQ workers handle `SIGTERM` by:
1. Stopping new job pickup
2. Waiting for in-flight jobs to complete (up to `job_timeout`)
3. Exiting cleanly

Cloud Run sends `SIGTERM` before killing the container. With `WORKER_JOB_TIMEOUT_S=300`, a worker will take up to 5 minutes to drain. Cloud Run's `--max-graceful-termination` should be set to ≥ 310s for worker deployments.

---

## Dead-letter handling

Jobs that fail `WORKER_MAX_TRIES=3` times are moved to `arq:failed_jobs` in Redis.

Inspect dead-letter queue:
```bash
# Via Redis CLI (from within VPC):
redis-cli LRANGE arq:failed_jobs 0 -1
```

Failed jobs do NOT retry automatically after entering dead-letter. Create an alert on `praxis_worker_jobs_total{status="dead_letter"}` (see alerting.tf).

---

## Idempotency

All worker jobs are idempotent: running the same job twice produces the same result. This is enforced by `backend/app/services/worker_idempotency.py`.

Idempotency key: `job_type:entity_id:version`.

---

*Last updated: 2026-10-05*
