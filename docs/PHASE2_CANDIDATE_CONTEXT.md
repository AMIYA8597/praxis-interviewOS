# PRAXIS InterviewOS — Phase 2 Candidate Context Intelligence

**Date**: 2026-11-01  
**Project**: PRAXIS InterviewOS (`AMIYA8597/praxis-interviewOS`)  
**Workstream**: WORKSTREAM B — CANDIDATE CONTEXT INTELLIGENCE  
**Classification**: PRODUCTION ARCHITECTURE SPECIFICATION  

---

## 1. Candidate Fact Model & Provenance Integrity

In PRAXIS, candidate context is grounded strictly in source documents (resumes, project write-ups, GitHub repositories, and verifiable experience claims):

- **Factual Claims vs Inferences**:
  - `candidate_memory.py`: Explicit separation between verified facts (directly corroborated by source text) and AI-generated inferences.
  - Inferences are strictly tagged (`inference: true`) and never elevated to verified facts without explicit candidate confirmation.
- **Source Chunk Provenance**:
  - Every extracted skill, experience, or metric is mapped to its `source_chunk_id` and character span `[start_char, end_char]`.
  - When the AI interviewer refers to candidate projects, it cites the exact source excerpt.
- **Tenant Isolation**:
  - All document chunks in `document_chunks` and `documents` enforce strict PostgreSQL Row Level Security (`tenant_isolation_policy` on `candidate_id`). Cross-candidate data access is physically prevented at the database engine level.

---

## 2. Job Description (JD) Intelligence & Alignment

- **Requirement Extraction**:
  - JDs are parsed into structured competencies: Core Required Skills, Preferred Technologies, Domain Knowledge, Seniority/Scope.
- **Explainable Match Scoring**:
  - Candidate skills and verified project experiences are compared against JD requirements using deterministic coverage scoring and semantic alignment.
  - Generates clear gap identification: Strong Matches, Emerging Skills, and Unverified Gaps.
- **Coverage Modulation in Interviews**:
  - The Question Intelligence Engine tracks which JD competencies have been probed during the interview session, prioritizing uncovered domains in subsequent turns.
