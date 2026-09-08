-- ============
-- ADMIN HELPER
-- ============
create or replace function is_admin()
returns boolean as $$
  select exists (
    select 1 from admin_users where profile_id = auth.uid()
  );
$$ language sql stable security definer;

-- ============
-- OWNERSHIP RESOLUTION PATTERN
-- ============
-- For tables with a direct `candidate_id` column:
--   candidate_id in (select id from candidates where profile_id = auth.uid())
-- For second-hop tables (e.g. project_metrics -> candidate_projects -> candidates):
--   project_id in (select id from candidate_projects where candidate_id in (...))

-- Table: profiles
alter table profiles enable row level security;
create policy "profiles_select_own" on profiles for select using (id = auth.uid());
create policy "profiles_insert_own" on profiles for insert with check (id = auth.uid());
create policy "profiles_update_own" on profiles for update using (id = auth.uid()) with check (id = auth.uid());
create policy "profiles_delete_own" on profiles for delete using (id = auth.uid());

-- Table: provider_configs
alter table provider_configs enable row level security;
create policy "provider_configs_select_own" on provider_configs for select using (profile_id = auth.uid());
create policy "provider_configs_insert_own" on provider_configs for insert with check (profile_id = auth.uid());
create policy "provider_configs_update_own" on provider_configs for update using (profile_id = auth.uid()) with check (profile_id = auth.uid());
create policy "provider_configs_delete_own" on provider_configs for delete using (profile_id = auth.uid());

-- Table: model_requests
alter table model_requests enable row level security;
create policy "model_requests_select_own" on model_requests for select using (profile_id = auth.uid());
create policy "model_requests_insert_own" on model_requests for insert with check (profile_id = auth.uid());
create policy "model_requests_update_own" on model_requests for update using (profile_id = auth.uid()) with check (profile_id = auth.uid());
create policy "model_requests_delete_own" on model_requests for delete using (profile_id = auth.uid());

-- Table: usage_events
alter table usage_events enable row level security;
create policy "usage_events_select_own" on usage_events for select using (profile_id = auth.uid());
create policy "usage_events_insert_own" on usage_events for insert with check (profile_id = auth.uid());
create policy "usage_events_update_own" on usage_events for update using (profile_id = auth.uid()) with check (profile_id = auth.uid());
create policy "usage_events_delete_own" on usage_events for delete using (profile_id = auth.uid());

-- Table: notifications
alter table notifications enable row level security;
create policy "notifications_select_own" on notifications for select using (profile_id = auth.uid());
create policy "notifications_insert_own" on notifications for insert with check (profile_id = auth.uid());
create policy "notifications_update_own" on notifications for update using (profile_id = auth.uid()) with check (profile_id = auth.uid());
create policy "notifications_delete_own" on notifications for delete using (profile_id = auth.uid());

-- Table: shortcuts
alter table shortcuts enable row level security;
create policy "shortcuts_select_own" on shortcuts for select using (profile_id = auth.uid());
create policy "shortcuts_insert_own" on shortcuts for insert with check (profile_id = auth.uid());
create policy "shortcuts_update_own" on shortcuts for update using (profile_id = auth.uid()) with check (profile_id = auth.uid());
create policy "shortcuts_delete_own" on shortcuts for delete using (profile_id = auth.uid());

-- Table: deletion_jobs
alter table deletion_jobs enable row level security;
create policy "deletion_jobs_select_own" on deletion_jobs for select using (profile_id = auth.uid());
create policy "deletion_jobs_insert_own" on deletion_jobs for insert with check (profile_id = auth.uid());
create policy "deletion_jobs_update_own" on deletion_jobs for update using (profile_id = auth.uid()) with check (profile_id = auth.uid());
create policy "deletion_jobs_delete_own" on deletion_jobs for delete using (profile_id = auth.uid());

