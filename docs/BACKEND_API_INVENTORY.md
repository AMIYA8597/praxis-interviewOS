# PRAXIS Backend API Inventory

All routes are mounted under `/api/v1` prefix except `/metrics` (mounted at root) and
`/health/*` (also mounted at `/api/v1`).

Authentication: `Auth Required = Yes` means the `get_current_user` dependency is present.
`Candidate Required` additionally requires a resolved `candidates` row.

---

## Auth Router (`backend/app/api/auth.py`)

| Method | Path | Auth | Purpose | Key Request Fields | Key Response Fields |
|---|---|---|---|---|---|
| POST | `/auth/logout` | Yes (user) | Invalidate server-side Redis cache for the caller | — | `{message}` |
| GET | `/auth/me` | Yes (user) | Return caller's user_id and email from JWT | — | `{user_id, email}` |
| DELETE | `/auth/account` | Yes (candidate) | Queue irreversible account deletion | — | `{status, job_id}` (202) |

Note: signup and login are handled by Supabase Auth directly (frontend calls Supabase SDK).
The backend does not implement `/auth/signup` or `/auth/login` endpoints.

---

## Candidates Router (`backend/app/api/candidates.py`)

| Method | Path | Auth | Purpose | Key Request Fields | Key Response Fields |
|---|---|---|---|---|---|
| GET | `/candidates/me` | Yes (candidate) | Get caller's candidate profile | — | CandidateResponse |
| PATCH | `/candidates/me` | Yes (candidate) | Partial-update caller's candidate profile | CandidateUpdate fields | CandidateResponse |
| PUT | `/candidates/me` | Yes (user) | Upsert candidate profile (onboarding) | CandidateUpdate fields | CandidateResponse (201 on create) |

---

## Resumes Router (`backend/app/api/resumes.py`)

| Method | Path | Auth | Purpose | Key Request Fields | Key Response Fields |
|---|---|---|---|---|---|
| POST | `/resumes` | Yes (candidate) | Upload a resume file; triggers async parsing | `file` (multipart, PDF/DOCX) | `{document_id, resume_id, status}` (202) |
| POST | `/resumes/upload` | Yes (candidate) | Alias for POST `/resumes` (legacy path) | Same | Same |
| GET | `/resumes` | Yes (candidate) | List all resumes (paginated) | `cursor`, `limit` | `{items: [ResumeResponse], next_cursor}` |
| GET | `/resumes/{id}` | Yes (candidate) | Get resume processing status | — | ResumeStatusResponse |
| GET | `/resumes/{id}/facts` | Yes (candidate) | List extracted resume claims | — | `[ResumeFactResponse]` |
| POST | `/resumes/{id}/facts/{fact_id}/confirm` | Yes (candidate) | Mark a resume fact as verified by user | — | ResumeFactResponse |
| POST | `/resumes/{id}/facts/{fact_id}/reject` | Yes (candidate) | Reject a resume fact | — | 204 No Content |
| PATCH | `/resumes/{id}/facts/{fact_id}` | Yes (candidate) | Update fact text | `{content}` | ResumeFactResponse |

---

## Jobs Router (`backend/app/api/jobs.py`)

| Method | Path | Auth | Purpose | Key Request Fields | Key Response Fields |
|---|---|---|---|---|---|
| POST | `/jobs` | Yes (candidate) | Create a job + queue JD analysis | `company_name`, `role_title`, `raw_jd_text` | `{job_id, status}` (202) |
| GET | `/jobs` | Yes (candidate) | List jobs (paginated) | `cursor`, `limit` | `{items: [JobResponse], next_cursor}` |
| GET | `/jobs/{id}` | Yes (candidate) | Get job + blueprint details | — | JobDetailResponse |
| DELETE | `/jobs/{id}` | Yes (candidate) | Delete a job and cascade | — | 204 No Content |

---

## Sessions Router (`backend/app/api/sessions.py`)

| Method | Path | Auth | Purpose | Key Request Fields | Key Response Fields |
|---|---|---|---|---|---|
| POST | `/sessions` | Yes (candidate) | Create a new interview session | `job_id` (opt), `mode`, `interview_type`, `difficulty` | SessionResponse (201) |
| GET | `/sessions` | Yes (candidate) | List sessions (paginated) | `cursor`, `limit` | `{items: [SessionResponse], next_cursor}` |
| GET | `/sessions/{id}` | Yes (candidate) | Get session details | — | SessionResponse |
| GET | `/sessions/{id}/turns` | Yes (candidate) | List all turns in a session | — | `[SessionTurnResponse]` |
| GET | `/sessions/{id}/debrief` | Yes (candidate) | Get session debrief (AI-generated summary) | — | SessionDebriefResponse |
| POST | `/sessions/{id}/end` | Yes (candidate) | Mark session complete + queue debrief generation | — | SessionEndResponse (202) |

---

## Study Router (`backend/app/api/study.py`)

| Method | Path | Auth | Purpose | Key Request Fields | Key Response Fields |
|---|---|---|---|---|---|
| GET | `/study/items` | Yes (candidate) | List all study items (paginated) | `cursor`, `limit` | `{items: [StudyItemResponse], next_cursor}` |
| POST | `/study/items` | Yes (candidate) | Create a study item manually | `topic`, `prompt`, `reference_answer`, `difficulty` | StudyItemResponse (201) |
| GET | `/study/items/due` | Yes (candidate) | Get items due for SM-2 review | `limit` | `{items: [StudyItemResponse]}` |
| POST | `/study/items/{item_id}/review` | Yes (candidate) | Record a review; advances SM-2 state | `quality` (0–5) | ReviewItemResponse |
| POST | `/study/generate` | Yes (candidate) | Queue AI generation of a study item | `topic`, `difficulty` | `{task_id, status}` (202) |
| POST | `/study/screenshots/solve` | Yes (candidate) | AI-solve a screenshot coding problem | `image_base64`, `screenshot_task_id` | `{solution, confidence}` |
| POST | `/study/items/from-solve/{solver_result_id}` | Yes (candidate) | Create a study item from a solver result | — | StudyItemResponse (201) |

