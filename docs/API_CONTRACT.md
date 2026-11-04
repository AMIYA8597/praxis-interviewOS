# PRAXIS InterviewOS — Master API Contract & Specification

**Specification Version:** 1.0.0  
**Base URL:** `https://api.praxis.internal/api/v1` (Production) / `http://localhost:8000/api/v1` (Local)  
**OpenAPI Specification:** Available at `/openapi.json` and mirrored in `docs/openapi.json`  

---

## 1. Authentication & Security Contract

All endpoints under `/api/v1/*` (except health checks) require an authenticated Bearer token in the standard HTTP `Authorization` header:

```http
Authorization: Bearer <jwt_access_token>
```

### Token Verification Rules
- Supported Algorithms: `HS256` (symmetric local dev) and `RS256` (asymmetric Supabase Auth).
- Public Key Verification: For RS256, public keys are retrieved from the configured JWKS URL (`SUPABASE_JWKS_URL`) and cached in Redis with a 24-hour TTL (`JWKS_CACHE_TTL_S`).
- Mandatory Claims:
  - `sub`: Authenticated user UUID (maps to `profiles.id`).
  - `exp`: Token expiry epoch timestamp. Must not be expired (leeway: 60s).
  - `aud`: Audience claim. Must match `JWT_AUDIENCE` (`authenticated`).
  - `iss`: Issuer URL. Must match `SUPABASE_URL` if configured.
- Unauthorized Response: Missing, expired, or forged tokens receive HTTP 401:
  ```json
  {
    "detail": "Invalid or expired authorization token",
    "error_code": "AUTH_TOKEN_INVALID",
    "request_id": "c6a2d981-817e-46bb-8484-df253a6e3820"
  }
  ```

---

## 2. Global Request & Response Conventions

### 2.1 Request Correlation & Tracing
Every incoming request is tagged by `RequestIdMiddleware`.
- Clients may optionally send a tracing ID: `X-Request-ID: <uuid-v4>`.
- If omitted, the server generates a unique UUIDv4.
- The server echoes the header on all responses:
  ```http
  X-Request-ID: 7a82c40d-2b99-4c07-93aa-bf482e36127f
  ```
- All log lines, audit entries, and database transaction traces link to this request ID.

### 2.2 Standard Error Response Schema
All 4xx and 5xx errors strictly follow a uniform JSON schema (`backend/app/schemas/error.py`):

```json
{
  "detail": "Human-readable description of the error",
  "error_code": "RESOURCE_NOT_FOUND",
  "request_id": "7a82c40d-2b99-4c07-93aa-bf482e36127f",
  "timestamp": "2026-11-04T14:40:00.123456Z",
  "context": {
    "field": "session_id",
    "rejected_value": "invalid-uuid"
  }
}
```

### 2.3 Common HTTP Status Codes
| HTTP Status | Error Code | Meaning |
|---|---|---|
| `200 OK` | — | Request succeeded; response contains payload. |
| `201 Created` | — | Entity successfully created; response contains new resource. |
| `202 Accepted` | — | Long-running asynchronous job queued (e.g. resume parsing, export). |
| `204 No Content` | — | Entity deleted or action confirmed with empty body. |
| `400 Bad Request` | `VALIDATION_ERROR` | Schema validation error, malformed UUID, or bad input. |
| `401 Unauthorized` | `AUTH_REQUIRED` | Missing, malformed, or expired Bearer token. |
| `403 Forbidden` | `PERMISSION_DENIED` | Caller does not own the requested resource or lacks Admin privileges. |
| `404 Not Found` | `RESOURCE_NOT_FOUND` | Resource does not exist or has been soft-deleted. |
| `409 Conflict` | `STATE_CONFLICT` | Resource in incompatible state (e.g. session already ended). |
| `422 Unprocessable`| `SCHEMA_ERROR` | Pydantic validation error with field-level details. |
| `429 Too Many Req` | `RATE_LIMIT_EXCEEDED`| Rate limit exceeded; response includes `Retry-After: <seconds>`. |
| `503 Unavailable` | `SERVICE_DEGRADED` | Database, Redis, or external AI provider temporarily unreachable. |

---

## 3. Pagination, Filtering & Sorting

List endpoints (`/api/v1/resumes`, `/api/v1/jobs`, `/api/v1/sessions`, `/api/v1/study/items`) use cursor-based pagination to guarantee stable results under concurrent writes:

### Query Parameters
- `limit` (integer, optional, default: 20, max: 100): Number of items per page.
- `cursor` (string, optional): Base64 opaque cursor returned in `next_cursor`.
- `filter` (string, optional): Domain filter (e.g. `?status=completed&interview_type=system_design`).
- `order_by` (string, optional, default: `-created_at`): Sorting column and direction (`-` for descending).

