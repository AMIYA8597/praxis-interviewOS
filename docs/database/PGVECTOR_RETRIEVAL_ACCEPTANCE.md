# PRAXIS InterviewOS — pgvector & RAG Retrieval Acceptance Report

**Document Version:** 1.0.0  
**Audit Date:** 2026-11-04  

---

## 1. Vector Search Architecture

PRAXIS InterviewOS implements dense vector embeddings and hybrid search directly inside PostgreSQL:
1. **Embedding Dimension:** `384` dimensions (`vector(384)`).
2. **Local Model:** `BAAI/bge-small-en-v1.5` executed locally on CPU/ONNX (zero network latency, zero per-token cost, zero data leakage).
3. **Index Type:** HNSW (Hierarchical Navigable Small World) index with cosine distance (`vector_cosine_ops`):
   ```sql
   CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding 
   ON document_chunks USING hnsw (embedding vector_cosine_ops)
   WITH (m = 16, ef_construction = 64);
   ```
4. **Full-Text Index:** PostgreSQL `tsvector` with GIN indexing on chunk contents for hybrid lexical + semantic search.

---

## 2. Retrieval Grounding & Tenant Isolation

1. **Scoped Candidate Filtering:** All vector retrieval queries enforce an explicit `candidate_id` filter joined through `documents` and `document_chunks`.
2. **Grounding Traceability:** Spoken turns evaluate candidate claims against top-k retrieved chunks, attaching exact `chunk_id`, text excerpt, and similarity distance to the recorded evaluation.
3. **Deduplication:** Hashing of document chunk contents prevents duplicate chunk insertions when re-processing resumes.
