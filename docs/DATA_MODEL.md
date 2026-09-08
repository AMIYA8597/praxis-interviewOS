PART 4 — DATA MODEL

## 4.1 ER overview

```
auth.users (Supabase)
   │ 1:1
   ▼
profiles ──────────────────────────────────────────────┐
   │ 1:1                                                │
   ▼                                                    │
candidates                                              │
   ├──1:N──▶ candidate_skills ──N:1──▶ skills           │
   ├──1:N──▶ candidate_experiences                      │
   ├──1:N──▶ candidate_education                        │
   ├──1:N──▶ candidate_projects ──1:N──▶ project_metrics│
   │              └──1:N──▶ stories (STAR bank)         │
   ├──1:N──▶ candidate_certifications                   │
   ├──1:N──▶ resumes ──1:N──▶ resume_versions           │
   │                              └──1:N──▶ resume_claims
   ├──1:N──▶ documents ──1:N──▶ document_chunks (vector)│
   ├──1:N──▶ jobs ──1:1──▶ job_blueprints               │
   │            ├──1:N──▶ job_requirements              │
   │            ├──1:1──▶ job_matches                   │
   │            └──1:N──▶ applications ──1:N──▶ application_events
   ├──1:N──▶ practice_sessions                          │
   │            ├──1:N──▶ session_turns                 │
   │            │            ├──1:N──▶ transcript_segments
   │            │            ├──1:1──▶ turn_metrics     │
   │            │            └──1:1──▶ turn_scores      │
   │            ├──1:N──▶ session_claims ───────────────┘ (→ document_chunks)
   │            ├──1:1──▶ session_debriefs
   │            └──1:N──▶ session_state_log
   ├──1:N──▶ study_items ──1:N──▶ study_reviews (SRS)
   ├──1:N──▶ screenshot_tasks ──1:1──▶ solver_results
   └──1:N──▶ outreach_drafts

provider_configs · provider_health · model_requests · usage_events
feature_flags · user_settings · shortcuts · notifications
audit_logs · privacy_events · deletion_jobs · admin_users
```

## 4.2 Table specifications (abridged — full DDL is generated in Phase 1)

**Conventions applied to every table:** `id uuid pk default gen_random_uuid()`, `created_at timestamptz not null default now()`, `updated_at timestamptz` (trigger-maintained), RLS enabled, owner column indexed.

* **`candidates`** — `user_id fk`, `full_name`, `headline`, `location`, `years_experience numeric`, `target_roles text[]`, `preferred_language`, `speaking_style jsonb`, `onboarding_step`, `onboarding_completed_at`
* **`candidate_projects`** — the highest-value table in the system. `candidate_id`, `name`, `summary`, `problem`, `motivation`, `users_served`, `architecture`, `tech_stack text[]`, `datasets`, `data_pipeline`, `models_used text[]`, `training_approach`, `evaluation_method`, `metrics jsonb`, `deployment`, `infra`, `challenges`, `failure_cases`, `tradeoffs`, `improvements`, `business_impact`, `personal_contribution`, `team_size`, `duration_months`, `github_url`, `demo_url`, `confidence numeric`, `verified_by_user boolean not null default false`
  * > **NOTE**: `verified_by_user` is load-bearing. An LLM extraction is a hypothesis until the human confirms it. Nothing unverified may be cited as candidate evidence in feedback. Enforce this in the retrieval query, not in the UI.
* **`resume_claims`** — `resume_version_id`, `claim_text`, `claim_type (skill|metric|role|project|education|certification)`, `page int`, `char_start int`, `char_end int`, `extraction_confidence numeric`, `verified_by_user boolean default false`, `verified_at`
* **`document_chunks`** — `document_id`, `chunk_index`, `content text`, `token_count`, `embedding vector(384)`, `embedding_model`, `embedding_version`, `metadata jsonb`, `content_tsv tsvector generated always as (to_tsvector('english', content)) stored`
  * > **Indexes**: HNSW on `embedding` (vector_cosine_ops), GIN on `content_tsv`. Both — hybrid retrieval needs both.
