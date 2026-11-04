# PRAXIS InterviewOS — Master API Inventory

**Audit Date:** 2026-11-04  
**FastAPI Version:** 0.115+ (mounted under `/api/v1` prefix and root `/health`, `/metrics`)  
**Total Registered Routes:** 106  
**OpenAPI Specification:** Available at `/openapi.json` and generated in `docs/openapi.json`  

---

## 1. Authentication & Candidate Profile Domain

| Method | Endpoint Path | Auth Scope | Function / Handler | Purpose & Contract |
|---|---|---|---|---|
| `GET` | `/api/v1/auth/me` | Bearer User | `get_me` | Resolves authenticated user ID, email, and role from JWT claims. |
| `POST` | `/api/v1/auth/logout` | Bearer User | `logout` | Clears Redis server-side session cache for the caller. |
| `DELETE` | `/api/v1/auth/account` | Bearer Candidate | `delete_account` | Enqueues irreversible GDPR cascading deletion job. Returns 202 Accepted. |
| `GET` | `/api/v1/candidates/me` | Bearer Candidate | `get_me` | Retrieves caller's candidate record, skills, target roles, and status. |
| `PATCH` | `/api/v1/candidates/me` | Bearer Candidate | `update_me` | Partially updates candidate fields (e.g. `full_name`, `target_role`). |
| `PUT` | `/api/v1/candidates/me` | Bearer User | `upsert_me` | Upserts candidate profile on onboarding completion. Returns 201 Created. |
| `GET` | `/api/v1/profile` | Bearer Candidate | `get_profile` | Alias for candidate profile with populated skill graph. |
| `POST` | `/api/v1/profile/compute` | Bearer Candidate | `compute_profile` | Recalculates candidate aggregate metrics from verified resume facts. |

---

## 2. Resumes, Evidence & Claim Extraction Domain

| Method | Endpoint Path | Auth Scope | Function / Handler | Purpose & Contract |
|---|---|---|---|---|
| `POST` | `/api/v1/resumes` | Bearer Candidate | `upload_resume` | Multipart upload (PDF/DOCX). Validates MIME type, stores file, triggers parsing worker. Returns 202. |
| `POST` | `/api/v1/resumes/upload` | Bearer Candidate | `upload_resume_legacy` | Legacy alias for `/resumes`. |
| `GET` | `/api/v1/resumes` | Bearer Candidate | `list_resumes` | Cursor-paginated list of uploaded resumes and processing statuses. |
| `GET` | `/api/v1/resumes/{id}` | Bearer Candidate | `get_resume_status` | Status probe for background chunking, embedding, and claim extraction. |
| `GET` | `/api/v1/resumes/{id}/facts` | Bearer Candidate | `get_resume_facts` | Extracted facts/claims with provenance chunk IDs and verification states. |
| `PATCH` | `/api/v1/resumes/{id}/facts/{fact_id}` | Bearer Candidate | `update_resume_fact` | Allows candidate to correct extracted claim text. |
| `POST` | `/api/v1/resumes/{id}/facts/{fact_id}/confirm` | Bearer Candidate | `confirm_resume_fact` | Candidate marks extracted fact as verified evidence. |
| `POST` | `/api/v1/resumes/{id}/facts/{fact_id}/reject` | Bearer Candidate | `reject_resume_fact` | Candidate flags extracted fact as inaccurate or rejected. |
| `POST` | `/api/v1/resumes/tailored` | Bearer Candidate | `generate_tailored_resume` | Generates targeted resume draft aligned to a specific job description. |

---

## 3. Job Intelligence, Blueprints & Applications Domain