-- Table: candidates
alter table candidates enable row level security;
create policy "candidates_select_own" on candidates for select using (profile_id = auth.uid());
create policy "candidates_insert_own" on candidates for insert with check (profile_id = auth.uid());
create policy "candidates_update_own" on candidates for update using (profile_id = auth.uid()) with check (profile_id = auth.uid());
create policy "candidates_delete_own" on candidates for delete using (profile_id = auth.uid());

-- Table: user_settings
alter table user_settings enable row level security;
create policy "user_settings_select_own" on user_settings for select using (candidate_id in (select id from candidates where profile_id = auth.uid()));
create policy "user_settings_insert_own" on user_settings for insert with check (candidate_id in (select id from candidates where profile_id = auth.uid()));
create policy "user_settings_update_own" on user_settings for update using (candidate_id in (select id from candidates where profile_id = auth.uid())) with check (candidate_id in (select id from candidates where profile_id = auth.uid()));
create policy "user_settings_delete_own" on user_settings for delete using (candidate_id in (select id from candidates where profile_id = auth.uid()));

-- Table: candidate_skills
alter table candidate_skills enable row level security;
create policy "candidate_skills_select_own" on candidate_skills for select using (candidate_id in (select id from candidates where profile_id = auth.uid()));
create policy "candidate_skills_insert_own" on candidate_skills for insert with check (candidate_id in (select id from candidates where profile_id = auth.uid()));
create policy "candidate_skills_update_own" on candidate_skills for update using (candidate_id in (select id from candidates where profile_id = auth.uid())) with check (candidate_id in (select id from candidates where profile_id = auth.uid()));
create policy "candidate_skills_delete_own" on candidate_skills for delete using (candidate_id in (select id from candidates where profile_id = auth.uid()));

-- Table: candidate_experiences
alter table candidate_experiences enable row level security;
create policy "candidate_experiences_select_own" on candidate_experiences for select using (candidate_id in (select id from candidates where profile_id = auth.uid()));
create policy "candidate_experiences_insert_own" on candidate_experiences for insert with check (candidate_id in (select id from candidates where profile_id = auth.uid()));
create policy "candidate_experiences_update_own" on candidate_experiences for update using (candidate_id in (select id from candidates where profile_id = auth.uid())) with check (candidate_id in (select id from candidates where profile_id = auth.uid()));
create policy "candidate_experiences_delete_own" on candidate_experiences for delete using (candidate_id in (select id from candidates where profile_id = auth.uid()));

-- Table: candidate_education
alter table candidate_education enable row level security;
create policy "candidate_education_select_own" on candidate_education for select using (candidate_id in (select id from candidates where profile_id = auth.uid()));
create policy "candidate_education_insert_own" on candidate_education for insert with check (candidate_id in (select id from candidates where profile_id = auth.uid()));
create policy "candidate_education_update_own" on candidate_education for update using (candidate_id in (select id from candidates where profile_id = auth.uid())) with check (candidate_id in (select id from candidates where profile_id = auth.uid()));
create policy "candidate_education_delete_own" on candidate_education for delete using (candidate_id in (select id from candidates where profile_id = auth.uid()));

-- Table: candidate_projects
alter table candidate_projects enable row level security;
create policy "candidate_projects_select_own" on candidate_projects for select using (candidate_id in (select id from candidates where profile_id = auth.uid()));
create policy "candidate_projects_insert_own" on candidate_projects for insert with check (candidate_id in (select id from candidates where profile_id = auth.uid()));
create policy "candidate_projects_update_own" on candidate_projects for update using (candidate_id in (select id from candidates where profile_id = auth.uid())) with check (candidate_id in (select id from candidates where profile_id = auth.uid()));
create policy "candidate_projects_delete_own" on candidate_projects for delete using (candidate_id in (select id from candidates where profile_id = auth.uid()));

