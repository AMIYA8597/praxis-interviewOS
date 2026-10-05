# PRAXIS Backend API Contract

**Version**: v1  
**Base URL**: `https://<host>/api/v1`  
**Auth**: All endpoints except health checks require `Authorization: Bearer <supabase-jwt>` (RS256).  
**Request-ID**: Pass `X-Request-ID` header; echoed in responses for tracing.

---

## Conventions

| Convention | Value |
|---|---|
| Content-Type | `application/json` |
| Pagination | `?page=1&page_size=20` → `{items, total, page, page_size}` |
| Async tasks | `202 Accepted` + `{task_id}` queued in ARQ worker pool |
| Errors | `{detail: string}` — RFC 7807 style |
| IDs | UUID strings |
| Timestamps | ISO 8601 UTC (`2026-10-05T12:00:00Z`) |

---

## Health

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/health/live` | None | Liveness — returns `{status: "ok"}` |
| GET | `/api/v1/health/ready` | None | Readiness — checks DB + Redis connectivity |
| GET | `/api/v1/health/providers` | None | AI provider reachability status |

---

## Observability / Metrics

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/metrics` | None (infra-only) | Prometheus metrics (scrape target) |
| GET | `/api/v1/observability/provider-health` | JWT | AI gateway provider circuit-breaker states |
| GET | `/api/v1/observability/cost-latency` | JWT | Per-provider cost and latency telemetry |
| GET | `/api/v1/observability/system` | JWT | System-level resource usage |

---

## Auth

Signup, login, and token refresh are handled by **Supabase Auth** (client-side SDK). The backend exposes only session management.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/auth/logout` | JWT | Invalidate session token |
| GET | `/api/v1/auth/me` | JWT | Current user profile |
| DELETE | `/api/v1/auth/account` | JWT | Queue account deletion (GDPR) — `202 Accepted` |

---

## Candidates

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/candidates/me` | JWT | Fetch candidate profile |
| PATCH | `/api/v1/candidates/me` | JWT | Update candidate profile fields |
| PUT | `/api/v1/candidates/me/target` | JWT | Set target role / company / level |

---

## Resumes

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/resumes` | JWT | Upload resume file (multipart) — triggers async parse |
| POST | `/api/v1/resumes/text` | JWT | Submit resume as plain text — triggers async parse |
| GET | `/api/v1/resumes` | JWT | List resumes (paginated) |
| GET | `/api/v1/resumes/{id}` | JWT | Resume parse status + metadata |
| GET | `/api/v1/resumes/{id}/facts` | JWT | Extracted resume facts (skills, claims) |
| POST | `/api/v1/resumes/{id}/facts/{fact_id}/confirm` | JWT | Confirm an extracted fact |
| POST | `/api/v1/resumes/{id}/facts/{fact_id}/reject` | JWT | Reject an extracted fact |
| PATCH | `/api/v1/resumes/{id}/facts/{fact_id}` | JWT | Edit a resume fact |

---

## Jobs (JD ingestion)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/jobs` | JWT | Submit job description — `202 Accepted` + `{task_id}` |
| GET | `/api/v1/jobs` | JWT | List parsed JDs (paginated) |
| GET | `/api/v1/jobs/{id}` | JWT | JD detail: requirements, skills, weights |
| DELETE | `/api/v1/jobs/{id}` | JWT | Delete a JD |

---

## Applications (job-tracking)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/applications` | JWT | List applications (paginated) |
| POST | `/api/v1/applications` | JWT | Create application record |
| GET | `/api/v1/applications/{app_id}` | JWT | Application detail |
| PATCH | `/api/v1/applications/{app_id}` | JWT | Update status, notes |
| DELETE | `/api/v1/applications/{app_id}` | JWT | Delete application |

---

## Projects (portfolio)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/projects` | JWT | Create project |
| GET | `/api/v1/projects` | JWT | List projects (paginated) |
| GET | `/api/v1/projects/{id}` | JWT | Project detail |
| PATCH | `/api/v1/projects/{id}` | JWT | Update project |
| DELETE | `/api/v1/projects/{id}` | JWT | Delete project |

---

## Interview Sessions

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/sessions` | JWT | Create interview session — `201 Created` |
| GET | `/api/v1/sessions` | JWT | List sessions (paginated) |
| GET | `/api/v1/sessions/{id}` | JWT | Session detail + current state |
| GET | `/api/v1/sessions/{id}/turns` | JWT | All turns in a session |
| GET | `/api/v1/sessions/{id}/debrief` | JWT | Post-session debrief + scores |
| POST | `/api/v1/sessions/{id}/end` | JWT | End session — `202 Accepted` triggers scoring |

### Realtime (WebSocket)

Realtime interview conduct happens over WebSocket via the **realtime-agent** service (separate Cloud Run service). The REST API manages session lifecycle; audio + turn-taking run over WebSocket at `wss://<realtime-host>/ws/{session_id}`.

---