* **`practice_sessions`** — `candidate_id`, `job_id nullable`, `mode (mock_interview|drill|freeform|debrief)`, `interview_type (behavioral|technical|system_design|mixed|screening)`, `difficulty (warmup|standard|senior|stress)`, `language`, `persona jsonb`, `started_at`, `ended_at`, `duration_s`, `turn_count`, `stt_provider`, `llm_provider`, `tts_provider`, `fallback_count int default 0`, `status`
* **`session_turns`** — `session_id`, `turn_index`, `speaker (interviewer|candidate)`, `question_id nullable`, `parent_turn_id nullable` ← **this is the follow-up graph edge**, `text`, `started_at`, `ended_at`, `duration_ms`
* **`turn_metrics`** — the coaching layer's output, all locally computed: `turn_id`, `word_count`, `duration_ms`, `wpm numeric`, `filler_count int`, `filler_rate numeric`, `filler_breakdown jsonb`, `pause_count int`, `longest_pause_ms int`, `pause_ratio numeric`, `pitch_variance numeric`, `energy_variance numeric`, `hedge_count int`, `sentence_count int`, `avg_sentence_len numeric`, `time_to_first_word_ms int`
* **`turn_scores`** — `turn_id`, `rubric_version`, `relevance numeric`, `correctness numeric`, `structure numeric`, `grounding numeric`, `specificity numeric`, `conciseness numeric`, `star_completeness jsonb ({situation:bool, task:bool, action:bool, result:bool})`, `overall numeric`, `rationale text`, `model_used`, `scored_at`
* **`session_claims`** — `session_id`, `turn_id`, `claim_text`, `supported boolean`, `source_chunk_id fk nullable`, `source_project_id fk nullable`, `confidence numeric`, `contradiction_of_claim_id fk nullable`
  * > **NOTE**: This table powers two features: provenance display, and claim-consistency detection ("in turn 3 you said 100k rows; in turn 7 you said 1M rows").
* **`study_items` + `study_reviews`** — SM-2 spaced repetition.
  * **`study_items`**: `candidate_id`, `topic`, `source (weak_answer|missed_concept|jd_gap|manual)`, `source_turn_id nullable`, `prompt`, `reference_answer`, `difficulty`, `ease_factor numeric default 2.5`, `interval_days int default 1`, `next_review_at`.
  * **`study_reviews`**: `item_id`, `reviewed_at`, `quality int (0–5)`, `new_interval_days`, `new_ease_factor`
* **`provider_health`** — `provider`, `capability`, `state (closed|open|half_open)`, `last_success_at`, `last_failure_at`, `consecutive_failures`, `latency_p50_ms`, `latency_p95_ms`, `latency_p99_ms`, `error_rate`, `rate_limited_until`, `checked_at`
* **`usage_events`** — `user_id`, `session_id nullable`, `provider`, `model`, `capability`, `input_tokens`, `output_tokens`, `audio_seconds`, `image_count`, `request_count`, `estimated_cost_usd numeric default 0`, `was_free_tier boolean`, `latency_ms`, `fell_back_from nullable`
  * > **NOTE**: Build this from Phase 4 even while every value reads 0. Its purpose is to make cost real from measured data rather than guessed at, and to answer "what happens when we outgrow the free tier?" with a number instead of a shrug.

## 4.3 Row Level Security

Every candidate-owned table gets, at minimum:

```sql
alter table <t> enable row level security;

create policy "<t>_select_own" on <t> for select
  using (auth.uid() = (select user_id from candidates where id = <t>.candidate_id));

create policy "<t>_insert_own" on <t> for insert
  with check (auth.uid() = (select user_id from candidates where id = <t>.candidate_id));
-- ... update, delete equivalents
```

Phase 1 must include an automated RLS test that creates two users, has User A attempt to read every one of User B's rows across every table, and asserts zero rows returned. Run it in CI. **RLS that was never tested is RLS that does not work.**