---

## Readiness Router (`backend/app/api/readiness.py`)

| Method | Path | Auth | Purpose | Key Request Fields | Key Response Fields |
|---|---|---|---|---|---|
| GET | `/readiness` | Yes (candidate) | Compute interview readiness score | `job_id` (opt query param) | ReadinessResponse |
| POST | `/readiness/plan` | Yes (candidate) | Generate a preparation plan | `job_id` (opt query param) | PreparationPlanResponse |
| GET | `/readiness/plan` | Yes (candidate) | Get existing preparation plan | `job_id` (opt query param) | PreparationPlanResponse |

---

## Analytics Router (`backend/app/api/analytics.py`)

| Method | Path | Auth | Purpose | Key Request Fields | Key Response Fields |
|---|---|---|---|---|---|
| GET | `/analytics/dashboard` | Yes (candidate) | Aggregate session metrics dashboard | — | `{interviews_completed, average_score, average_pace_wpm, ...}` |
| GET | `/analytics/reports` | Yes (candidate) | Per-session report list | `limit` | `{reports: [...]}` |
| GET | `/daily/recommendation` | Yes (candidate) | Today's practice recommendation | `job_id` (opt) | Recommendation object |
| POST | `/sessions/{session_id}/snapshot` | Yes (candidate) | Snapshot a session's performance metrics | — | Snapshot object |
| GET | `/sessions/compare` | Yes (candidate) | Compare sessions over time | — | Comparison object |
| POST | `/weaknesses/detect` | Yes (candidate) | Detect and persist weakness patterns | — | Weaknesses list |
| GET | `/weaknesses` | Yes (candidate) | Get current unresolved weaknesses | — | `{weaknesses: [...]}` |
| GET | `/communication/recommendations` | Yes (candidate) | Communication coaching recommendations | — | `{recommendations: [...]}` |
| GET | `/questions/{question_id}/attempts` | Yes (candidate) | Answer history for a question | — | `{attempts: [...], total}` |
| POST | `/improvement/ideal-answer` | Yes (candidate) | Generate ideal answer feedback | `question_text`, `candidate_answer`, scores | Feedback object |

---

## Admin Router (`backend/app/api/admin.py`)

All admin routes require `require_admin` dependency (checks `admin_users` table).

| Method | Path | Auth | Purpose | Key Request Fields | Key Response Fields |
|---|---|---|---|---|---|
| GET | `/admin/users` | Admin | List all candidates (paginated) | `cursor`, `limit` | `{users: [...], next_cursor}` |
| GET | `/admin/providers` | Admin | AI provider health snapshot | — | Provider status dict |
| GET | `/admin/audit-logs` | Admin | Paginated audit log | `cursor`, `limit` | `{logs: [...], next_cursor}` |
| POST | `/admin/users/ban` | Admin | Ban a user | `user_id`, `reason` | `{status, user_id, reason}` |

---

## Health Router (`backend/app/api/health.py`)

No authentication required.

| Method | Path | Auth | Purpose | Key Response Fields |
|---|---|---|---|---|
| GET | `/health/live` | No | Liveness probe | `{status: "ok"}` |
| GET | `/health/ready` | No | Readiness probe (checks DB + Redis) | `{status: "ready"}` or 503 with component details |
| GET | `/health/providers` | No | AI provider circuit breaker state | `{status, providers: {name: {capabilities, circuit_breaker_state}}}` |

---

## Metrics Router (`backend/app/api/metrics.py`)

Mounted at root (no `/api/v1` prefix). Not included in OpenAPI schema.

| Method | Path | Auth | Purpose | Response |
|---|---|---|---|---|
| GET | `/metrics` | No (network-level restriction) | Prometheus metrics scrape endpoint | Prometheus text format |

Metrics defined: `praxis_http_requests_total`, `praxis_http_request_duration_seconds`,
`praxis_ai_calls_total`, `praxis_ai_tokens_total`, `praxis_ai_cost_usd_total`,
`praxis_ai_budget_exceeded_total`, `praxis_ai_output_safety_violations_total`,
`praxis_worker_jobs_total`, `praxis_resume_processing_total`,
`praxis_interview_sessions_total`, `praxis_rls_violations_total`,
`praxis_rate_limit_hits_total`.

---

## Additional Routers (not detailed above)

The following routers are registered in `backend/app/main.py` but not fully documented here:

- **memory** (`/api/v1/memory`) — Candidate memory management
- **preparation** (`/api/v1/preparation`) — Preparation sessions
- **interview_engines** (`/api/v1/interview_engines`) — Interview engine configuration
- **observability** (`/api/v1/observability`) — Internal observability endpoints
- **prepare_me** (`/api/v1/prepare_me`) — Guided preparation flow
- **outreach** (`/api/v1/outreach`) — Outreach draft management
- **applications** (`/api/v1/applications`) — Job application tracking
- **projects** (`/api/v1/projects`) — Candidate project management
- **questions** (`/api/v1/questions`) — Question bank
