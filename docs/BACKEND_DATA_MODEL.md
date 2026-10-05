# PRAXIS Backend Data Model

All tables live in the Supabase `public` schema. Every table has `created_at timestamptz`
and (where mutable) `updated_at timestamptz` maintained by a `set_updated_at()` trigger.
All IDs are UUID v4. Foreign key cascades are `ON DELETE CASCADE` unless noted.

**Canonical** = single authoritative source. **Derived** = computed/aggregated from other tables.

---

## Identity & Profile Group

### `auth.users` (Supabase managed)
Not in `public` schema. Owned by Supabase Auth. The PK (`id: uuid`) is the root identity
anchor for the entire system. PRAXIS never writes to this table.

### `profiles` — CANONICAL
Bridge between `auth.users` and the application.

| Column | Type | Notes |
|---|---|---|
| `id` | uuid PK | FK → `auth.users(id)` ON DELETE CASCADE |
| `created_at` | timestamptz | |
| `updated_at` | timestamptz | |

RLS: owner-only CRUD (`id = auth.uid()`). `is_admin()` function queries this table via
`admin_users`. The `profiles` row is the RLS root — all tenant data chains back to it.

### `candidates` — CANONICAL
One per user. Stores career identity and onboarding state.

| Column | Type | Notes |
|---|---|---|
| `id` | uuid PK | |
| `profile_id` | uuid | FK → `profiles(id)` |
| `full_name` | text | Required |
| `headline`, `location` | text | |
| `years_experience` | numeric | |
| `target_roles` | text[] | |
| `preferred_language` | text | |
| `speaking_style` | jsonb | Interviewer persona config |
| `onboarding_step`, `onboarding_completed_at` | | |

RLS: `profile_id = auth.uid()`.

### `admin_users` — CANONICAL
Grants admin role to a profile. Managed out-of-band (no self-service endpoint).

| Column | Type | Notes |
|---|---|---|
| `profile_id` | uuid | FK → `profiles(id)`, UNIQUE |
| `role` | text | Future: granular admin roles |

RLS: SELECT own row or `is_admin()`; mutations admin-only.

---

## Document & Resume Group

### `documents` — CANONICAL
Represents an uploaded file (resume, other). Processing pipeline state machine here.

| Column | Type | Notes |
|---|---|---|
| `candidate_id` | uuid | |
| `kind` | text | `resume` or `other` |
| `original_filename`, `storage_path` | text | GCS path |
| `mime_type`, `size_bytes` | | |
| `processing_status` | text | `uploading → parsing → embedding → ready / failed` |
| `error_message` | text | Set on failure |

RLS: candidate-scoped.

### `resumes` — CANONICAL
Links a document to a candidate as a resume. Supports multiple resumes with a primary flag.

| Column | Type | Notes |
|---|---|---|
| `document_id` | uuid | FK → `documents(id)` |
| `is_primary` | boolean | |

RLS: candidate-scoped.

### `resume_versions` — CANONICAL
Versioned snapshots of a resume (e.g. one per extraction run, one per JD tailoring).

| Column | Type | Notes |
|---|---|---|
| `resume_id` | uuid | FK → `resumes(id)` |
| `version_number` | int | |
| `label` | text | e.g. `extracted`, `tailored` |
| `generated_for_job_id` | uuid | FK → `jobs(id)` ON DELETE SET NULL |

### `resume_claims` — CANONICAL
Individual extracted facts from a resume version.

| Column | Type | Notes |
|---|---|---|
| `resume_version_id` | uuid | |
| `claim_text` | text | The extracted fact |
| `claim_type` | text | `skill / metric / role / project / education / certification` |
| `page`, `char_start`, `char_end` | int | Source location in document |
| `extraction_confidence` | numeric | LLM confidence [0,1] |
| `verified_by_user` | boolean | User confirmed/rejected |

RLS: three-hop chain (`resume_claims → resume_versions → resumes → candidates`).

### `document_chunks` — CANONICAL
Chunked text from any document with dual-mode search indexes.