-- Table: stories
alter table stories enable row level security;
create policy "stories_select_own" on stories for select using (candidate_id in (select id from candidates where profile_id = auth.uid()));
create policy "stories_insert_own" on stories for insert with check (candidate_id in (select id from candidates where profile_id = auth.uid()));
create policy "stories_update_own" on stories for update using (candidate_id in (select id from candidates where profile_id = auth.uid())) with check (candidate_id in (select id from candidates where profile_id = auth.uid()));
create policy "stories_delete_own" on stories for delete using (candidate_id in (select id from candidates where profile_id = auth.uid()));

-- Table: candidate_certifications
alter table candidate_certifications enable row level security;
create policy "candidate_certifications_select_own" on candidate_certifications for select using (candidate_id in (select id from candidates where profile_id = auth.uid()));
create policy "candidate_certifications_insert_own" on candidate_certifications for insert with check (candidate_id in (select id from candidates where profile_id = auth.uid()));
create policy "candidate_certifications_update_own" on candidate_certifications for update using (candidate_id in (select id from candidates where profile_id = auth.uid())) with check (candidate_id in (select id from candidates where profile_id = auth.uid()));
create policy "candidate_certifications_delete_own" on candidate_certifications for delete using (candidate_id in (select id from candidates where profile_id = auth.uid()));

-- Table: documents
alter table documents enable row level security;
create policy "documents_select_own" on documents for select using (candidate_id in (select id from candidates where profile_id = auth.uid()));
create policy "documents_insert_own" on documents for insert with check (candidate_id in (select id from candidates where profile_id = auth.uid()));
create policy "documents_update_own" on documents for update using (candidate_id in (select id from candidates where profile_id = auth.uid())) with check (candidate_id in (select id from candidates where profile_id = auth.uid()));
create policy "documents_delete_own" on documents for delete using (candidate_id in (select id from candidates where profile_id = auth.uid()));

-- Table: resumes
alter table resumes enable row level security;
create policy "resumes_select_own" on resumes for select using (candidate_id in (select id from candidates where profile_id = auth.uid()));
create policy "resumes_insert_own" on resumes for insert with check (candidate_id in (select id from candidates where profile_id = auth.uid()));
create policy "resumes_update_own" on resumes for update using (candidate_id in (select id from candidates where profile_id = auth.uid())) with check (candidate_id in (select id from candidates where profile_id = auth.uid()));
create policy "resumes_delete_own" on resumes for delete using (candidate_id in (select id from candidates where profile_id = auth.uid()));

-- Table: jobs
alter table jobs enable row level security;
create policy "jobs_select_own" on jobs for select using (candidate_id in (select id from candidates where profile_id = auth.uid()));
create policy "jobs_insert_own" on jobs for insert with check (candidate_id in (select id from candidates where profile_id = auth.uid()));
create policy "jobs_update_own" on jobs for update using (candidate_id in (select id from candidates where profile_id = auth.uid())) with check (candidate_id in (select id from candidates where profile_id = auth.uid()));
create policy "jobs_delete_own" on jobs for delete using (candidate_id in (select id from candidates where profile_id = auth.uid()));

-- Table: job_matches
alter table job_matches enable row level security;
create policy "job_matches_select_own" on job_matches for select using (candidate_id in (select id from candidates where profile_id = auth.uid()));
create policy "job_matches_insert_own" on job_matches for insert with check (candidate_id in (select id from candidates where profile_id = auth.uid()));
create policy "job_matches_update_own" on job_matches for update using (candidate_id in (select id from candidates where profile_id = auth.uid())) with check (candidate_id in (select id from candidates where profile_id = auth.uid()));
create policy "job_matches_delete_own" on job_matches for delete using (candidate_id in (select id from candidates where profile_id = auth.uid()));

-- Table: practice_sessions
alter table practice_sessions enable row level security;
create policy "practice_sessions_select_own" on practice_sessions for select using (candidate_id in (select id from candidates where profile_id = auth.uid()));
create policy "practice_sessions_insert_own" on practice_sessions for insert with check (candidate_id in (select id from candidates where profile_id = auth.uid()));
create policy "practice_sessions_update_own" on practice_sessions for update using (candidate_id in (select id from candidates where profile_id = auth.uid())) with check (candidate_id in (select id from candidates where profile_id = auth.uid()));
create policy "practice_sessions_delete_own" on practice_sessions for delete using (candidate_id in (select id from candidates where profile_id = auth.uid()));

