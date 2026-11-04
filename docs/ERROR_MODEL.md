# PRAXIS InterviewOS — Error Model & Failure Handling Specification

**Document Version:** 1.0.0  
**Status:** Certified & Active  
**Scope:** REST API errors, WebSocket error envelopes, AI Gateway failure degradation, and client error handling guidelines.

---

## 1. Unified Error Architecture

PRAXIS enforces an explicit, zero-fabrication error architecture. When a service, provider, or database operation fails:
- **Never silently substitute fake values:** No fake scores, default WPM, or synthetic evaluations are ever returned.
- **Explicit Error / Degraded States:** The failure is categorized, given a permanent error code, and reported explicitly.
- **Traceability:** Every error envelope contains a unique `request_id` or session sequence number matching the server logs.

---

## 2. Standard REST Error Schema

All REST API error responses (HTTP status $\ge 400$) return the uniform error model:

```json
{
  "detail": "Descriptive message explaining the reason for rejection",
  "error_code": "RESOURCE_NOT_FOUND",
  "request_id": "8b23f0a1-4321-4def-9876-ab0123456789",
  "timestamp": "2026-11-04T14:45:00.000000Z",
  "context": {
    "resource_type": "practice_sessions",
    "resource_id": "f2b48ce0-1668-42a4-aea5-0aca2954901f"
  }
}
```

### Field Definitions
- `detail` (`str`): Clear, human-readable description safe for logging.
- `error_code` (`str`): Machine-readable uppercase snake_case string used by client UI for localized rendering.
- `request_id` (`str`): UUIDv4 correlation identifier linking client requests to backend OpenTelemetry traces and logs.
- `timestamp` (`str`): ISO 8601 UTC timestamp of error generation.
- `context` (`dict`, optional): Diagnostic metadata (e.g. invalid parameter names, field boundaries, or retry parameters).

---

## 3. Canonical Error Code Catalog

### 3.1 Authentication & Security (`AUTH_*`, `SEC_*`)
| Error Code | HTTP Status | Meaning & Client Action |
|---|---|---|
| `AUTH_TOKEN_MISSING` | `401` | Missing `Authorization` header. Client must prompt user to log in. |
| `AUTH_TOKEN_EXPIRED` | `401` | JWT expired. Client must invoke refresh token flow or re-authenticate. |
| `AUTH_TOKEN_INVALID` | `401` | Signature or claims verification failed. Client must clear stored credentials. |
| `PERMISSION_DENIED` | `403` | User does not own the requested resource or lacks role. Deny action in UI. |
| `ADMIN_REQUIRED` | `403` | Operation requires verified system administrator privileges. |
| `SSRF_ATTEMPT_BLOCKED`| `400` | User provided private/internal subnet URL. Flag input as dangerous in UI. |
| `RATE_LIMIT_EXCEEDED` | `429` | Request burst limit exceeded. Client must honor `Retry-After` header. |

### 3.2 Resource & Validation (`RES_*`, `VAL_*`)
| Error Code | HTTP Status | Meaning & Client Action |
|---|---|---|
| `RESOURCE_NOT_FOUND` | `404` | Entity does not exist or caller does not own it. Display 404 page. |
| `VALIDATION_ERROR` | `422` | Request body failed Pydantic schema validation. Highlight offending field in UI. |
| `UNSUPPORTED_MEDIA_TYPE`| `415` | Uploaded resume is not PDF, DOCX, or plain text. Display format restriction banner. |
| `FILE_TOO_LARGE` | `413` | Upload exceeds 10 MB payload limit. Advise user to compress file. |
| `STATE_CONFLICT` | `409` | Resource state prohibits operation (e.g. updating an ended session). |

### 3.3 AI Gateway & Provider Degradation (`AI_*`)
| Error Code | HTTP Status | Degraded Behavior |
|---|---|---|
| `AI_PROVIDER_NOT_CONFIGURED` | `503` | Neither Groq nor Gemini key configured for zero-spend mode. System logs warning; exposes unconfigured status. |
| `AI_PROVIDER_AUTH_ERROR` | `503` | Third-party provider returned 401/403 (invalid key or revoked key). Tripped circuit breaker. |
| `AI_PROVIDER_RATE_LIMITED` | `503` | Upstream provider 429. Automatically attempts configured fallback candidate. |
| `AI_ALL_PROVIDERS_UNAVAILABLE`| `503` | Fallback chain exhausted. Realtime session transitions to `DSP_ONLY` mode. |
| `AI_BUDGET_EXCEEDED` | `429` | Session, daily, or user dollar budget exceeded. Client shows quota limit warning. |
| `AI_SAFETY_VIOLATION` | `200 / 400` | Model output or input flagged for prompt injection or system leakage. Filtered safely. |

### 3.4 Code Sandbox Engine (`SANDBOX_*`)
| Error Code | HTTP Status | Meaning & Client Action |
|---|---|---|
| `SANDBOX_TIMEOUT` | `200` | Candidate code exceeded 2.0s execution time limit (e.g. infinite loop). Mark test failed. |
| `SANDBOX_MEMORY_LIMIT`| `200` | Candidate code exceeded 128 MB heap allocation. Mark OOM error. |
| `SANDBOX_NETWORK_DENIED`| `200` | Candidate code attempted network socket connection. Mark security violation. |
| `SANDBOX_UNAVAILABLE` | `503` | Sandbox microservice container unreachable. Inform candidate code execution is temporarily paused. |

---

## 4. Realtime WebSocket Degraded Mode Protocol

When an external LLM provider experiences an outage during an active live interview, the Realtime agent **does not disconnect or terminate the candidate's interview session**.

Instead, the agent executes the following degradation sequence:
1. **Emit Alert:** Realtime agent broadcasts `session.degraded` envelope to client:
   ```json
   {
     "version": "1",
     "type": "session.degraded",
     "session_id": "f2b48ce0-1668-42a4-aea5-0aca2954901f",
     "sequence": 85,
     "timestamp": "2026-11-04T14:46:12Z",
     "payload": {
       "mode": "DSP_ONLY",
       "reason": "AI_ALL_PROVIDERS_UNAVAILABLE",
       "message": "AI reasoning is temporarily unavailable. Live speech coaching (WPM, pause detection, filler words) remains fully operational."
     }
   }
   ```
2. **DSP Continuity:** Low-latency speech processing continues unaffected:
   - Voice Activity Detection (Silero VAD) continues tracking candidate speech.
   - Speech-to-Text (Faster-Whisper) continues recording transcripts locally.
   - Coaching Accumulator emits `coaching.metrics` every 1 second (WPM, filler word count, pauses).
3. **Recovery:** Once the provider restores connectivity or the circuit breaker resets, the session transparently re-engages LLM scoring and turn generation.
