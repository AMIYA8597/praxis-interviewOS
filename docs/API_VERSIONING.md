# PRAXIS API Versioning & Contract Guidelines

## 1. URI Namespace & Versioning Scheme

All REST API endpoints are mounted under the explicit version prefix `/api/v1`:
```
https://api.praxis.domain/api/v1/...
```

### Exceptions:
- **Liveness Probes**: `/health/live`, `/health/ready`, `/health/startup` are mounted at root and mirrored at `/api/v1/health/*`.
- **Metrics**: `/metrics` (internal Prometheus exposition) is mounted exclusively at root `/metrics` and excluded from public OpenAPI schemas.
- **Realtime WebSocket**: Mounted at `/ws/sessions/{session_id}`.

---

## 2. Uniform Error Envelope

All error responses (4xx and 5xx) strictly follow the standardized PRAXIS error envelope:

```json
{
  "code": "VALIDATION_ERROR",
  "message": "Invalid file upload format. Only PDF, DOCX, and TXT are accepted.",
  "request_id": "7f09312b-3e54-463e-a10c-9d6e3f4c2b9a",
  "retryable": false
}
```

### Standard Error Codes:
| HTTP Status | Error Code | Description | Retryable |
|---|---|---|:---:|
| 400 | `BAD_REQUEST` | Malformed request body or schema validation failure | No |
| 401 | `UNAUTHORIZED` | Missing, expired, or cryptographically invalid access token | No |
| 403 | `FORBIDDEN` | Caller lacks ownership of the requested resource or admin role | No |
| 404 | `NOT_FOUND` | Target entity does not exist or belongs to another candidate | No |
| 409 | `CONFLICT` | Concurrent state transition conflict (e.g. session already completed) | No |
| 413 | `PAYLOAD_TOO_LARGE` | Upload exceeds the 10 MB maximum allowed file size | No |
| 422 | `UNPROCESSABLE_ENTITY` | Semantic validation error (e.g. invalid rating range) | No |
| 429 | `RATE_LIMITED` | Request rate limit exceeded for this endpoint | Yes |
| 500 | `INTERNAL_ERROR` | Unhandled server exception (redacted in response; logged with stack trace) | No |
| 503 | `SERVICE_UNAVAILABLE` | Database, Redis, or essential upstream dependency unreachable | Yes |

---

## 3. Cursor-Based Pagination

All collection endpoints support deterministic, cursor-based pagination to avoid offset scan penalties:

```
GET /api/v1/resumes?limit=20&cursor=eyJpZCI6IC...
```

### Response Format:
```json
{
  "items": [...],
  "next_cursor": "eyJpZCI6IC..."
}
```
If `next_cursor` is `null`, the final page of records has been reached.

---

## 4. Idempotency on Write Operations

Critical mutating operations (such as session creation and debrief scheduling) accept an optional `Idempotency-Key` HTTP header:
```
Idempotency-Key: 9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d
```
1. Keys are persisted in the `idempotency_keys` table with an expiration TTL of 24 hours.
2. Concurrent duplicate requests return the cached original response or wait for ongoing execution, preventing duplicate records.

---

## 5. Deprecation & Sunset Policy

When an API endpoint or field is superseded:
1. **Notice Window**: Minimum 90 days before sunset in production.
2. **Standard Headers**: Responses from deprecated routes include:
   - `Deprecation: @<timestamp>` (RFC 8594)
   - `Sunset: <date>` (RFC 8594)
   - `Link: </api/v2/...>; rel="successor-version"`
3. Breaking schema changes are never introduced in `/api/v1`; breaking changes require a new major version prefix (`/api/v2`).