-- Table: study_items
alter table study_items enable row level security;
create policy "study_items_select_own" on study_items for select using (candidate_id in (select id from candidates where profile_id = auth.uid()));
create policy "study_items_insert_own" on study_items for insert with check (candidate_id in (select id from candidates where profile_id = auth.uid()));
create policy "study_items_update_own" on study_items for update using (candidate_id in (select id from candidates where profile_id = auth.uid())) with check (candidate_id in (select id from candidates where profile_id = auth.uid()));
create policy "study_items_delete_own" on study_items for delete using (candidate_id in (select id from candidates where profile_id = auth.uid()));

-- Table: screenshot_tasks
alter table screenshot_tasks enable row level security;
create policy "screenshot_tasks_select_own" on screenshot_tasks for select using (candidate_id in (select id from candidates where profile_id = auth.uid()));
create policy "screenshot_tasks_insert_own" on screenshot_tasks for insert with check (candidate_id in (select id from candidates where profile_id = auth.uid()));
create policy "screenshot_tasks_update_own" on screenshot_tasks for update using (candidate_id in (select id from candidates where profile_id = auth.uid())) with check (candidate_id in (select id from candidates where profile_id = auth.uid()));
create policy "screenshot_tasks_delete_own" on screenshot_tasks for delete using (candidate_id in (select id from candidates where profile_id = auth.uid()));

-- Table: applications
alter table applications enable row level security;
create policy "applications_select_own" on applications for select using (candidate_id in (select id from candidates where profile_id = auth.uid()));
create policy "applications_insert_own" on applications for insert with check (candidate_id in (select id from candidates where profile_id = auth.uid()));
create policy "applications_update_own" on applications for update using (candidate_id in (select id from candidates where profile_id = auth.uid())) with check (candidate_id in (select id from candidates where profile_id = auth.uid()));
create policy "applications_delete_own" on applications for delete using (candidate_id in (select id from candidates where profile_id = auth.uid()));

-- Table: project_metrics
alter table project_metrics enable row level security;
create policy "project_metrics_select_own" on project_metrics for select using (project_id in (select id from candidate_projects where candidate_id in (select id from candidates where profile_id = auth.uid())));
create policy "project_metrics_insert_own" on project_metrics for insert with check (project_id in (select id from candidate_projects where candidate_id in (select id from candidates where profile_id = auth.uid())));
create policy "project_metrics_update_own" on project_metrics for update using (project_id in (select id from candidate_projects where candidate_id in (select id from candidates where profile_id = auth.uid()))) with check (project_id in (select id from candidate_projects where candidate_id in (select id from candidates where profile_id = auth.uid())));
create policy "project_metrics_delete_own" on project_metrics for delete using (project_id in (select id from candidate_projects where candidate_id in (select id from candidates where profile_id = auth.uid())));

-- Table: document_chunks
alter table document_chunks enable row level security;
create policy "document_chunks_select_own" on document_chunks for select using (document_id in (select id from documents where candidate_id in (select id from candidates where profile_id = auth.uid())));
create policy "document_chunks_insert_own" on document_chunks for insert with check (document_id in (select id from documents where candidate_id in (select id from candidates where profile_id = auth.uid())));
create policy "document_chunks_update_own" on document_chunks for update using (document_id in (select id from documents where candidate_id in (select id from candidates where profile_id = auth.uid()))) with check (document_id in (select id from documents where candidate_id in (select id from candidates where profile_id = auth.uid())));
create policy "document_chunks_delete_own" on document_chunks for delete using (document_id in (select id from documents where candidate_id in (select id from candidates where profile_id = auth.uid())));