| Method | Endpoint Path | Auth Scope | Function / Handler | Purpose & Contract |
|---|---|---|---|---|
| `POST` | `/api/v1/jobs` | Bearer Candidate | `create_job` | Ingests job description text, generates blueprint and requirement graph. |
| `GET` | `/api/v1/jobs` | Bearer Candidate | `list_jobs` | Paginated listing of candidate's saved job targets. |
| `GET` | `/api/v1/jobs/{id}` | Bearer Candidate | `get_job` | Full job details including parsed required and preferred competencies. |
| `DELETE` | `/api/v1/jobs/{id}` | Bearer Candidate | `delete_job` | Deletes job target and associated application artifacts. Returns 204. |
| `GET` | `/api/v1/applications` | Bearer Candidate | `list_applications` | Pipeline tracking across applied jobs, interview stages, and offers. |
| `POST` | `/api/v1/applications` | Bearer Candidate | `create_application` | Associates a job with application tracking stages. |
| `GET` | `/api/v1/applications/{app_id}` | Bearer Candidate | `get_application` | Detailed application timeline and notes. |
| `PATCH` | `/api/v1/applications/{app_id}` | Bearer Candidate | `update_application` | Updates stage (e.g. `SCREENING`, `TECHNICAL`, `OFFER`). |
| `DELETE` | `/api/v1/applications/{app_id}` | Bearer Candidate | `delete_application` | Removes application entry. |
| `POST` | `/api/v1/preparation/jd-parse` | Bearer Candidate | `parse_jd` | Direct synchronous extraction of skills and requirements from raw text. |
| `GET` | `/api/v1/preparation/jd-coverage` | Bearer Candidate | `get_jd_coverage` | Analyzes percentage of JD requirements covered by candidate resume evidence. |
| `GET` | `/api/v1/preparation/plan` | Bearer Candidate | `get_preparation_plan` | Retrieves structured study timeline and mock interview targets for JD. |
| `POST` | `/api/v1/prepare-me` | Bearer Candidate | `prepare_me` | Guided preparation flow generating targeted drills and question sets. |
| `GET` | `/api/v1/outreach/campaigns` | Bearer Candidate | `list_campaigns` | Lists recruiter and hiring manager outreach drafts. |
| `POST` | `/api/v1/outreach/draft` | Bearer Candidate | `draft_outreach` | AI-assisted generation of tailored networking and referral outreach. |

---

## 4. Practice Sessions, Turns & Debrief Domain

| Method | Endpoint Path | Auth Scope | Function / Handler | Purpose & Contract |
|---|---|---|---|---|
| `POST` | `/api/v1/sessions` | Bearer Candidate | `create_session` | Initializes new interview session with specified mode, role, and difficulty. |
| `GET` | `/api/v1/sessions` | Bearer Candidate | `list_sessions` | Paginated list of completed and in-progress sessions. |
| `GET` | `/api/v1/sessions/{id}` | Bearer Candidate | `get_session` | Session metadata, status, duration, and interviewer personality. |
| `GET` | `/api/v1/sessions/{id}/turns` | Bearer Candidate | `get_session_turns` | Ordered dialogue history with turn-level audio scores and DSP metrics. |
| `GET` | `/api/v1/sessions/{id}/debrief` | Bearer Candidate | `get_session_debrief` | Comprehensive session debrief: headline metrics, strengths, weaknesses, claims. |
| `POST` | `/api/v1/sessions/{id}/end` | Bearer Candidate | `end_session` | Completes active session and triggers asynchronous debrief generation. |
| `POST` | `/api/v1/sessions/{session_id}/snapshot` | Bearer Candidate | `snapshot_session` | Captures intermediate session checkpoint during long interviews. |
| `GET` | `/api/v1/sessions/compare` | Bearer Candidate | `compare_sessions` | Compares scores, speaking rate, and rubric performance across multiple sessions. |
| `GET` | `/api/v1/sessions/{session_id}/difficulty` | Bearer Candidate | `get_difficulty` | Returns current adaptive difficulty level and historical difficulty trajectory. |

---

## 5. Specialized Interview Engines Domain

