"""
Prometheus metrics endpoint — P7 of the Backend Sovereignty Spec.

Exposes /metrics in Prometheus text format for scraping by Cloud Monitoring,
Grafana, or any compatible collector.

Metrics defined here are application-level counters/histograms. Infrastructure
metrics (CPU, memory, Cloud Run instances) come from the platform directly.

All counters use the `praxis_` prefix per Prometheus naming conventions.
"""
from __future__ import annotations

from fastapi import APIRouter, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

router = APIRouter(tags=["observability"])

# ── Metrics definitions ───────────────────────────────────────────────────────
# These are module-level singletons shared across the process lifetime.

http_requests_total = Counter(
    "praxis_http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status_code"],
)

http_request_duration_seconds = Histogram(
    "praxis_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

websocket_connections_active = Gauge(
    "praxis_websocket_connections_active",
    "Currently active realtime WebSocket connections",
)

ai_calls_total = Counter(
    "praxis_ai_calls_total",
    "Total AI provider calls",
    ["provider", "task", "method", "status"],
)

ai_call_duration_seconds = Histogram(
    "praxis_ai_call_duration_seconds",
    "AI provider call duration in seconds",
    ["provider", "task"],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
)

ai_tokens_total = Counter(
    "praxis_ai_tokens_total",
    "Total AI tokens consumed",
    ["provider", "direction"],  # direction: input | output
)

ai_cost_usd_total = Counter(
    "praxis_ai_cost_usd_total",
    "Total estimated AI cost in USD",
    ["provider"],
)

ai_budget_exceeded_total = Counter(
    "praxis_ai_budget_exceeded_total",
    "Number of times AI budget was exceeded",
    ["scope"],  # scope: session | daily | global
)

ai_output_safety_violations_total = Counter(
    "praxis_ai_output_safety_violations_total",
    "AI output safety violations detected",
    ["code"],
)

worker_jobs_total = Counter(
    "praxis_worker_jobs_total",
    "Total background worker jobs",
    ["job_type", "status"],  # status: success | failure | dead_letter
)

worker_job_duration_seconds = Histogram(
    "praxis_worker_job_duration_seconds",
    "Worker job duration in seconds",
    ["job_type"],
    buckets=(0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0),
)

resume_processing_total = Counter(
    "praxis_resume_processing_total",
    "Total resume processing attempts",
    ["status"],  # status: success | parse_failure | embed_failure
)

interview_sessions_total = Counter(
    "praxis_interview_sessions_total",
    "Total interview sessions created",
    ["mode"],  # mode: technical | behavioral | system_design | coding
)

rls_violations_total = Counter(
    "praxis_rls_violations_total",
    "Authorization / RLS violations detected at application layer",
)

rate_limit_hits_total = Counter(
    "praxis_rate_limit_hits_total",
    "Total rate limit rejections",
    ["endpoint"],
)


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.get(
    "/metrics",
    summary="Prometheus metrics",
    description="Exposes application metrics in Prometheus text exposition format. "
                "Restrict access to internal scraping network in production.",
    response_class=Response,
    include_in_schema=False,  # exclude from public OpenAPI — internal endpoint
)
async def metrics() -> Response:
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
