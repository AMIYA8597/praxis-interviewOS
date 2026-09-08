-- ============
-- MOCK AUTH SCHEMA (Local Dev Only)
-- ============
-- Since we are running a raw pgvector image in local dev instead of the full 
-- Supabase stack, we need to mock the auth.users table so foreign keys work.

create schema if not exists auth;
create table if not exists auth.users (
  id uuid primary key default gen_random_uuid()
);

-- ============
-- SHARED INFRASTRUCTURE
-- ============

create extension if not exists vector;
create extension if not exists pgcrypto;

create or replace function set_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

-- ============
-- IDENTITY & PROFILE GROUP
-- ============

create table profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create trigger trg_profiles_updated_at before update on profiles for each row execute function set_updated_at();

create table candidates (
  id uuid primary key default gen_random_uuid(),
  profile_id uuid references profiles(id) on delete cascade not null,
  full_name text not null,
  headline text,
  location text,
  years_experience numeric,
  target_roles text[],
  preferred_language text,
  speaking_style jsonb,
  onboarding_step text,
  onboarding_completed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create trigger trg_candidates_updated_at before update on candidates for each row execute function set_updated_at();

create table user_settings (
  id uuid primary key default gen_random_uuid(),
  candidate_id uuid references candidates(id) on delete cascade not null,
  theme text,
  latency_mode text,
  cost_mode text,
  answer_style_default text,
  shortcuts jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create trigger trg_user_settings_updated_at before update on user_settings for each row execute function set_updated_at();

-- ============
-- CANDIDATE BRAIN GROUP
-- ============

create table skills (
  id uuid primary key default gen_random_uuid(),
  name text not null unique,
  category text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create trigger trg_skills_updated_at before update on skills for each row execute function set_updated_at();

create table candidate_skills (
  id uuid primary key default gen_random_uuid(),
  candidate_id uuid references candidates(id) on delete cascade not null,
  skill_id uuid references skills(id) on delete cascade not null,
  proficiency text,
  years_used numeric,
  evidence_source text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(candidate_id, skill_id)
);
create trigger trg_candidate_skills_updated_at before update on candidate_skills for each row execute function set_updated_at();

create table candidate_experiences (
  id uuid primary key default gen_random_uuid(),
  candidate_id uuid references candidates(id) on delete cascade not null,
  company text not null,
  title text not null,
  start_date date not null,
  end_date date,
  description text,
  achievements text[],
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create trigger trg_candidate_experiences_updated_at before update on candidate_experiences for each row execute function set_updated_at();

create table candidate_education (
  id uuid primary key default gen_random_uuid(),
  candidate_id uuid references candidates(id) on delete cascade not null,
  institution text not null,
  degree text not null,
  field text not null,
  start_date date not null,
  end_date date,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create trigger trg_candidate_education_updated_at before update on candidate_education for each row execute function set_updated_at();

create table candidate_projects (
  id uuid primary key default gen_random_uuid(),
  candidate_id uuid references candidates(id) on delete cascade not null,
  experience_id uuid references candidate_experiences(id) on delete cascade,
  name text not null,
  summary text,
  problem text,
  motivation text,
  users_served text,
  architecture text,
  tech_stack text[],
  datasets text,
  data_pipeline text,
  models_used text[],
  training_approach text,
  evaluation_method text,
  metrics jsonb,
  deployment text,
  infra text,
  challenges text,
  failure_cases text,
  tradeoffs text,
  improvements text,
  business_impact text,
  personal_contribution text,
  team_size int,
  duration_months int,
  github_url text,
  demo_url text,
  confidence numeric,
  verified_by_user boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create trigger trg_candidate_projects_updated_at before update on candidate_projects for each row execute function set_updated_at();

create table project_metrics (
  id uuid primary key default gen_random_uuid(),
  project_id uuid references candidate_projects(id) on delete cascade not null,
  metric_name text not null,
  metric_value text not null,
  unit text,
  is_estimate boolean,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create trigger trg_project_metrics_updated_at before update on project_metrics for each row execute function set_updated_at();

create table stories (
  id uuid primary key default gen_random_uuid(),
  candidate_id uuid references candidates(id) on delete cascade not null,
  project_id uuid references candidate_projects(id) on delete set null,
  experience_id uuid references candidate_experiences(id) on delete set null,
  title text not null,
  situation text,
  task text,
  action text,
  result text,
  competency_tags text[],
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create trigger trg_stories_updated_at before update on stories for each row execute function set_updated_at();

create table candidate_certifications (
  id uuid primary key default gen_random_uuid(),
  candidate_id uuid references candidates(id) on delete cascade not null,
  name text not null,
  issuer text not null,
  issue_date date not null,
  expiry_date date,
  credential_url text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create trigger trg_candidate_certifications_updated_at before update on candidate_certifications for each row execute function set_updated_at();

-- ============
-- DOCUMENTS & RETRIEVAL GROUP
-- ============

create table documents (
  id uuid primary key default gen_random_uuid(),
  candidate_id uuid references candidates(id) on delete cascade not null,
  kind text check (kind in ('resume','other')),
  original_filename text,
  storage_path text,
  mime_type text,
  size_bytes bigint,
  processing_status text check (processing_status in ('uploading','parsing','embedding','ready','failed')),
  error_message text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create trigger trg_documents_updated_at before update on documents for each row execute function set_updated_at();

create table resumes (
  id uuid primary key default gen_random_uuid(),
  candidate_id uuid references candidates(id) on delete cascade not null,
  document_id uuid references documents(id) on delete cascade not null,
  is_primary boolean default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create trigger trg_resumes_updated_at before update on resumes for each row execute function set_updated_at();

create table resume_versions (
  id uuid primary key default gen_random_uuid(),
  resume_id uuid references resumes(id) on delete cascade not null,
  version_number int,
  label text,
  generated_for_job_id uuid, -- will reference jobs(id) below via alter table
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create trigger trg_resume_versions_updated_at before update on resume_versions for each row execute function set_updated_at();

create table resume_claims (
  id uuid primary key default gen_random_uuid(),
  resume_version_id uuid references resume_versions(id) on delete cascade not null,
  claim_text text not null,
  claim_type text check (claim_type in ('skill','metric','role','project','education','certification')),
  page int,
  char_start int,
  char_end int,
  extraction_confidence numeric,
  verified_by_user boolean not null default false,
  verified_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create trigger trg_resume_claims_updated_at before update on resume_claims for each row execute function set_updated_at();

create table document_chunks (
  id uuid primary key default gen_random_uuid(),
  document_id uuid references documents(id) on delete cascade not null,
  chunk_index int not null,
  content text not null,
  token_count int,
  embedding vector(384),
  embedding_model text not null,
  embedding_version text not null,
  metadata jsonb default '{}'::jsonb,
  content_tsv tsvector generated always as (to_tsvector('english', content)) stored,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(document_id, chunk_index)
);
create trigger trg_document_chunks_updated_at before update on document_chunks for each row execute function set_updated_at();

-- ============
-- JOB BRAIN GROUP
-- ============

create table jobs (
  id uuid primary key default gen_random_uuid(),
  candidate_id uuid references candidates(id) on delete cascade not null,
  company_name text not null,
  role_title text not null,
  raw_jd_text text,
  seniority_signal text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create trigger trg_jobs_updated_at before update on jobs for each row execute function set_updated_at();

alter table resume_versions add constraint fk_resume_versions_job_id foreign key (generated_for_job_id) references jobs(id) on delete set null;

create table job_blueprints (
  id uuid primary key default gen_random_uuid(),
  job_id uuid references jobs(id) on delete cascade not null unique,
  top_skills jsonb,
  likely_topics text[],
  summary text,
  prep_pack jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create trigger trg_job_blueprints_updated_at before update on job_blueprints for each row execute function set_updated_at();

create table job_requirements (
  id uuid primary key default gen_random_uuid(),
  job_blueprint_id uuid references job_blueprints(id) on delete cascade not null,
  skill_text text not null,
  category text,
  priority text check (priority in ('required','preferred')),
  evidence_quote text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create trigger trg_job_requirements_updated_at before update on job_requirements for each row execute function set_updated_at();

create table job_matches (
  id uuid primary key default gen_random_uuid(),
  job_id uuid references jobs(id) on delete cascade not null unique,
  candidate_id uuid references candidates(id) on delete cascade not null,
  overall_score numeric,
  methodology_version text,
  breakdown jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create trigger trg_job_matches_updated_at before update on job_matches for each row execute function set_updated_at();

-- ============
-- PRACTICE SESSIONS GROUP
-- ============

create table practice_sessions (
  id uuid primary key default gen_random_uuid(),
  candidate_id uuid references candidates(id) on delete cascade not null,
  job_id uuid references jobs(id) on delete cascade,
  mode text check (mode in ('mock_interview','drill','freeform','debrief')),
  interview_type text check (interview_type in ('behavioral','technical','system_design','mixed','screening')),
  difficulty text check (difficulty in ('warmup','standard','senior','stress')),
  language text,
  persona jsonb,
  started_at timestamptz,
  ended_at timestamptz,
  duration_s int,
  turn_count int default 0,
  stt_provider text,
  llm_provider text,
  tts_provider text,
  fallback_count int default 0,
  status text check (status in ('active','completed','abandoned','failed')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create trigger trg_practice_sessions_updated_at before update on practice_sessions for each row execute function set_updated_at();

create table session_turns (
  id uuid primary key default gen_random_uuid(),
  session_id uuid references practice_sessions(id) on delete cascade not null,
  turn_index int not null,
  speaker text check (speaker in ('interviewer','candidate')),
  question_id uuid,
  parent_turn_id uuid references session_turns(id) on delete cascade,
  text text,
  started_at timestamptz,
  ended_at timestamptz,
  duration_ms int,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(session_id, turn_index)
);
create trigger trg_session_turns_updated_at before update on session_turns for each row execute function set_updated_at();

create table transcript_segments (
  id uuid primary key default gen_random_uuid(),
  session_id uuid references practice_sessions(id) on delete cascade not null,
  turn_id uuid references session_turns(id) on delete cascade not null,
  is_interim boolean not null default false,
  text text,
  start_ms int,
  end_ms int,
  confidence numeric,
  language text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create trigger trg_transcript_segments_updated_at before update on transcript_segments for each row execute function set_updated_at();

create table turn_metrics (
  id uuid primary key default gen_random_uuid(),
  turn_id uuid references session_turns(id) on delete cascade not null unique,
  word_count int,
  duration_ms int,
  wpm numeric,
  filler_count int,
  filler_rate numeric,
  filler_breakdown jsonb,
  pause_count int,
  longest_pause_ms int,
  pause_ratio numeric,
  pitch_variance numeric,
  energy_variance numeric,
  hedge_count int,
  sentence_count int,
  avg_sentence_len numeric,
  time_to_first_word_ms int,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create trigger trg_turn_metrics_updated_at before update on turn_metrics for each row execute function set_updated_at();

create table turn_scores (
  id uuid primary key default gen_random_uuid(),
  turn_id uuid references session_turns(id) on delete cascade not null unique,
  rubric_version text,
  relevance numeric,
  correctness numeric,
  structure numeric,
  grounding numeric,
  specificity numeric,
  conciseness numeric,
  star_completeness jsonb,
  overall numeric,
  rationale text,
  model_used text,
  scored_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create trigger trg_turn_scores_updated_at before update on turn_scores for each row execute function set_updated_at();

create table session_claims (
  id uuid primary key default gen_random_uuid(),
  session_id uuid references practice_sessions(id) on delete cascade not null,
  turn_id uuid references session_turns(id) on delete cascade not null,
  claim_text text not null,
  supported boolean,
  source_chunk_id uuid references document_chunks(id) on delete set null,
  source_project_id uuid references candidate_projects(id) on delete set null,
  confidence numeric,
  contradiction_of_claim_id uuid references session_claims(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create trigger trg_session_claims_updated_at before update on session_claims for each row execute function set_updated_at();

create table session_state_log (
  id uuid primary key default gen_random_uuid(),
  session_id uuid references practice_sessions(id) on delete cascade not null,
  from_state text,
  to_state text not null,
  reason text,
  occurred_at timestamptz not null default now(),
  created_at timestamptz not null default now()
);

create table session_debriefs (
  id uuid primary key default gen_random_uuid(),
  session_id uuid references practice_sessions(id) on delete cascade not null unique,
  headline_metrics jsonb,
  strengths text[],
  weaknesses text[],
  flagged_claims jsonb,
  jd_coverage jsonb,
  generated_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create trigger trg_session_debriefs_updated_at before update on session_debriefs for each row execute function set_updated_at();

-- ============
-- STUDY LOOP GROUP
-- ============

create table study_items (
  id uuid primary key default gen_random_uuid(),
  candidate_id uuid references candidates(id) on delete cascade not null,
  topic text not null,
  source text check (source in ('weak_answer','missed_concept','jd_gap','manual')),
  source_turn_id uuid references session_turns(id) on delete cascade,
  prompt text not null,
  reference_answer text,
  difficulty text,
  ease_factor numeric default 2.5,
  interval_days int default 1,
  next_review_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create trigger trg_study_items_updated_at before update on study_items for each row execute function set_updated_at();

create table study_reviews (
  id uuid primary key default gen_random_uuid(),
  item_id uuid references study_items(id) on delete cascade not null,
  reviewed_at timestamptz not null default now(),
  quality int check (quality between 0 and 5),
  new_interval_days int,
  new_ease_factor numeric,
  created_at timestamptz not null default now()
);

-- ============
-- STUDY WORKBENCH, CAREER OPS, PLATFORM, GOVERNANCE GROUPS
-- ============

create table screenshot_tasks (
  id uuid primary key default gen_random_uuid(),
  candidate_id uuid references candidates(id) on delete cascade not null,
  storage_path text not null,
  status text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create trigger trg_screenshot_tasks_updated_at before update on screenshot_tasks for each row execute function set_updated_at();

create table solver_results (
  id uuid primary key default gen_random_uuid(),
  screenshot_task_id uuid references screenshot_tasks(id) on delete cascade not null,
  solution text,
  confidence numeric,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create trigger trg_solver_results_updated_at before update on solver_results for each row execute function set_updated_at();

create table applications (
  id uuid primary key default gen_random_uuid(),
  candidate_id uuid references candidates(id) on delete cascade not null,
  job_id uuid references jobs(id) on delete set null,
  status text,
  applied_at timestamptz,
  deleted_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create trigger trg_applications_updated_at before update on applications for each row execute function set_updated_at();

create table application_events (
  id uuid primary key default gen_random_uuid(),
  application_id uuid references applications(id) on delete cascade not null,
  event_type text,
  event_date timestamptz,
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create trigger trg_application_events_updated_at before update on application_events for each row execute function set_updated_at();

create table outreach_drafts (
  id uuid primary key default gen_random_uuid(),
  application_id uuid references applications(id) on delete cascade not null,
  recipient_name text,
  subject text,
  body text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create trigger trg_outreach_drafts_updated_at before update on outreach_drafts for each row execute function set_updated_at();

create table provider_configs (
  id uuid primary key default gen_random_uuid(),
  profile_id uuid references profiles(id) on delete cascade not null,
  provider text not null,
  api_key_encrypted text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create trigger trg_provider_configs_updated_at before update on provider_configs for each row execute function set_updated_at();

create table provider_health (
  id uuid primary key default gen_random_uuid(),
  provider text not null,
  capability text not null,
  state text check (state in ('closed','open','half_open')),
  last_success_at timestamptz,
  last_failure_at timestamptz,
  consecutive_failures int default 0,
  latency_p50_ms int,
  latency_p95_ms int,
  latency_p99_ms int,
  error_rate numeric,
  rate_limited_until timestamptz,
  checked_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create trigger trg_provider_health_updated_at before update on provider_health for each row execute function set_updated_at();

create table model_requests (
  id uuid primary key default gen_random_uuid(),
  profile_id uuid references profiles(id) on delete set null,
  session_id uuid references practice_sessions(id) on delete set null,
  provider text,
  model text,
  prompt text,
  response text,
  latency_ms int,
  created_at timestamptz not null default now()
);

create table usage_events (
  id uuid primary key default gen_random_uuid(),
  profile_id uuid references profiles(id) on delete cascade not null,
  session_id uuid references practice_sessions(id) on delete set null,
  provider text,
  model text,
  capability text,
  input_tokens int,
  output_tokens int,
  audio_seconds numeric,
  image_count int,
  request_count int,
  estimated_cost_usd numeric default 0,
  was_free_tier boolean,
  latency_ms int,
  fell_back_from text,
  created_at timestamptz not null default now()
);

create table feature_flags (
  id uuid primary key default gen_random_uuid(),
  name text not null unique,
  is_enabled boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create trigger trg_feature_flags_updated_at before update on feature_flags for each row execute function set_updated_at();

create table notifications (
  id uuid primary key default gen_random_uuid(),
  profile_id uuid references profiles(id) on delete cascade not null,
  type text not null,
  message text not null,
  is_read boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create trigger trg_notifications_updated_at before update on notifications for each row execute function set_updated_at();

create table shortcuts (
  id uuid primary key default gen_random_uuid(),
  profile_id uuid references profiles(id) on delete cascade not null,
  action_name text not null,
  keys text[] not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create trigger trg_shortcuts_updated_at before update on shortcuts for each row execute function set_updated_at();

create table audit_logs (
  id uuid primary key default gen_random_uuid(),
  profile_id uuid references profiles(id) on delete set null,
  action text not null,
  resource text,
  details jsonb,
  created_at timestamptz not null default now()
);

create table privacy_events (
  id uuid primary key default gen_random_uuid(),
  profile_id uuid references profiles(id) on delete set null,
  event_type text not null,
  consent_given boolean,
  created_at timestamptz not null default now()
);

create table deletion_jobs (
  id uuid primary key default gen_random_uuid(),
  profile_id uuid references profiles(id) on delete cascade not null,
  status text not null,
  scheduled_for timestamptz,
  completed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create trigger trg_deletion_jobs_updated_at before update on deletion_jobs for each row execute function set_updated_at();

create table admin_users (
  id uuid primary key default gen_random_uuid(),
  profile_id uuid references profiles(id) on delete cascade not null unique,
  role text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create trigger trg_admin_users_updated_at before update on admin_users for each row execute function set_updated_at();