| Method | Endpoint Path | Auth Scope | Function / Handler | Purpose & Contract |
|---|---|---|---|---|
| `POST` | `/api/v1/sessions/{session_id}/code/run` | Bearer Candidate | `run_code` | Dispatches untrusted candidate code to isolated sandbox service. |
| `GET` | `/api/v1/sessions/{session_id}/code/state` | Bearer Candidate | `get_code_state` | Retrieves candidate code editor buffer, language, and execution history. |
| `POST` | `/api/v1/sessions/{session_id}/system-design/advance` | Bearer Candidate | `advance_sd_phase` | Advances 24-phase system design state machine (requirements -> capacity -> API). |
| `GET` | `/api/v1/sessions/{session_id}/system-design/state` | Bearer Candidate | `get_sd_state` | Current system design phase, active dynamic challenge, and component graph. |
| `POST` | `/api/v1/sessions/{session_id}/diagram/analyze` | Bearer Candidate | `analyze_diagram` | Analyzes candidate architecture diagram components, connections, and bottlenecks. |
| `POST` | `/api/v1/behavioral/star-analysis` | Bearer Candidate | `analyze_star` | Evaluates behavioral response for STAR completeness and ownership language. |
| `POST` | `/api/v1/behavioral/resume-probe` | Bearer Candidate | `generate_resume_probe` | Generates deep-dive follow-up question probing specific resume metrics. |
| `GET` | `/api/v1/interviewer/personalities` | Bearer Candidate | `list_personalities` | Lists available interviewer personas (`Socratic`, `Direct`, `Supportive`). |
| `POST` | `/api/v1/interviewer/personality` | Bearer Candidate | `set_personality` | Selects interviewer persona for upcoming sessions. |

---

## 6. Question Bank & Variants Domain

| Method | Endpoint Path | Auth Scope | Function / Handler | Purpose & Contract |
|---|---|---|---|---|
| `GET` | `/api/v1/questions` | Bearer Candidate | `list_questions` | Filterable question catalog (by domain, seniority, and track). |
| `POST` | `/api/v1/questions` | Bearer Candidate | `create_question` | Creates new custom question variant with evaluation rubric. |
| `GET` | `/api/v1/questions/domains` | Bearer Candidate | `list_domains` | Canonical engineering domains (`Distributed Systems`, `Databases`, `DSA`). |
| `GET` | `/api/v1/questions/{question_id}` | Bearer Candidate | `get_question` | Question prompt, expected keywords, rubrics, and difficulty. |
| `GET` | `/api/v1/questions/{question_id}/attempts` | Bearer Candidate | `get_answer_history` | History of candidate responses and scored attempts on a question. |

---

## 7. Study Cards & SM-2 Spaced Repetition Domain

| Method | Endpoint Path | Auth Scope | Function / Handler | Purpose & Contract |
|---|---|---|---|---|
| `GET` | `/api/v1/study/items` | Bearer Candidate | `list_study_items` | Paginated listing of study cards in candidate review deck. |
| `POST` | `/api/v1/study/items` | Bearer Candidate | `create_study_item` | Manually creates flashcard item with reference answer and topic. |
| `GET` | `/api/v1/study/items/due` | Bearer Candidate | `get_due_items` | Fetches cards currently due for review according to SM-2 schedule. |
| `POST` | `/api/v1/study/items/{item_id}/review` | Bearer Candidate | `review_study_item` | Submits recall score (0-5); updates repetition count, interval, and ease factor. |
| `POST` | `/api/v1/study/generate` | Bearer Candidate | `generate_study_material` | AI generation of targeted study cards based on session weaknesses. |
| `GET` | `/api/v1/study/materials` | Bearer Candidate | `get_study_materials` | Returns categorized reference materials and cheat sheets. |
| `POST` | `/api/v1/study/screenshots/solve` | Bearer Candidate | `solve_screenshot_endpoint` | OCR + VLM solver for coding/technical screenshot problems. |
| `POST` | `/api/v1/study/items/from-solve/{solver_result_id}` | Bearer Candidate | `create_item_from_solve` | Converts a solved screenshot problem into a permanent study card. |

---

## 8. Readiness, Weaknesses & Analytics Domain

