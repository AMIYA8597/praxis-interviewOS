# PRAXIS InterviewOS — Health Checks & Service Lifecycle

**Document ID**: PROD-HEALTH-001  
**Milestone**: Phase 5 — Production Engineering  
**Endpoints**: `/health` (Liveness) & `/health/ready` (Readiness)  
**Date**: 2026-11-01  
**Status**: Authoritative Service Lifecycle Specification  

---

## 1. Healthcheck Architecture & Probing Strategy

To prevent cascading restarts caused by temporary third-party outages, PRAXIS decouples internal process liveness from external service readiness:

```mermaid
flowchart TD
    subgraph Probes
        StartProbe[Startup Probe\nHas model loaded in memory?\nInitial delay: 15s]
        LiveProbe[Liveness Probe\nIs web process responding?\nPeriod: 30s]
        ReadyProbe[Readiness Probe\nAre DB and Redis reachable?\nPeriod: 15s]
    end

    subgraph Service Health Actions
        StartProbe -- Failed 3x --> Restart1[Restart Container]
        LiveProbe -- Failed 3x --> Restart2[Restart Container]
        ReadyProbe -- Failed --> Degrade[Remove from Load Balancer\nDo NOT restart container]
    end
```

### 1.1 Endpoint Contracts
| Endpoint | Method | Checks Performed | Failure Action |
| :--- | :--- | :--- | :--- |
| **`/health` (Liveness)** | `GET` | Event loop responsiveness, memory ceiling | If 3 consecutive checks fail, Cloud Run restarts instance |
| **`/health/ready` (Readiness)** | `GET` | Database pool pre-ping, Redis `PING` | If check fails, instance is removed from traffic routing |

> [!NOTE]
> External LLM providers (e.g. OpenRouter, DeepSeek) are **never** queried in liveness probes. An external provider outage must never cause local API containers to crash or restart in a loop.

---

## 2. Container Lifecycle & Graceful Shutdown

When Google Cloud Run scales down or rolls out a new revision, it sends a `SIGTERM` signal to the container:

```mermaid
sequenceDiagram
    autonumber
    participant GCP as Cloud Run Supervisor
    participant App as FastAPI / Uvicorn Server
    participant WS as Active WebSocket Connections
    participant DB as Connection Pool
    participant Worker as ARQ Tasks

    GCP->>App: Sends SIGTERM signal (Grace period: 30s)
    App->>App: Stop accepting new HTTP requests
    App->>WS: Broadcast session_terminating notice
    WS->>WS: Flush remaining audio chunks to Redis
    App->>Worker: Complete current task iteration (do not dequeue new)
    App->>DB: Close idle database connections
    App->>GCP: Process exits cleanly (Exit code 0)
```

### 2.1 Graceful Shutdown Parameters
- **Uvicorn Grace Timeout**: `--timeout-graceful-shutdown 30` allows 30 seconds for pending HTTP requests and audio frames to drain before forced termination (`SIGKILL`).
- **ARQ Worker Draining**: The ARQ worker intercepts SIGTERM and completes its current in-flight task while refusing to pull new jobs from the queue.
- **WebSocket Closure Code**: Active interview sessions receive close code `1001` (Going Away), prompting the desktop client to attempt automatic reconnection to another active container instance.