-- Table: resume_versions
alter table resume_versions enable row level security;
create policy "resume_versions_select_own" on resume_versions for select using (resume_id in (select id from resumes where candidate_id in (select id from candidates where profile_id = auth.uid())));
create policy "resume_versions_insert_own" on resume_versions for insert with check (resume_id in (select id from resumes where candidate_id in (select id from candidates where profile_id = auth.uid())));
create policy "resume_versions_update_own" on resume_versions for update using (resume_id in (select id from resumes where candidate_id in (select id from candidates where profile_id = auth.uid()))) with check (resume_id in (select id from resumes where candidate_id in (select id from candidates where profile_id = auth.uid())));
create policy "resume_versions_delete_own" on resume_versions for delete using (resume_id in (select id from resumes where candidate_id in (select id from candidates where profile_id = auth.uid())));

-- Table: job_blueprints
alter table job_blueprints enable row level security;
create policy "job_blueprints_select_own" on job_blueprints for select using (job_id in (select id from jobs where candidate_id in (select id from candidates where profile_id = auth.uid())));
create policy "job_blueprints_insert_own" on job_blueprints for insert with check (job_id in (select id from jobs where candidate_id in (select id from candidates where profile_id = auth.uid())));
create policy "job_blueprints_update_own" on job_blueprints for update using (job_id in (select id from jobs where candidate_id in (select id from candidates where profile_id = auth.uid()))) with check (job_id in (select id from jobs where candidate_id in (select id from candidates where profile_id = auth.uid())));
create policy "job_blueprints_delete_own" on job_blueprints for delete using (job_id in (select id from jobs where candidate_id in (select id from candidates where profile_id = auth.uid())));

-- Table: session_turns
alter table session_turns enable row level security;
create policy "session_turns_select_own" on session_turns for select using (session_id in (select id from practice_sessions where candidate_id in (select id from candidates where profile_id = auth.uid())));
create policy "session_turns_insert_own" on session_turns for insert with check (session_id in (select id from practice_sessions where candidate_id in (select id from candidates where profile_id = auth.uid())));
create policy "session_turns_update_own" on session_turns for update using (session_id in (select id from practice_sessions where candidate_id in (select id from candidates where profile_id = auth.uid()))) with check (session_id in (select id from practice_sessions where candidate_id in (select id from candidates where profile_id = auth.uid())));
create policy "session_turns_delete_own" on session_turns for delete using (session_id in (select id from practice_sessions where candidate_id in (select id from candidates where profile_id = auth.uid())));

-- Table: session_state_log
alter table session_state_log enable row level security;
create policy "session_state_log_select_own" on session_state_log for select using (session_id in (select id from practice_sessions where candidate_id in (select id from candidates where profile_id = auth.uid())));
create policy "session_state_log_insert_own" on session_state_log for insert with check (session_id in (select id from practice_sessions where candidate_id in (select id from candidates where profile_id = auth.uid())));
create policy "session_state_log_update_own" on session_state_log for update using (session_id in (select id from practice_sessions where candidate_id in (select id from candidates where profile_id = auth.uid()))) with check (session_id in (select id from practice_sessions where candidate_id in (select id from candidates where profile_id = auth.uid())));
create policy "session_state_log_delete_own" on session_state_log for delete using (session_id in (select id from practice_sessions where candidate_id in (select id from candidates where profile_id = auth.uid())));

-- Table: session_debriefs
alter table session_debriefs enable row level security;
create policy "session_debriefs_select_own" on session_debriefs for select using (session_id in (select id from practice_sessions where candidate_id in (select id from candidates where profile_id = auth.uid())));
create policy "session_debriefs_insert_own" on session_debriefs for insert with check (session_id in (select id from practice_sessions where candidate_id in (select id from candidates where profile_id = auth.uid())));
create policy "session_debriefs_update_own" on session_debriefs for update using (session_id in (select id from practice_sessions where candidate_id in (select id from candidates where profile_id = auth.uid()))) with check (session_id in (select id from practice_sessions where candidate_id in (select id from candidates where profile_id = auth.uid())));
create policy "session_debriefs_delete_own" on session_debriefs for delete using (session_id in (select id from practice_sessions where candidate_id in (select id from candidates where profile_id = auth.uid())));

