# PRAXIS InterviewOS — Logging & Distributed Tracing Specification

**Document ID**: PROD-LOG-TRACE-001  
**Milestone**: Phase 5 — Production Engineering  
**Log Format**: Structured JSON (Google Cloud Logging Compatible)  
**Tracing Protocol**: OpenTelemetry / W3C TraceContext  
**Date**: 2026-11-01  
**Status**: Authoritative Logging & Tracing Specification  

---

## 1. Structured JSON Log Schema

All services emit logs formatted as single-line JSON to stdout/stderr. Google Cloud Logging automatically parses these records and indexes the embedded metadata:

```json
{
  "timestamp": "2026-11-01T18:08:00.123456Z",
  "severity": "INFO",
  "service": "praxis-api",
  "environment": "production",
  "message": "Processed interview session creation",
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "span_id": "00f067aa0ba902b7",
  "http": {
    "method": "POST",
    "route": "/sessions",
    "status_code": 201,
    "duration_ms": 142.5
  },
  "user": {
    "user_id": "usr_9b1deb4d3b7d4e8b",
    "tenant_id": "ten_default"
  }
}
```

---

## 2. Mandatory Sensitive Data Redaction Filter

To comply with privacy laws (GDPR, CCPA) and security policies, the logger utilizes an in-stream redaction filter ([`backend/app/core/logging.py`](file:///d:/work/interviewOS/backend/app/core/logging.py)) that intercepts and redacts sensitive keys:

### 2.1 Scrubbed Fields
- `Authorization`: Replaced with `[REDACTED]`
- `Cookie` / `Set-Cookie`: Replaced with `[REDACTED]`
- `password` / `secret`: Replaced with `[REDACTED]`
- `apiKey` / `token`: Stripped of key material
- `audio_data` / `audio_base64`: Suppressed from log output
- `resume_content` / `full_text`: Truncated or omitted

---

## 3. Distributed Trace Context Propagation

### 3.1 Trace Header Injection
FastAPI middleware intercepts inbound requests and checks for `traceparent`:
- If present, the trace context is adopted and continued.
- If missing, a new W3C-compliant 128-bit trace ID is generated.
- The trace ID is bound to the async request context via Python's `contextvars` and injected into response headers:
  ```http
  X-Request-ID: req_4bf92f3577b34da6
  traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01
  ```

### 3.2 Worker Queue Propagation
When the API enqueues an asynchronous task to Redis, `trace_id` is serialized into the ARQ task payload:
```python
await arq_pool.enqueue_job(
    "process_resume_document",
    resume_id=resume.id,
    _trace_id=context.get_trace_id()
)
```
Upon task dequeue, the worker restores the trace context, allowing unified root-cause tracing across API and background worker lifecycles.
