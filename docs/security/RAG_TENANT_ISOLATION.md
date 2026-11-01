# PRAXIS InterviewOS — RAG Retrieval Tenant Isolation Specification

**Milestone**: Phase 4 — Enterprise Security Engineering  
**Branch**: `phase4-security`  
**Date**: 2026-11-01  
**Classification**: VECTOR & RAG SECURITY SPECIFICATION  

---

## 1. Vector Search Threat Analysis

In a Retrieval-Augmented Generation (RAG) system, candidate resumes and project documentation are embedded into vector spaces (`pgvector`). If vector similarity search queries do not strictly isolate embeddings by tenant, Candidate A could retrieve document chunks containing Candidate B's sensitive project details or proprietary company metrics.

---

## 2. Invariant: Multi-Stage Tenant Filtering

PRAXIS enforces tenant isolation at every stage of the RAG pipeline (`packages/ai-gateway/praxis_ai_gateway/retrieval.py`):

```
Candidate Question / Spoken Utterance
                 |
                 v
        Generate Embedding
                 |
                 v
+=======================================================================+
| Dense Vector Search (pgvector cosine similarity)                      |
|                                                                       |
| SELECT chunk_id, content, 1 - (embedding <=> :query_vec) AS score    |
| FROM document_chunks                                                  |
| WHERE candidate_id = :authenticated_candidate_id                      |
| ORDER BY embedding <=> :query_vec LIMIT 20;                           |
+=======================================================================+
                 |
                 v
+=======================================================================+
| Sparse Lexical Search (PostgreSQL ts_rank_cd)                         |
|                                                                       |
| SELECT chunk_id, content, ts_rank_cd(tsv, plainto_tsquery(:query))    |
| FROM document_chunks                                                  |
| WHERE candidate_id = :authenticated_candidate_id                      |
| ORDER BY rank DESC LIMIT 20;                                          |
+=======================================================================+
                 |
                 v
+=======================================================================+
| Reciprocal Rank Fusion (RRF) & Merging                                |
| - Drops any chunk lacking valid candidate_id verification             |
| - Verifies parent document ownership in documents table              |
+=======================================================================+
                 |
                 v
Top-K Chunks Scoped Exclusively to Authenticated Candidate
```

---

## 3. Storage & Background Embedding Isolation
- **Document Chunk Ingestion**: Ingested chunks in the `document_chunks` table inherit `candidate_id` directly from the parent `documents` row.
- **RLS on `document_chunks`**: The `document_chunks` table has Row Level Security enabled, ensuring direct SQL queries without `WHERE candidate_id = ...` fail closed and return 0 rows for other users.
- **Cache Isolation**: Any retrieval cache keys in Redis incorporate the candidate ID: `rag:cache:{candidate_id}:{query_hash}`.