-- Table: study_reviews
alter table study_reviews enable row level security;
create policy "study_reviews_select_own" on study_reviews for select using (item_id in (select id from study_items where candidate_id in (select id from candidates where profile_id = auth.uid())));
create policy "study_reviews_insert_own" on study_reviews for insert with check (item_id in (select id from study_items where candidate_id in (select id from candidates where profile_id = auth.uid())));
create policy "study_reviews_update_own" on study_reviews for update using (item_id in (select id from study_items where candidate_id in (select id from candidates where profile_id = auth.uid()))) with check (item_id in (select id from study_items where candidate_id in (select id from candidates where profile_id = auth.uid())));
create policy "study_reviews_delete_own" on study_reviews for delete using (item_id in (select id from study_items where candidate_id in (select id from candidates where profile_id = auth.uid())));

-- Table: solver_results
alter table solver_results enable row level security;
create policy "solver_results_select_own" on solver_results for select using (screenshot_task_id in (select id from screenshot_tasks where candidate_id in (select id from candidates where profile_id = auth.uid())));
create policy "solver_results_insert_own" on solver_results for insert with check (screenshot_task_id in (select id from screenshot_tasks where candidate_id in (select id from candidates where profile_id = auth.uid())));
create policy "solver_results_update_own" on solver_results for update using (screenshot_task_id in (select id from screenshot_tasks where candidate_id in (select id from candidates where profile_id = auth.uid()))) with check (screenshot_task_id in (select id from screenshot_tasks where candidate_id in (select id from candidates where profile_id = auth.uid())));
create policy "solver_results_delete_own" on solver_results for delete using (screenshot_task_id in (select id from screenshot_tasks where candidate_id in (select id from candidates where profile_id = auth.uid())));

-- Table: application_events
alter table application_events enable row level security;
create policy "application_events_select_own" on application_events for select using (application_id in (select id from applications where candidate_id in (select id from candidates where profile_id = auth.uid())));
create policy "application_events_insert_own" on application_events for insert with check (application_id in (select id from applications where candidate_id in (select id from candidates where profile_id = auth.uid())));
create policy "application_events_update_own" on application_events for update using (application_id in (select id from applications where candidate_id in (select id from candidates where profile_id = auth.uid()))) with check (application_id in (select id from applications where candidate_id in (select id from candidates where profile_id = auth.uid())));
create policy "application_events_delete_own" on application_events for delete using (application_id in (select id from applications where candidate_id in (select id from candidates where profile_id = auth.uid())));

-- Table: outreach_drafts
alter table outreach_drafts enable row level security;
create policy "outreach_drafts_select_own" on outreach_drafts for select using (application_id in (select id from applications where candidate_id in (select id from candidates where profile_id = auth.uid())));
create policy "outreach_drafts_insert_own" on outreach_drafts for insert with check (application_id in (select id from applications where candidate_id in (select id from candidates where profile_id = auth.uid())));
create policy "outreach_drafts_update_own" on outreach_drafts for update using (application_id in (select id from applications where candidate_id in (select id from candidates where profile_id = auth.uid()))) with check (application_id in (select id from applications where candidate_id in (select id from candidates where profile_id = auth.uid())));
create policy "outreach_drafts_delete_own" on outreach_drafts for delete using (application_id in (select id from applications where candidate_id in (select id from candidates where profile_id = auth.uid())));