| Method | Endpoint Path | Auth Scope | Function / Handler | Purpose & Contract |
|---|---|---|---|---|
| `GET` | `/api/v1/readiness` | Bearer Candidate | `get_readiness` | Comprehensive readiness score across technical, behavioral, and pacing metrics. |
| `GET` | `/api/v1/readiness/v2` | Bearer Candidate | `get_readiness_v2` | Advanced multi-dimensional readiness model with Bayesian confidence bounds. |
| `POST` | `/api/v1/readiness/plan` | Bearer Candidate | `generate_plan` | Generates structured preparation roadmap to achieve target readiness score. |
| `GET` | `/api/v1/readiness/plan` | Bearer Candidate | `get_plan` | Retrieves active preparation roadmap and milestone status. |
| `GET` | `/api/v1/weaknesses` | Bearer Candidate | `get_weaknesses` | Active detected weaknesses with supporting evidence and frequency counts. |
| `POST` | `/api/v1/weaknesses/detect` | Bearer Candidate | `detect_weaknesses` | Analyzes recent session transcripts to identify recurring knowledge gaps. |
| `GET` | `/api/v1/analytics/dashboard` | Bearer Candidate | `get_dashboard` | High-level candidate statistics (sessions completed, avg score, total duration). |
| `GET` | `/api/v1/analytics/reports` | Bearer Candidate | `get_reports` | Detailed per-session analytics and performance trends. |
| `GET` | `/api/v1/daily/recommendation` | Bearer Candidate | `get_daily_recommendation` | Recommended daily drill based on spaced repetition and skill gaps. |
| `GET` | `/api/v1/communication/recommendations` | Bearer Candidate | `get_communication_recommendations` | Speech coaching insights (speaking pace, filler word reduction, conciseness). |
| `POST` | `/api/v1/improvement/ideal-answer` | Bearer Candidate | `generate_ideal_answer` | Generates model answer and structured comparison against candidate transcript. |
| `GET` | `/api/v1/interview-day/readiness-check` | Bearer Candidate | `interview_day_readiness_check` | Pre-interview checklist and confidence assessment. |

---

## 9. GDPR Data Exports Domain

| Method | Endpoint Path | Auth Scope | Function / Handler | Purpose & Contract |
|---|---|---|---|---|
| `POST` | `/api/v1/export` | Bearer Candidate | `initiate_export` | Enqueues full GDPR archive export. Rate limited (1 per 24 hours). Returns 202. |
| `GET` | `/api/v1/export/{export_id}` | Bearer Candidate | `get_export_status` | Status probe for export job; returns expiring private download URL when ready. |

---

## 10. Admin & Observability Domain

| Method | Endpoint Path | Auth Scope | Function / Handler | Purpose & Contract |
|---|---|---|---|---|
| `GET` | `/api/v1/admin/users` | Bearer Admin | `list_users` | Paginated listing of system users, candidate IDs, and activity timestamps. |
| `POST` | `/api/v1/admin/users/ban` | Bearer Admin | `ban_user` | Administrative suspension of user account and active sessions. |
| `GET` | `/api/v1/admin/providers` | Bearer Admin | `get_admin_providers` | Live health, circuit breaker states, and rate limit budgets for all AI providers. |
| `GET` | `/api/v1/admin/audit-logs` | Bearer Admin | `get_audit_logs` | Append-only security audit log of auth events, data exports, and admin actions. |
| `GET` | `/api/v1/observability/provider-health` | Bearer Admin | `get_provider_health` | Detailed provider latency, token throughput, and error rates. |
| `GET` | `/api/v1/observability/cost-latency` | Bearer Admin | `get_cost_latency` | Aggregated dollar spend and latency percentiles (p50, p95, p99). |
| `GET` | `/api/v1/observability/system` | Bearer Admin | `get_system_metrics` | Database pool utilization, Redis memory, and ARQ queue depths. |

---

## 11. Platform Health & Telemetry Probes

| Method | Endpoint Path | Auth Scope | Function / Handler | Purpose & Contract |
|---|---|---|---|---|
| `GET` | `/health` / `/health/live` | Public | `live_check` | Kubernetes/Cloud Run liveness probe. Returns 200 OK `{status: "ok"}`. |
| `GET` | `/health/ready` | Public | `ready_check` | Readiness probe. Validates PostgreSQL connection pool and Redis reachability. Returns 503 if degraded. |
| `GET` | `/health/startup` | Public | `startup_check` | Startup probe. Verifies database schema and confirms all 31 migrations applied. |
| `GET` | `/health/providers` | Public | `providers_check` | AI Gateway circuit breaker state and configured provider availability. |
| `GET` | `/metrics` | Restricted | `metrics` | Prometheus metrics scrape endpoint (HTTP duration, AI tokens, RLS violations). |
