# Privacy Data Map

Maps every category of personal data PRAXIS collects to its purpose, legal basis,
storage location, retention period, and deletion path.

Regulatory scope: GDPR (EU/UK), CCPA (California).
Last reviewed: 2026-10-05

---

## Data inventory

### 1. Identity data

| Field | Source | Purpose | Legal basis | Table | Retention |
|-------|--------|---------|-------------|-------|-----------|
| Email address | Supabase Auth registration | Authentication | Contract | `auth.users` (Supabase-managed) | Until account deletion |
| Display name | Profile setup | Personalisation | Contract | `candidates.full_name` | Until deletion |
| Headline | Profile setup | Resume builder context | Contract | `candidates.headline` | Until deletion |

### 2. Career data (user-provided)

| Category | Purpose | Legal basis | Tables | Retention |
|----------|---------|-------------|--------|-----------|
| Work experiences | Practice session context; resume builder | Contract | `candidate_experiences` | Until deletion |
| Projects | Same + embeddings for RAG | Contract | `candidate_projects`, `document_chunks` | Until deletion |
| Skills | Readiness scoring | Contract | `candidate_skills`, `skills` | Until deletion |
| Uploaded resumes | Document parsing; skills extraction | Contract | `documents`, `document_chunks` (GCS blob) | Until deletion or `data_retention_days` |
| STAR stories | Behavioral practice | Contract | `stories` | Until deletion |
| Job descriptions (uploaded) | Personalised coaching | Contract | `jobs`, `job_blueprints` | Until deletion |

### 3. Session and performance data

| Category | Purpose | Legal basis | Tables | Retention |
|----------|---------|-------------|--------|-----------|
| Session transcripts | Debrief generation; coaching | Contract | `transcript_segments`, `session_state_log` | `data_retention_days` (default 365 days) |
| Session scores | Readiness tracking | Contract | `practice_sessions`, `candidate_readiness` | Until deletion |
| Coding session state | In-session progress | Contract | `coding_session_state`, `coding_test_run_results` | Cascades with session deletion |

### 4. AI-derived data

| Category | Source | Purpose | Legal basis | Tables | Retention |
|----------|--------|---------|-------------|--------|-----------|
| Document embeddings | BAAI/bge-small-en-v1.5 | Semantic search | Contract | `document_chunks.embedding` | Until parent document deletion |
| Extracted resume facts | LLM extraction | Skill mapping | Contract | `resume_claims`, `resume_versions` | Until resume deletion |
| Session debriefs | LLM summarisation | Learning feedback | Contract | `session_debriefs` | Until session deletion |
| JD requirement graph | LLM extraction | Preparation planning | Contract | `jd_requirement_graph` | Until job deletion |

### 5. System / operational data

| Category | Purpose | Legal basis | Location | Retention |
|----------|---------|-------------|----------|-----------|
| AI call logs (user_id, latency, token counts — no content) | Abuse monitoring; billing | Legitimate interest | `ai_call_log` | 90 days |
| Privacy/consent events | Regulatory audit | Legal obligation | `privacy_events` | Permanent |
| Worker dead letters (sanitised) | Incident response | Legitimate interest | `failed_jobs` | 30 days |
| Data export records | GDPR access-request audit | Legal obligation | `candidate_data_exports` | `expires_at` + 7 days |
| Deletion jobs | GDPR erasure audit | Legal obligation | `deletion_jobs` | Permanent |

---

## Legal bases (GDPR)

| Basis | Used for |
|-------|---------|
| **Contract (Art. 6(1)(b))** | All core product features: coaching, scoring, resume builder, session storage |
| **Legal obligation (Art. 6(1)(c))** | Consent audit trail, deletion audit trail |
| **Legitimate interest (Art. 6(1)(f))** | Operational logs (no personal content), abuse monitoring |

---

## Data subject rights

| Right | Mechanism | Latency |
|-------|-----------|---------|
| Access | `POST /api/v1/export` → JSON archive | Async; ready within minutes |
| Deletion (erasure) | `DELETE /api/v1/candidates/me` → `delete_candidate_account_job` | Async; 24 h SLO |
| Rectification | Profile edit endpoints | Synchronous |
| Restriction | `data_retention_days` setting in `user_settings` | Effective next retention cron run |
| Portability | Same JSON archive as Access right | Async |

---

## Third-party data sharing

| Recipient | Data shared | Purpose | Safeguard |
|-----------|-------------|---------|-----------|
| LLM provider (API calls) | Candidate document text (chunked, not PII-identified) | AI coaching | Data processor agreement; model configured not to train on data |
| Supabase | Auth tokens, email | Authentication | DPA; SOC 2 certified |
| Google Cloud Platform | All backend data (processing) | Infrastructure | DPA; ISO 27001 certified |

**No data is sold to third parties.**

---

## Data residency

All backend infrastructure is provisioned in a single GCP region (configurable, default `us-central1`).
No cross-region replication by default. See `infra/gcp/environments/production/terraform.tfvars`.