-- Table: resume_claims
alter table resume_claims enable row level security;
create policy "resume_claims_select_own" on resume_claims for select using (resume_version_id in (select id from resume_versions where resume_id in (select id from resumes where candidate_id in (select id from candidates where profile_id = auth.uid()))));
create policy "resume_claims_insert_own" on resume_claims for insert with check (resume_version_id in (select id from resume_versions where resume_id in (select id from resumes where candidate_id in (select id from candidates where profile_id = auth.uid()))));
create policy "resume_claims_update_own" on resume_claims for update using (resume_version_id in (select id from resume_versions where resume_id in (select id from resumes where candidate_id in (select id from candidates where profile_id = auth.uid())))) with check (resume_version_id in (select id from resume_versions where resume_id in (select id from resumes where candidate_id in (select id from candidates where profile_id = auth.uid()))));
create policy "resume_claims_delete_own" on resume_claims for delete using (resume_version_id in (select id from resume_versions where resume_id in (select id from resumes where candidate_id in (select id from candidates where profile_id = auth.uid()))));

-- Table: job_requirements
alter table job_requirements enable row level security;
create policy "job_requirements_select_own" on job_requirements for select using (job_blueprint_id in (select id from job_blueprints where job_id in (select id from jobs where candidate_id in (select id from candidates where profile_id = auth.uid()))));
create policy "job_requirements_insert_own" on job_requirements for insert with check (job_blueprint_id in (select id from job_blueprints where job_id in (select id from jobs where candidate_id in (select id from candidates where profile_id = auth.uid()))));
create policy "job_requirements_update_own" on job_requirements for update using (job_blueprint_id in (select id from job_blueprints where job_id in (select id from jobs where candidate_id in (select id from candidates where profile_id = auth.uid())))) with check (job_blueprint_id in (select id from job_blueprints where job_id in (select id from jobs where candidate_id in (select id from candidates where profile_id = auth.uid()))));
create policy "job_requirements_delete_own" on job_requirements for delete using (job_blueprint_id in (select id from job_blueprints where job_id in (select id from jobs where candidate_id in (select id from candidates where profile_id = auth.uid()))));

-- Table: transcript_segments
alter table transcript_segments enable row level security;
create policy "transcript_segments_select_own" on transcript_segments for select using (turn_id in (select id from session_turns where session_id in (select id from practice_sessions where candidate_id in (select id from candidates where profile_id = auth.uid()))));
create policy "transcript_segments_insert_own" on transcript_segments for insert with check (turn_id in (select id from session_turns where session_id in (select id from practice_sessions where candidate_id in (select id from candidates where profile_id = auth.uid()))));
create policy "transcript_segments_update_own" on transcript_segments for update using (turn_id in (select id from session_turns where session_id in (select id from practice_sessions where candidate_id in (select id from candidates where profile_id = auth.uid())))) with check (turn_id in (select id from session_turns where session_id in (select id from practice_sessions where candidate_id in (select id from candidates where profile_id = auth.uid()))));
create policy "transcript_segments_delete_own" on transcript_segments for delete using (turn_id in (select id from session_turns where session_id in (select id from practice_sessions where candidate_id in (select id from candidates where profile_id = auth.uid()))));

-- Table: turn_metrics
alter table turn_metrics enable row level security;
create policy "turn_metrics_select_own" on turn_metrics for select using (turn_id in (select id from session_turns where session_id in (select id from practice_sessions where candidate_id in (select id from candidates where profile_id = auth.uid()))));
create policy "turn_metrics_insert_own" on turn_metrics for insert with check (turn_id in (select id from session_turns where session_id in (select id from practice_sessions where candidate_id in (select id from candidates where profile_id = auth.uid()))));
create policy "turn_metrics_update_own" on turn_metrics for update using (turn_id in (select id from session_turns where session_id in (select id from practice_sessions where candidate_id in (select id from candidates where profile_id = auth.uid())))) with check (turn_id in (select id from session_turns where session_id in (select id from practice_sessions where candidate_id in (select id from candidates where profile_id = auth.uid()))));
create policy "turn_metrics_delete_own" on turn_metrics for delete using (turn_id in (select id from session_turns where session_id in (select id from practice_sessions where candidate_id in (select id from candidates where profile_id = auth.uid()))));