| Column | Type | Notes |
|---|---|---|
| `document_id` | uuid | |
| `chunk_index` | int | Chunk order, UNIQUE with `document_id` |
| `content` | text | Raw text chunk |
| `token_count` | int | |
| `embedding` | vector(384) | bge-small-en-v1.5 embeddings. NULL if embedding failed. |
| `embedding_model`, `embedding_version` | text | |
| `metadata` | jsonb | |
| `content_tsv` | tsvector | Generated: `to_tsvector('english', content)` — for BM25/FTS |

RLS: two-hop chain (`document_chunks → documents → candidates`).
This table is the primary RAG source. Hybrid search uses both `embedding` (pgvector HNSW)
and `content_tsv` (GIN index) simultaneously.

---

## Job Brain Group

### `jobs` — CANONICAL
A job description provided by the candidate. Source of JD-specific prep.

| Column | Type | Notes |
|---|---|---|
| `candidate_id` | uuid | |
| `company_name`, `role_title` | text | Required |
| `raw_jd_text` | text | Full JD pasted by user |
| `seniority_signal` | text | Extracted by AI (e.g. "Senior", "Staff") |
| `processing_status` | text | `uploading → parsing → ready / failed` |

RLS: candidate-scoped.

### `job_blueprints` — DERIVED
AI-extracted structured analysis of a job. One per job (UNIQUE).

| Column | Type | Notes |
|---|---|---|
| `job_id` | uuid | UNIQUE |
| `top_skills` | jsonb | Required skills list |
| `likely_topics` | text[] | Predicted interview topics |
| `summary` | text | Human-readable role summary |
| `prep_pack` | jsonb | Extended prep data |

### `job_requirements` — DERIVED
Individual requirements extracted from `job_blueprints`.

| Column | Type | Notes |
|---|---|---|
| `job_blueprint_id` | uuid | |
| `skill_text` | text | Literal requirement text |
| `category` | text | e.g. `technical`, `behavioral` |
| `priority` | text | `required` or `preferred` |
| `evidence_quote` | text | Verbatim quote from JD |

### `job_matches` — DERIVED
Scored match between candidate and job. One per job (UNIQUE).

| Column | Type | Notes |
|---|---|---|
| `overall_score` | numeric | Aggregate match score |
| `methodology_version` | text | Version tracking |
| `breakdown` | jsonb | Per-dimension scores |

---

## Interview Session Group

### `practice_sessions` — CANONICAL
Root of an interview session. All session data hangs off this.

| Column | Type | Notes |
|---|---|---|
| `candidate_id` | uuid | |
| `job_id` | uuid | Optional — FK → `jobs(id)` ON DELETE CASCADE |
| `mode` | text | `mock_interview / drill / freeform / debrief` |
| `interview_type` | text | `behavioral / technical / system_design / mixed / screening` |
| `difficulty` | text | `warmup / standard / senior / stress` |
| `started_at`, `ended_at`, `duration_s` | | |
| `turn_count` | int | |
| `stt_provider`, `llm_provider`, `tts_provider` | text | Provider actually used |
| `fallback_count` | int | How many AI fallbacks occurred |
| `status` | text | `active / completed / abandoned / failed` |

### `session_turns` — CANONICAL
Individual turns in a session. UNIQUE on `(session_id, turn_index)`.

| Column | Type | Notes |
|---|---|---|
| `session_id` | uuid | |
| `turn_index` | int | Ordered |
| `speaker` | text | `interviewer` or `candidate` |
| `question_id` | uuid | Optional reference to question bank |
| `parent_turn_id` | uuid | Self-FK for follow-up tree |
| `text` | text | Finalized transcript |
| `started_at`, `ended_at`, `duration_ms` | | |

### `turn_scores` — CANONICAL
LLM-generated rubric scores per turn. One per turn (UNIQUE).

| Column | Type | Notes |
|---|---|---|
| `turn_id` | uuid | UNIQUE |
| `rubric_version` | text | Tracks which rubric generated the score |
| `relevance`, `correctness`, `structure`, `grounding`, `specificity`, `conciseness` | numeric | [0,10] each |
| `star_completeness` | jsonb | Per-component STAR scores |
| `overall` | numeric | [0,10] |
| `rationale` | text | LLM explanation |
| `model_used` | text | |
| `scored_at` | timestamptz | |

`rubric_version` enables future score comparisons across rubric updates.

