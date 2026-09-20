import os

sql = """-- ============
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
"""

standard_tables = {
    'profiles': 'id = auth.uid()',
    'provider_configs': 'profile_id = auth.uid()',
    'model_requests': 'profile_id = auth.uid()',
    'usage_events': 'profile_id = auth.uid()',
    'notifications': 'profile_id = auth.uid()',
    'shortcuts': 'profile_id = auth.uid()',
    'deletion_jobs': 'profile_id = auth.uid()',
    
    'candidates': 'profile_id = auth.uid()',
    'user_settings': 'candidate_id in (select id from candidates where profile_id = auth.uid())',
    'candidate_skills': 'candidate_id in (select id from candidates where profile_id = auth.uid())',
    'candidate_experiences': 'candidate_id in (select id from candidates where profile_id = auth.uid())',
    'candidate_education': 'candidate_id in (select id from candidates where profile_id = auth.uid())',
    'candidate_projects': 'candidate_id in (select id from candidates where profile_id = auth.uid())',
    'stories': 'candidate_id in (select id from candidates where profile_id = auth.uid())',
    'candidate_certifications': 'candidate_id in (select id from candidates where profile_id = auth.uid())',
    'documents': 'candidate_id in (select id from candidates where profile_id = auth.uid())',
    'resumes': 'candidate_id in (select id from candidates where profile_id = auth.uid())',
    'jobs': 'candidate_id in (select id from candidates where profile_id = auth.uid())',
    'job_matches': 'candidate_id in (select id from candidates where profile_id = auth.uid())',
    'practice_sessions': 'candidate_id in (select id from candidates where profile_id = auth.uid())',
    'study_items': 'candidate_id in (select id from candidates where profile_id = auth.uid())',
    'screenshot_tasks': 'candidate_id in (select id from candidates where profile_id = auth.uid())',
    'applications': 'candidate_id in (select id from candidates where profile_id = auth.uid())',
    
    'project_metrics': 'project_id in (select id from candidate_projects where candidate_id in (select id from candidates where profile_id = auth.uid()))',
    'document_chunks': 'document_id in (select id from documents where candidate_id in (select id from candidates where profile_id = auth.uid()))',
    'resume_versions': 'resume_id in (select id from resumes where candidate_id in (select id from candidates where profile_id = auth.uid()))',
    'job_blueprints': 'job_id in (select id from jobs where candidate_id in (select id from candidates where profile_id = auth.uid()))',
    'session_turns': 'session_id in (select id from practice_sessions where candidate_id in (select id from candidates where profile_id = auth.uid()))',
    'session_state_log': 'session_id in (select id from practice_sessions where candidate_id in (select id from candidates where profile_id = auth.uid()))',
    'session_debriefs': 'session_id in (select id from practice_sessions where candidate_id in (select id from candidates where profile_id = auth.uid()))',
    'study_reviews': 'item_id in (select id from study_items where candidate_id in (select id from candidates where profile_id = auth.uid()))',
    'solver_results': 'screenshot_task_id in (select id from screenshot_tasks where candidate_id in (select id from candidates where profile_id = auth.uid()))',
    'application_events': 'application_id in (select id from applications where candidate_id in (select id from candidates where profile_id = auth.uid()))',
    'outreach_drafts': 'application_id in (select id from applications where candidate_id in (select id from candidates where profile_id = auth.uid()))',

    'resume_claims': 'resume_version_id in (select id from resume_versions where resume_id in (select id from resumes where candidate_id in (select id from candidates where profile_id = auth.uid())))',
    'job_requirements': 'job_blueprint_id in (select id from job_blueprints where job_id in (select id from jobs where candidate_id in (select id from candidates where profile_id = auth.uid())))',
    'transcript_segments': 'turn_id in (select id from session_turns where session_id in (select id from practice_sessions where candidate_id in (select id from candidates where profile_id = auth.uid())))',
    'turn_metrics': 'turn_id in (select id from session_turns where session_id in (select id from practice_sessions where candidate_id in (select id from candidates where profile_id = auth.uid())))',
    'turn_scores': 'turn_id in (select id from session_turns where session_id in (select id from practice_sessions where candidate_id in (select id from candidates where profile_id = auth.uid())))',
    'session_claims': 'turn_id in (select id from session_turns where session_id in (select id from practice_sessions where candidate_id in (select id from candidates where profile_id = auth.uid())))',
}

for t, pred in standard_tables.items():
    sql += f"""
-- Table: {t}
alter table {t} enable row level security;
create policy "{t}_select_own" on {t} for select using ({pred});
create policy "{t}_insert_own" on {t} for insert with check ({pred});
create policy "{t}_update_own" on {t} for update using ({pred}) with check ({pred});
create policy "{t}_delete_own" on {t} for delete using ({pred});
"""

sql += """
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
"""

os.makedirs('supabase/migrations', exist_ok=True)
with open('supabase/migrations/20260907235802_enable_rls_policies.sql', 'w', newline='\n', encoding='utf-8') as f:
    f.write(sql)
print("Generated 20260907235802_enable_rls_policies.sql")
