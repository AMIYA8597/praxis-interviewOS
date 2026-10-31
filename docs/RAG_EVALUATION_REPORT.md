# RAG Evaluation Report

Retrieval-Augmented Generation (RAG) quality for PRAXIS semantic document search.

**Stack:** BAAI/bge-small-en-v1.5 (384-dim) → pgvector HNSW + BM25 FTS hybrid reranking.
**Current status: BLOCKED** — requires Supabase PostgreSQL + real candidate data.
**Date:** 2026-10-05

---

## Architecture

```
User query
    │
    ├─ Dense path ──► bge-small embed ──► pgvector cosine HNSW ──► top-50 chunks
    │
    └─ Sparse path ─► PostgreSQL FTS (BM25 ranking, tsvector) ──► top-50 chunks
                                                       │
                                     Reciprocal Rank Fusion (α=0.7 dense, 0.3 sparse)
                                                       │
                                              top-k (default 5) chunks returned
```

Implemented in: `backend/app/services/memory.py`

---

## Evaluation methodology

### Offline eval (planned)

1. 30 synthetic resume + document fixtures covering DSA, system design, behavioral domains.
2. 60 queries with ground-truth relevant chunks annotated.
3. Metrics: MRR@5, NDCG@5, Recall@10.

### Online eval (planned — requires staging traffic)

1. Track click-through on cited chunks in debrief and study flows.
2. A/B test: dense-only vs. hybrid for retrieval quality.

---

## Target metrics

| Metric | Target | Current |
|--------|--------|---------|
| MRR@5 | ≥ 0.65 | BLOCKED |
| NDCG@5 | ≥ 0.60 | BLOCKED |
| Recall@10 | ≥ 0.80 | BLOCKED |
| p95 retrieval latency | < 200 ms | BLOCKED |

---

## HNSW index configuration

```sql
CREATE INDEX document_chunks_embedding_idx
    ON document_chunks
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
```

- **m = 16**: graph connectivity; higher values improve recall at the cost of index size.
- **ef_construction = 64**: build-time precision; controls index quality.
- **ef_search** (query-time): default 40 via `SET hnsw.ef_search = 40`.

Tuning guidance: If Recall@10 < 0.75, increase `ef_construction` to 128 and `m` to 32.
This doubles index build time but typically recovers 5-10 pp recall.

---

## Hybrid retrieval parameters

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Dense weight α | 0.7 | Dense vectors capture semantic similarity better for technical questions |
| Sparse weight | 0.3 | BM25 handles exact identifier matches (function names, error codes) |
| Top-k | 5 | Balances context window usage vs. recall |
| Chunk size | 512 tokens | Balances context coherence and embedding quality |
| Chunk overlap | 64 tokens | Prevents split sentences from losing context |

---

## Known limitations

1. **Short code snippets:** bge-small poorly distinguishes semantically similar one-liners.
   Mitigation: BM25 sparse path handles exact token matches.
2. **Cross-lingual:** Model is English-only; non-English resumes will have degraded recall.
3. **Domain gap:** bge-small trained on general text; fine-tuning on interview content
   would improve domain-specific recall (future improvement, not blocking).

---

## BLOCKED

All numeric results require:
- Supabase PostgreSQL provisioning (for pgvector HNSW index)
- Real candidate document uploads
- Minimum 1 week of staging traffic
