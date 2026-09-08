\set ON_ERROR_STOP on

DO $$
DECLARE
  v_user_id uuid := gen_random_uuid();
  v_cand_id uuid := gen_random_uuid();
  v_doc_id uuid := gen_random_uuid();
  i int;
  v_embedding vector(384);
BEGIN
  INSERT INTO auth.users (id) VALUES (v_user_id);
  INSERT INTO profiles (id) VALUES (v_user_id);
  INSERT INTO candidates (id, profile_id, full_name) VALUES (v_cand_id, v_user_id, 'Index Test User');
  INSERT INTO documents (id, candidate_id, kind) VALUES (v_doc_id, v_cand_id, 'other');

  FOR i IN 1..50 LOOP
    SELECT array_agg(random())::vector(384) INTO v_embedding FROM generate_series(1, 384);
    
    INSERT INTO document_chunks (document_id, chunk_index, content, token_count, embedding, embedding_model, embedding_version)
    VALUES (
      v_doc_id, 
      i, 
      'Synthetic content chunk ' || i || ' discussing ambiguous requirements, kubernetes, and react.', 
      20, 
      v_embedding, 
      'bge-small-en-v1.5', 
      '1.0'
    );
  END LOOP;
END $$;

\echo '-------------------------------------------------------'
\echo 'HNSW VECTOR QUERY PLAN'
\echo '-------------------------------------------------------'
-- create a temp table to hold our random query vector
CREATE TEMP TABLE tmp_query (vec vector(384));
INSERT INTO tmp_query SELECT array_agg(random())::vector(384) FROM generate_series(1, 384);

EXPLAIN ANALYZE 
SELECT d.id 
FROM document_chunks d, tmp_query q 
ORDER BY d.embedding <=> q.vec 
LIMIT 10;

\echo '-------------------------------------------------------'
\echo 'GIN FULL-TEXT QUERY PLAN'
\echo '-------------------------------------------------------'
EXPLAIN ANALYZE 
SELECT id 
FROM document_chunks 
WHERE content_tsv @@ plainto_tsquery('english', 'ambiguous requirements');