### `turn_metrics` — DERIVED
Acoustic/linguistic metrics computed from transcript. One per turn (UNIQUE).

Key columns: `wpm`, `filler_count`, `filler_rate`, `filler_breakdown` (jsonb),
`pause_count`, `longest_pause_ms`, `pause_ratio`, `hedge_count`, `time_to_first_word_ms`.

### `transcript_segments` — CANONICAL
Raw STT output including interim segments. Full provenance chain.

| Column | Type | Notes |
|---|---|---|
| `turn_id` | uuid | |
| `is_interim` | boolean | |
| `text`, `start_ms`, `end_ms`, `confidence` | | |

### `session_claims` — DERIVED
Claims made by the candidate during the session, grounded against resume chunks.

| Column | Type | Notes |
|---|---|---|
| `claim_text` | text | Claim extracted from candidate's answer |
| `supported` | boolean | Whether grounding found evidence |
| `source_chunk_id` | uuid | FK → `document_chunks(id)` ON DELETE SET NULL |
| `source_project_id` | uuid | FK → `candidate_projects(id)` ON DELETE SET NULL |
| `confidence` | numeric | |
| `contradiction_of_claim_id` | uuid | Self-FK for contradiction detection |

### `session_debriefs` — DERIVED
Post-session AI-generated summary. One per session (UNIQUE). Generated asynchronously
by the `generate_session_debrief_job` ARQ worker.

Key columns: `headline_metrics` (jsonb), `strengths` (text[]), `weaknesses` (text[]),
`flagged_claims` (jsonb), `jd_coverage` (jsonb).

### `session_state_log` — CANONICAL
State machine transition log for a session. Append-only (no `updated_at`).

---

## Study Loop Group

### `study_items` — CANONICAL
Spaced-repetition flashcard items. SM-2 state stored inline.

| Column | Type | Notes |
|---|---|---|
| `candidate_id` | uuid | |
| `topic` | text | |
| `source` | text | `weak_answer / missed_concept / jd_gap / manual` |
| `source_turn_id` | uuid | FK → `session_turns(id)` ON DELETE CASCADE |
| `prompt` | text | Question |
| `reference_answer` | text | Ideal answer |
| `difficulty` | text | |
| `ease_factor` | numeric | SM-2 E-factor, default 2.5 |
| `interval_days` | int | SM-2 interval |
| `next_review_at` | timestamptz | Scheduled review time |

### `study_reviews` — CANONICAL
Individual review events. Append-only (no `updated_at`).

| Column | Type | Notes |
|---|---|---|
| `item_id` | uuid | |
| `quality` | int | SM-2 quality rating 0–5 |
| `new_interval_days`, `new_ease_factor` | | Post-review SM-2 state |

---

## Analytics & Governance Group

### `usage_events` — CANONICAL
Per-call AI provider usage. Written by `GatewayRouter._log_usage()`.

Key columns: `provider`, `model`, `capability`, `input_tokens`, `output_tokens`,
`estimated_cost_usd`, `was_free_tier`, `latency_ms`, `fell_back_from`.

Used by: budget guard (via Redis), admin AI usage reports.

### `audit_logs` — CANONICAL
Append-only security audit trail. Admin-read only via RLS.

### `feature_flags` — CANONICAL
Platform-wide feature toggles. Admin-managed. Read by all users.

### `provider_health` — DERIVED
Circuit breaker state and latency statistics per provider/capability. Updated by
`CircuitBreaker` in the AI Gateway.

Key columns: `state` (`closed / open / half_open`), `consecutive_failures`,
`latency_p50_ms`, `latency_p95_ms`, `latency_p99_ms`, `error_rate`.

### `privacy_events` — CANONICAL
Consent and retention-purge events. Admin-read only via RLS.

### `deletion_jobs` — CANONICAL
Queued/running/completed account deletion requests. Written by `DELETE /auth/account`.

---

## Skills Catalog (shared)

### `skills` — CANONICAL
Global skills dictionary. Not tenant-scoped.
INSERT/UPDATE/DELETE: admin only. SELECT: public.

### `candidate_skills` — CANONICAL
Many-to-many junction: candidate ↔ skill with proficiency and evidence source.
UNIQUE on `(candidate_id, skill_id)`.
