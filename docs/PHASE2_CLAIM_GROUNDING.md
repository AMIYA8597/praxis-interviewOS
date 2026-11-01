# PRAXIS InterviewOS — Phase 2 Claim Grounding & Evidence Engine

**Date**: 2026-11-01  
**Project**: PRAXIS InterviewOS (`AMIYA8597/praxis-interviewOS`)  
**Workstream**: WORKSTREAM F — CLAIM GROUNDING AND EVIDENCE ENGINE  
**Classification**: PRODUCTION ARCHITECTURE SPECIFICATION  

---

## 1. 5-Tier Claim Classification System

Candidate interview statements are parsed into discrete factual assertions and verified against the candidate's background document knowledge base:

```
[Candidate Spoken Answer]
         │
         ▼
[Claim Extraction] (PromptBuilder + fast_classify)
         │
         ▼
[Hybrid RAG Grounding] (vector + tsvector lexical)
         │
         ▼
[5-Tier Entailment Evaluation]
   ├── SUPPORTED: Direct factual evidence corroborates claim (Confidence >= 0.85)
   ├── PARTIALLY_SUPPORTED: Core claim aligns with facts, but scale/metrics are exaggerated
   ├── UNSUPPORTED: No corroborating evidence in candidate documents (Never upgraded silently)
   ├── CONTRADICTED: Statement directly conflicts with document evidence or prior session claims
   └── UNCERTAIN: Ambiguous wording, vague timeline, or insufficient context
```

---

## 2. Provenance Tracking & Character Offsets

Every verified claim links directly to its source provenance:
- `claim_text`: The extracted factual statement.
- `classification`: One of the 5 canonical tiers (`SUPPORTED`, `PARTIALLY_SUPPORTED`, `UNSUPPORTED`, `CONTRADICTED`, `UNCERTAIN`).
- `source_chunk_id`: UUID of the backing `document_chunks` record.
- `source_project_id`: UUID of the associated `candidate_projects` entry.
- `source_excerpt`: Exact substring from the source document backing the classification.
- `confidence`: Calibrated model probability $[0.0, 1.0]$.
- `contradiction_of_claim_id`: UUID of any earlier session claim contradicted by this assertion.

---

## 3. Contradiction Engine

The session consistency engine maintains a running window of factual assertions made throughout the interview session:
- Detects intra-session flip-flopping (e.g., claiming to have built a system in Rust on Turn 2, then claiming Python on Turn 5).
- Detects cross-document contradictions (e.g., claiming 10,000 QPS on a project whose architectural specification records 500 QPS).
- Immediately flags contradiction in `session_claims.contradiction_of_claim_id` without breaking the live conversational flow.