## Interview Engines

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/interviewer/personalities` | JWT | List available interviewer personas |
| POST | `/api/v1/interviewer/personality` | JWT | Set personality for a session |
| GET | `/api/v1/sessions/{id}/system-design/state` | JWT | System design session state (current phase, etc.) |
| POST | `/api/v1/sessions/{id}/system-design/advance` | JWT | Advance to next system design phase |
| POST | `/api/v1/sessions/{id}/diagram/analyze` | JWT | Analyze a system design diagram image |
| POST | `/api/v1/sessions/{id}/code/run` | JWT | Execute code against test cases |
| GET | `/api/v1/sessions/{id}/code/state` | JWT | Current coding session state |
| POST | `/api/v1/behavioral/star-analysis` | JWT | STAR component analysis for a response |
| POST | `/api/v1/behavioral/resume-probe` | JWT | Resume-grounded follow-up generation |

---

## Questions (Question Bank)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/questions/domains` | JWT | List interview domains |
| GET | `/api/v1/questions` | JWT | List questions (filterable by domain, difficulty) |
| GET | `/api/v1/questions/{question_id}` | JWT | Question detail |
| POST | `/api/v1/questions` | JWT | Create custom question |

---

## Study (Spaced Repetition)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/study/items` | JWT | Study items (paginated) |
| POST | `/api/v1/study/items` | JWT | Create study item |
| POST | `/api/v1/study/generate` | JWT | Generate AI study material — `202 Accepted` |
| POST | `/api/v1/study/screenshots/solve` | JWT | AI analysis of a screenshot (interview problem) |
| POST | `/api/v1/study/upload-materials` | JWT | Upload study materials |
| GET | `/api/v1/study/items/due` | JWT | Items due for review (SM-2 schedule) |
| POST | `/api/v1/study/items/{item_id}/review` | JWT | Submit SM-2 review result |

---

## Readiness

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/readiness` | JWT | Multi-dimensional readiness score |
| POST | `/api/v1/readiness/plan` | JWT | Generate personalized preparation plan |
| GET | `/api/v1/readiness/plan` | JWT | Retrieve current preparation plan |
| GET | `/api/v1/readiness/v2` | JWT | Extended readiness (v2 scoring model) |

---

## Preparation

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/preparation/plan` | JWT | Preparation plan details |
| POST | `/api/v1/preparation/jd-parse` | JWT | Trigger on-demand JD re-parse |
| GET | `/api/v1/preparation/jd-coverage` | JWT | How well resume covers JD requirements |
| GET | `/api/v1/sessions/{session_id}/difficulty` | JWT | Adaptive difficulty score for session |

---

## Prepare-Me (Interview Day)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/prepare-me` | JWT | Instant contextual preparation brief |
| GET | `/api/v1/interview-day/readiness-check` | JWT | Pre-interview readiness checklist |

---

## Analytics

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/analytics/dashboard` | JWT | Performance dashboard |
| GET | `/api/v1/analytics/reports` | JWT | Detailed reports (filterable) |
| GET | `/api/v1/daily/recommendation` | JWT | Daily practice recommendation |
| POST | `/api/v1/sessions/{session_id}/snapshot` | JWT | Capture analytics snapshot for session |
| GET | `/api/v1/sessions/compare` | JWT | Compare multiple sessions |
| POST | `/api/v1/weaknesses/detect` | JWT | Detect skill weaknesses from sessions |
| GET | `/api/v1/weaknesses` | JWT | Current weakness profile |
| GET | `/api/v1/communication/recommendations` | JWT | Communication skill recommendations |
| GET | `/api/v1/questions/{question_id}/attempts` | JWT | Attempt history for a question |
| POST | `/api/v1/improvement/ideal-answer` | JWT | Generate ideal answer for comparison |

---

## Memory / Profile

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/memory/summary` | JWT | AI-summarised candidate memory |
| POST | `/api/v1/memory/update-from-session` | JWT | Trigger memory update from session transcript |
| GET | `/api/v1/profile` | JWT | Full candidate profile (computed) |
| POST | `/api/v1/profile/compute` | JWT | Recompute profile from all sessions |

---

## Outreach

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/outreach/campaigns` | JWT | List outreach campaigns |
| POST | `/api/v1/outreach/draft` | JWT | Generate outreach message draft |

---

## Admin (role: admin required)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/admin/users` | JWT + admin | List users (paginated) |
| GET | `/api/v1/admin/providers` | JWT + admin | AI provider health + cost summary |
| GET | `/api/v1/admin/audit-logs` | JWT + admin | Audit log (paginated) |
| POST | `/api/v1/admin/users/ban` | JWT + admin | Ban a user account |

---

## Common Response Schemas

### `PaginatedResponse<T>`
```json
{
  "items": [...],
  "total": 42,
  "page": 1,
  "page_size": 20
}
```

### `QueuedTaskResponse`
```json
{
  "task_id": "uuid",
  "queued_at": "2026-10-05T12:00:00Z"
}
```

### Error (4xx / 5xx)
```json
{
  "detail": "Human-readable error message"
}
```

---

## Not Provided by This Backend

The following are handled outside the backend REST API:

| Capability | Where it lives |
|---|---|
| User signup | Supabase Auth (client SDK) |
| Login / token issuance | Supabase Auth (client SDK) |
| Token refresh | Supabase Auth (client SDK) |
| OAuth (Google, GitHub, etc.) | Supabase Auth (client SDK) |
| File storage URLs | Supabase Storage (signed URLs via storage SDK) |
| Realtime audio/STT/TTS | `realtime-agent` WebSocket service |

---

*Last updated: 2026-10-05 — Backend Sovereignty Engineering Pass*