-- Table: turn_scores
alter table turn_scores enable row level security;
create policy "turn_scores_select_own" on turn_scores for select using (turn_id in (select id from session_turns where session_id in (select id from practice_sessions where candidate_id in (select id from candidates where profile_id = auth.uid()))));
create policy "turn_scores_insert_own" on turn_scores for insert with check (turn_id in (select id from session_turns where session_id in (select id from practice_sessions where candidate_id in (select id from candidates where profile_id = auth.uid()))));
create policy "turn_scores_update_own" on turn_scores for update using (turn_id in (select id from session_turns where session_id in (select id from practice_sessions where candidate_id in (select id from candidates where profile_id = auth.uid())))) with check (turn_id in (select id from session_turns where session_id in (select id from practice_sessions where candidate_id in (select id from candidates where profile_id = auth.uid()))));
create policy "turn_scores_delete_own" on turn_scores for delete using (turn_id in (select id from session_turns where session_id in (select id from practice_sessions where candidate_id in (select id from candidates where profile_id = auth.uid()))));

-- Table: session_claims
alter table session_claims enable row level security;
create policy "session_claims_select_own" on session_claims for select using (turn_id in (select id from session_turns where session_id in (select id from practice_sessions where candidate_id in (select id from candidates where profile_id = auth.uid()))));
create policy "session_claims_insert_own" on session_claims for insert with check (turn_id in (select id from session_turns where session_id in (select id from practice_sessions where candidate_id in (select id from candidates where profile_id = auth.uid()))));
create policy "session_claims_update_own" on session_claims for update using (turn_id in (select id from session_turns where session_id in (select id from practice_sessions where candidate_id in (select id from candidates where profile_id = auth.uid())))) with check (turn_id in (select id from session_turns where session_id in (select id from practice_sessions where candidate_id in (select id from candidates where profile_id = auth.uid()))));
create policy "session_claims_delete_own" on session_claims for delete using (turn_id in (select id from session_turns where session_id in (select id from practice_sessions where candidate_id in (select id from candidates where profile_id = auth.uid()))));

-- ============
-- SPECIAL CASE TABLES
-- ============

-- skills
alter table skills enable row level security;
create policy "skills_select_all" on skills for select using (true);
create policy "skills_insert_admin" on skills for insert with check (is_admin());
create policy "skills_update_admin" on skills for update using (is_admin()) with check (is_admin());
create policy "skills_delete_admin" on skills for delete using (is_admin());

-- admin_users
alter table admin_users enable row level security;
create policy "admin_users_select" on admin_users for select using (profile_id = auth.uid() or is_admin());
create policy "admin_users_insert" on admin_users for insert with check (is_admin());
create policy "admin_users_update" on admin_users for update using (is_admin()) with check (is_admin());
create policy "admin_users_delete" on admin_users for delete using (is_admin());

-- audit_logs
alter table audit_logs enable row level security;
create policy "audit_logs_select_admin" on audit_logs for select using (is_admin());

-- privacy_events
alter table privacy_events enable row level security;
create policy "privacy_events_select_admin" on privacy_events for select using (is_admin());

-- provider_health
alter table provider_health enable row level security;
create policy "provider_health_select_all" on provider_health for select using (true);
create policy "provider_health_insert_admin" on provider_health for insert with check (is_admin());
create policy "provider_health_update_admin" on provider_health for update using (is_admin()) with check (is_admin());
create policy "provider_health_delete_admin" on provider_health for delete using (is_admin());

-- feature_flags
alter table feature_flags enable row level security;
create policy "feature_flags_select_all" on feature_flags for select using (true);
create policy "feature_flags_insert_admin" on feature_flags for insert with check (is_admin());
create policy "feature_flags_update_admin" on feature_flags for update using (is_admin()) with check (is_admin());
create policy "feature_flags_delete_admin" on feature_flags for delete using (is_admin());
