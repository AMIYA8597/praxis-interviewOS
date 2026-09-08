# Privacy & Data Lifecycle

PRAXIS enforces a strict deletion cascade and data retention lifecycle. We do not support "soft deletes" (e.g., `is_deleted = true`) for user-owned operational data; when a user requests deletion, their data is cryptographically and completely wiped from Postgres and object storage.

## The Deletion Cascade Graph

```mermaid
graph TD
    %% Candidates
    Candidate["candidates (Account Deletion)"] -->|Cascade All| PracticeSessions
    Candidate -->|Cascade All| Documents
    Candidate -->|Cascade All| Projects

    %% Documents
    Documents["documents (Resume)"] -->|Cascade| ResumeVersions["resume_versions"]
    Documents -->|Cascade| DocumentChunks["document_chunks"]
    DocumentChunks -->|Cascade| ResumeClaims["resume_claims (via versions)"]
    DocumentChunks -.->|Set Null| SessionClaims1["session_claims.source_chunk_id"]

    %% Projects
    Projects["candidate_projects"] -->|Cascade| ProjectMetrics["project_metrics"]
    Projects -.->|Set Null| Stories["stories.project_id"]
    Projects -.->|Set Null| SessionClaims2["session_claims.source_project_id"]

    %% Practice Sessions
    PracticeSessions["practice_sessions"] -->|Cascade| SessionTurns["session_turns"]
    PracticeSessions -->|Cascade| TranscriptSegments["transcript_segments"]
    PracticeSessions -->|Cascade| TurnMetrics["turn_metrics, turn_scores"]
    PracticeSessions -->|Cascade| SessionState["session_state_log"]
    PracticeSessions -->|Cascade| Debriefs["session_debriefs"]
    PracticeSessions -->|Cascade| SessionClaims["session_claims"]
```

## Retention Policies

Raw audio from realtime sessions is **never persisted** to the database or object storage.
Transcripts (`transcript_segments`) and saved screenshots have a rolling retention window controlled by `user_settings.data_retention_days` (default 30 days). A daily scheduled background job purges older records and logs the event to `privacy_events`.
