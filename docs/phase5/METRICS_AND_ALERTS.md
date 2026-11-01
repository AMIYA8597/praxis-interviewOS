# PRAXIS InterviewOS — Metrics & Alerting Runbook

**Document ID**: PROD-METRICS-001  
**Milestone**: Phase 5 — Production Engineering  
**Scrape Format**: OpenMetrics / Prometheus 2.0  
**Alerting Engine**: Google Cloud Monitoring (`infra/gcp/alerting.tf`)  
**Date**: 2026-11-01  
**Status**: Authoritative Metrics & Alerting Runbook  

---

## 1. Key Production Metrics Inventory

### 1.1 Core API & Database Metrics
| Metric Name | Type | Labels | Operational Meaning |
| :--- | :--- | :--- | :--- |
| `http_requests_total` | Counter | `method`, `handler`, `status` | Total HTTP requests handled |
| `http_request_duration_seconds` | Histogram | `handler`, `le` | Latency distribution (p50, p95, p99) |
| `db_pool_active_connections` | Gauge | `pool_id` | Number of connections currently checked out |
| `db_pool_overflow_connections`| Gauge | `pool_id` | Number of burst connections in use |
| `db_pool_waiting_requests` | Gauge | `pool_id` | Requests blocked waiting for connection |

### 1.2 Realtime Audio & WebSocket Metrics
| Metric Name | Type | Labels | Operational Meaning |
| :--- | :--- | :--- | :--- |
| `ws_active_connections` | Gauge | `service` | Total active candidate WebSocket sessions |
| `ws_audio_frames_total` | Counter | `format`, `status` | Count of 18-byte audio frames processed |
| `ws_dropped_frames_total` | Counter | `reason` | Audio frames dropped due to buffer overflow |
| `stt_transcription_duration_seconds`| Histogram | `model`, `device` | Latency of faster-whisper transcription |
| `coaching_metrics_duration_seconds`| Histogram | `cadence` | Latency of fast coaching engine (< 80ms) |

### 1.3 AI Gateway & Worker Metrics
| Metric Name | Type | Labels | Operational Meaning |
| :--- | :--- | :--- | :--- |
| `ai_requests_total` | Counter | `provider`, `model`, `status` | Outbound LLM requests |
| `ai_tokens_consumed_total` | Counter | `provider`, `type` | Input and output token counts |
| `ai_circuit_breaker_state` | Gauge | `provider` | 0 = CLOSED, 1 = HALF-OPEN, 2 = OPEN |
| `ai_budget_exceeded_total` | Counter | `limit_type` | Count of rejected requests exceeding quota |
| `arq_queue_depth` | Gauge | `queue` | Number of pending background tasks |
| `arq_job_failures_total` | Counter | `job_name` | Tasks failing after maximum retries |

---

## 2. Actionable Alert Policies & Escalation Paths

As provisioned in [`infra/gcp/alerting.tf`](file:///d:/work/interviewOS/infra/gcp/alerting.tf):

| Alert Name | Severity | Condition | Impact | Escalation & Triage Runbook |
| :--- | :---: | :--- | :--- | :--- |
| **`api_5xx`** | **P1 (Critical)** | 5xx rate $> 1.0\%$ for 5 min | Service degraded | Check Cloud Logging for unhandled exceptions. If deploy-related, initiate immediate revision rollback via [`ROLLBACK_RUNBOOK.md`](file:///d:/work/interviewOS/docs/phase5/ROLLBACK_RUNBOOK.md). |
| **`api_latency`** | **P2 (High)** | p95 latency $> 3,000\text{ ms}$ for 5 min | Sluggish UX | Inspect `db_pool_waiting_requests` and external AI provider latencies. Scale API instances or trip provider circuit breaker. |
| **`realtime_5xx`** | **P1 (Critical)** | WS errors $> 5.0\%$ for 5 min | Practice rooms failing | Inspect CPU usage on `praxis-realtime`. Verify faster-whisper model memory footprint. |
| **`container_crash`**| **P1 (Critical)** | Crash count $> 0$ | Container restart loop | Inspect Cloud Run crash logs. Verify memory limits (OOM kill) and environment configuration. |
| **`redis_unavailable`**| **P1 (Critical)**| Rejected connections $> 10$ in 2 min | Cache/Worker outage | Check Memorystore Redis memory saturation. Verify VPC connector bandwidth. |
| **`budget_exceeded`**| **P3 (Medium)** | Event count $> 0$ in 5 min | Cost ceiling reached | Alert billing team. Verify if user is legitimate high-volume candidate or potential abuse scenario. |