### Paginated Response Wrapper
```json
{
  "items": [
    { "id": "uuid-1", "created_at": "2026-11-04T12:00:00Z" },
    { "id": "uuid-2", "created_at": "2026-11-04T11:30:00Z" }
  ],
  "next_cursor": "eyJjcmVhdGVkX2F0IjogIjIwMjYtMTEtMDRUMTE6MzA6MDBaIiwgImlkIjogInV1aWQtMiJ9",
  "has_more": true,
  "total_count": 142
}
```

---

## 4. Rate Limiting Contract

Rate limits are enforced by `RateLimitMiddleware` using a Redis token bucket algorithm per authenticated caller IP and user ID:

| Tier / Route Category | Window | Burst Limit | Refill Rate | Scope |
|---|---|---|---|---|
| **Standard REST API** | 60 seconds | 120 requests | 2 req/sec | Per User ID |
| **Resume & File Uploads** | 60 seconds | 5 uploads | 1 per 12s | Per Candidate ID |
| **Code Sandbox Execution** | 60 seconds | 10 executions| 1 per 6s | Per Session ID |
| **GDPR Data Exports** | 24 hours | 1 export | 1 per day | Per Candidate ID |
| **Realtime WebSocket Connect**| 60 seconds | 10 connections| 1 per 6s | Per Candidate ID |

When exceeded, the server returns `429 Too Many Requests` with HTTP header:
```http
Retry-After: 45
```

---

## 5. Primary API Endpoints Contract

### 5.1 Candidates Profile (`/api/v1/candidates/me`)
- `GET`: Returns the candidate profile for the calling user.
  - Response:
    ```json
    {
      "id": "70733de4-b0e3-46f6-b9c5-0bf25dde6f75",
      "profile_id": "00000000-0000-0000-0000-000000000000",
      "full_name": "Alex Morgan",
      "target_role": "Staff Infrastructure Engineer",
      "target_seniority": "Staff",
      "skills": ["Distributed Systems", "Kafka", "PostgreSQL", "Go"],
      "created_at": "2026-11-04T10:00:00Z"
    }
    ```
- `PATCH`: Updates candidate attributes. Request body accepts any subset of `{full_name, target_role, target_seniority, skills}`.

### 5.2 Resumes & Evidence (`/api/v1/resumes`)
- `POST`: Uploads resume file (Multipart form, key: `file`). Supported types: `application/pdf`, `application/vnd.openxmlformats-officedocument.wordprocessingml.document`, `text/plain`. Max size: 10 MB.
  - Response (202 Accepted):
    ```json
    {
      "document_id": "e45a1e89-6192-4919-8692-23c34a2e5192",
      "resume_id": "b18f8e02-8611-4043-a621-c49c7198bb12",
      "status": "parsing",
      "message": "Resume uploaded successfully; background parsing queued."
    }
    ```
- `GET /api/v1/resumes/{id}/facts`: Returns list of extracted claims with verification status (`is_confirmed`, `is_rejected`).

### 5.3 Practice Sessions (`/api/v1/sessions`)
- `POST`: Creates a practice session.
  - Request:
    ```json
    {
      "job_id": "d1c9ef0d-9b51-41b9-a9a7-9e0c52eb9b8a",
      "interview_type": "technical",
      "mode": "audio",
      "difficulty": 3,
      "interviewer_personality": "socratic"
    }
    ```
  - Response (201 Created):
    ```json
    {
      "id": "f2b48ce0-1668-42a4-aea5-0aca2954901f",
      "candidate_id": "70733de4-b0e3-46f6-b9c5-0bf25dde6f75",
      "job_id": "d1c9ef0d-9b51-41b9-a9a7-9e0c52eb9b8a",
      "status": "created",
      "websocket_url": "wss://api.praxis.internal/ws/sessions/f2b48ce0-1668-42a4-aea5-0aca2954901f",
      "created_at": "2026-11-04T14:00:00Z"
    }
    ```
- `GET /api/v1/sessions/{id}/debrief`: Returns final debrief with overall score, metrics, strengths, weaknesses, and study recommendations.

### 5.4 Study Cards & SM-2 Spaced Repetition (`/api/v1/study/*`)
- `GET /api/v1/study/items/due`: Returns cards due for review today.
- `POST /api/v1/study/items/{item_id}/review`: Records recall score:
  - Request: `{"quality": 4}` (0 = total blackout, 5 = perfect recall).
  - Response: Updated SM-2 state with `interval_days`, `ease_factor`, and `next_due_date`.

---

## 6. API Versioning & Deprecation Policy

- All breaking changes increment the URI prefix: `/api/v1` -> `/api/v2`.
- Non-breaking changes (adding optional fields, adding new endpoints) are introduced without changing the major version.
- Deprecated endpoints carry the standard HTTP headers:
  ```http
  Deprecation: @1798761600
  Sunset: Wed, 01 Jul 2027 00:00:00 GMT
  Link: </api/v2/resumes>; rel="successor-version"
  ```
