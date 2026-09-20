-- Missing Indexes added for performance
create index if not exists idx_document_chunks_document_id on document_chunks(document_id);
create index if not exists idx_model_requests_profile_created on model_requests(profile_id, created_at);
create index if not exists idx_practice_sessions_candidate_created on practice_sessions(candidate_id, created_at);
create index if not exists idx_applications_candidate_status on applications(candidate_id, status);
create index if not exists idx_jobs_company_name on jobs(company_name);
create index if not exists idx_provider_health_provider_state on provider_health(provider, state);

