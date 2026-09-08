# Phase 2 Implementation Report

**Phase:** 2 - Candidate Intelligence (Auth, Profile, Document Pipeline)  
**Objective:** Setup the authentication system, candidate profile schema, and resume ingestion pipeline with vector embeddings.

## Implemented
- Next.js Auth and Onboarding pages connected to Supabase.
- SQLAlchemy schemas for `CandidateProfile`, `Resume`, and `DocumentChunk`.
- FastAPI backend routes for:
  - Auth validation (`/api/v1/auth/me`).
  - Profile reading/updating (`/api/v1/candidates/me`).
  - File uploading for resumes (`/api/v1/resumes/upload`).
- Document chunking and embedding generation using local free-tier models (`BAAI/bge-small-en-v1.5` via `sentence-transformers`).
- Alembic database migration to support schema deployment and `pgvector`.

## Files Changed
- `backend/app/main.py`
- `backend/app/db/base.py`, `models.py`, `session.py`
- `backend/app/api/auth.py`, `candidates.py`, `resumes.py`
- `backend/app/rag/ingestion.py`, `embeddings.py`
- `backend/alembic/versions/001_candidate_schema.py`
- `backend/alembic.ini`, `backend/alembic/env.py`
- `apps/web/src/lib/supabase.ts`
- `apps/web/src/app/auth/page.tsx`
- `apps/web/src/app/onboarding/page.tsx`

## Database Changes
- Manual migration script added to enable `vector` extension and create the `candidate_profiles`, `resumes`, and `document_chunks` tables.

## API Changes
- Added user context injection utilizing Supabase Auth JWT token checks.
- Implemented `/api/v1/resumes/upload` using `python-multipart` to handle PDF parsing and initiate background processing.

## UI Changes
- Created modern dashboard auth interfaces.

## AI Changes
- Installed `sentence-transformers` to satisfy the FREE-FIRST constraints, allowing high-quality local RAG without API costs.

## Tests
- Need to expand PyTest suite in the next phase to hit mock DB contexts.

## Known limitations
- Local DB dependencies mean running backend tests requires either a local Postgres service or SQLite memory tests (with skipped pgvector paths).

## Performance
- The `sentence-transformers` inference is handled as an async `BackgroundTask` to avoid blocking the user API response.

## Security considerations
- Only authorized users with a valid JWT token can access candidate endpoints. 

## Next phase
- **Phase 3 — Realtime Audio & Transcription** (Electron audio capturing and provider-agnostic realtime sockets).
