-- ============
-- HNSW VECTOR INDEX
-- ============
-- HNSW is chosen over IVFFlat because HNSW performs well immediately at small 
-- data volumes (hundreds/thousands of chunks) without requiring a pre-training step.
-- vector_cosine_ops is used to match embedding similarity as cosine distance, 
-- suitable for normalized models like bge-small.

create index if not exists idx_document_chunks_embedding
  on document_chunks
  using hnsw (embedding vector_cosine_ops);

-- ============
-- GIN FULL-TEXT INDEX
-- ============
-- Targets the stored generated content_tsv column. Required for hybrid retrieval
-- to avoid full table scans on exact keyword searches.

create index if not exists idx_document_chunks_content_tsv
  on document_chunks 
  using gin (content_tsv);

-- ============
-- SUPPORTING B-TREE INDEXES
-- ============

create index if not exists idx_candidate_projects_candidate_id
  on candidate_projects (candidate_id);

create index if not exists idx_session_turns_session_id
  on session_turns (session_id);

create index if not exists idx_session_turns_parent_turn_id
  on session_turns (parent_turn_id);

-- Note: turn_scores.turn_id is already covered by a UNIQUE constraint index,
-- but we create it explicitly for clarity or in case the unique constraint changes.
create index if not exists idx_turn_scores_turn_id
  on turn_scores (turn_id);

create index if not exists idx_session_claims_session_id
  on session_claims (session_id);

-- Composite index for study loop ordering
create index if not exists idx_study_items_candidate_next_review
  on study_items (candidate_id, next_review_at);

-- Composite index for usage analytics
create index if not exists idx_usage_events_profile_created
  on usage_events (profile_id, created_at);
