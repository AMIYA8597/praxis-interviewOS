# PRAXIS Production Architecture
**Phase 118 — Final Architecture Document**
**Date:** 2026-10-05

---

## 1. System Architecture

```
                     ┌──────────────────────┐
                     │       VERCEL         │
                     │  Next.js Web App     │
                     │  Dashboard / OS      │
                     └──────────┬───────────┘
                                │ HTTPS
                     ┌──────────▼───────────┐
                     │ GCP External HTTPS   │
                     │ Load Balancer        │
                     │ + Managed TLS        │
                     │ + Cloud Armor WAF    │
                     └──────────┬───────────┘
              ┌─────────────────┼─────────────────┐
              │                 │
        /api/*               /ws/*
              │                 │
    ┌─────────▼──────┐  ┌──────▼──────────┐
    │ Cloud Run API  │  │ Cloud Run       │
    │ praxis-api     │  │ praxis-realtime │
    │ FastAPI/ASGI   │  │ WebSocket       │
    │ 1–10 instances │  │ 1–5 instances   │
    └─────────┬──────┘  └──────┬──────────┘
              └────────┬────────┘
                       │ Private VPC
              ┌────────▼────────┐
              │  Memorystore    │
              │  Redis 7.2      │
              │  (private)      │
              └────────┬────────┘
                       │
              ┌────────▼────────┐
              │ Cloud Run       │
              │ praxis-worker   │
              │ ARQ queue       │
              └────────┬────────┘
                       │
       ┌───────────────┼────────────────────┐
       │               │                    │
┌──────▼───────┐ ┌─────▼──────────┐ ┌──────▼───────┐
│ Supabase     │ │ AI Providers   │ │ Secret        │
│ Postgres     │ │ Groq/Gemini/   │ │ Manager       │
│ pgvector/RLS │ │ local models   │ │               │
│ Auth         │ │ (via Gateway)  │ └───────────────┘
│ Storage      │ └────────────────┘
└──────────────┘

Electron Desktop App connects directly to LB endpoints.
```

---

## 2. Data Flow

```
User request → Vercel → Next.js → apiFetch() → LB → Cloud Run API
→ Auth middleware (JWT verify via JWKS) → DB session → handler → response

Realtime audio:
Electron → Microphone capture → WebSocket → LB → Cloud Run Realtime
→ VAD (silero-vad) → STT (faster-whisper) → dual path:
  Fast path (250ms): coaching metrics → emit to WebSocket
  Slow path: AI Gateway → Groq/Gemini → question/scoring → emit to WebSocket
```

---

## 3. Auth Flow

```
1. User signs in via Supabase Auth (email/password or OAuth)
2. Supabase issues JWT (RS256) signed with project's private key
3. Client sends JWT as Bearer token
4. API: jwt.decode(verify=True, algorithms=["RS256"]) against JWKS endpoint
5. Verified sub → candidate_id resolution
6. DB transaction: SET LOCAL request.jwt.claims = '{"sub": "..."}' 
   (only set AFTER cryptographic verification)
7. RLS policies use auth.uid() which reads from request.jwt.claims
```

---

## 4. RLS Flow

All user tables have:
```sql
ALTER TABLE t ENABLE ROW LEVEL SECURITY;
ALTER TABLE t FORCE ROW LEVEL SECURITY;
CREATE POLICY ... USING (candidate_id = auth.uid());
```

The `request.jwt.claims` value is set ONLY from cryptographically verified tokens.
Never from client-supplied values.

---

## 5. Realtime Flow

```
Client connects → JWT auth → session lookup/create
→ Redis: acquire_session_lock(session_id, instance_id)
→ Load session state from Redis (if reconnecting)
→ Warm up InterviewSession (load prompts, candidate profile)
→ WebSocket message loop:
    audio_bytes → VAD → speech_end → STT → transcript
    → dual-path:
        asyncio.sleep(0.25) coaching fast path
        AI Gateway slow path
    → send interviewer.text or coaching.metrics
→ On close/SIGTERM: save state to Redis, release lock
```

---

## 6. AI Flow

```
All AI calls go through packages/ai-gateway (the ONLY place importing provider SDKs).
Routing:
  1. LOCAL (ollama/local model) — preferred for cost and latency
  2. Groq — cloud fast inference
  3. Gemini — fallback
  4. Degraded mode — if all fail

Each call records to ai_provider_call_log:
  alias, provider, model, latency_ms, input_tokens, output_tokens, cost_usd

Budget guard checks daily and per-session limits before each call.
```

---

## 7. RAG

```
Offline (worker):
  resume upload → extract text → chunk → embed (sentence-transformers) 
  → pgvector upsert → BM25 index update

Online (API):
  query → embed query → vector search (cosine, k=5)
           → BM25 search (k=5)
           → RRF fusion (k=60)
           → top-5 passages → context window
```

---

## 8. Interview State Machine

```
States: IDLE → PREFLIGHT → WARMING → READY → INTERVIEWER_TURN 
        → AWAITING_ANSWER → CANDIDATE_TURN → SCORING → NEXT_TURN 
        → SESSION_END → DEBRIEF → COMPLETED
        
Persistence: current state in Redis (session coordination)
             transitions logged to session_state_log (DB)
```

---

## 9. Worker Architecture

Workers run in Cloud Run with ARQ:
- `process_resume`: parse → embed → store facts
- `generate_debrief`: score all turns → GPT debrief
- `generate_study_cards`: SM-2 card creation
- `update_candidate_memory`: topic facts from session
- `cleanup_audio`: delete audio > 30 days
- `maintenance`: idempotency log cleanup, stale session cleanup

All jobs have idempotency keys (worker_idempotency_log table).

---

## 10. Redis Architecture

```
Keys used:
  praxis:session:{id}:state    — session state blob (TTL 2h)
  praxis:session:{id}:lock     — distributed lock (TTL 30s, heartbeat)
  praxis:session:{id}:seq      — sequence number for dedup (TTL 24h)
  cache:jwks                   — JWKS public key cache (TTL 1h)
  cache:candidate:{id}         — candidate profile cache (TTL 15m)
  arq:queue                    — ARQ job queue

Redis is coordination-only. Database is authoritative.
```

---

## 11. Storage Architecture

```
Supabase Storage (private buckets):
  resumes/     → {candidate_id}/resume_{uuid}.pdf
  documents/   → {candidate_id}/doc_{uuid}.pdf
  audio/       → {session_id}/audio_{turn_id}.opus (deleted after 30 days)

Access:
  Upload: authenticated user, path must start with their uid
  Read: signed URL with 1-hour expiry (generated server-side)
  Delete: owner only, or service role (worker cleanup)
```

---

## 12. Security Boundaries

- Service role key: only in backend environment variables (Secret Manager). Never in browser.
- JWT verification: cryptographic (JWKS/RS256 or HS256 with SUPABASE_JWT_SECRET). Never `decode(verify=False)`.
- RLS: ENABLE + FORCE on every user table. Policies use `auth.uid()`.
- CORS: explicit production origins only. No wildcard.
- Cloud Armor: rate limiting (100 req/60s per IP), SQLi/XSS rules.
- Load balancer ingress only: Cloud Run services set to `INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER`.
- Redis: private VPC, not exposed publicly.
- Postgres: Supabase (not directly accessible except via pooler URL).

---

## 13. Deployment Topology

```
GitHub repo
  ↓
PR + CI (GitHub Actions)
  ↓
Merge to main
  ↓
Cloud Build: build images → push to Artifact Registry (praxis-production project)
  ↓
Deploy to staging (praxis-staging project)
  ↓
Staging E2E
  ↓
Manual promote → Deploy to production (praxis-production project, 10% canary)
  ↓
Monitor 10 min → Promote to 100% or Rollback
```

---

## 14. Failure Modes

| Component | Failure | Behavior |
|-----------|---------|----------|
| AI provider | Unavailable | Gateway falls back to next provider |
| Redis | Unavailable | Session state falls back to DB; lock fails open |
| Database | High latency | Statement timeout (15s) → 503 |
| Supabase | Outage | API returns 503; desktop continues cached session |
| Cloud Run instance | Crash | Load balancer routes to healthy instances |
| WebSocket connection | Drop | RealtimeClient reconnects with backoff |
| STT model | Load failure | Startup fails; instance not served traffic |

---

## 15. Disaster Recovery

- RPO: 24h (Supabase daily backups on paid plan)
- RTO: 2h (restore from backup + redeploy)
- PITR: Enable on paid Supabase plan for RPO < 1h
- Off-site backup: weekly pg_dump to GCS (ARQ scheduled job)
- Backup verified: restore drill required before GA

---

## 16. Scaling Model

| Service | Scale trigger | Min | Max |
|---------|--------------|-----|-----|
| API | Request concurrency | 1 | 10 |
| Realtime | Request concurrency | 1 | 5 |
| Worker | Redis queue depth | 0 | 5 |
| Redis | Fixed (Basic tier) | — | 2GB |
| Postgres | Supabase managed | — | plan limit |

---

## 17. Cost Model

Monthly estimates (varies with usage):
- Cloud Run API: ~$10-50 (request-based, min 1 instance)
- Cloud Run Realtime: ~$20-100 (1 always-on, CPU never idle)
- Cloud Run Workers: ~$5-20 (scale to zero when idle)
- Memorystore Redis: ~$35 (1GB Basic)
- Artifact Registry: ~$1
- Load Balancer: ~$18/month + forwarding rule
- Supabase: $25-$599/month (Pro plan recommended for backups)
- AI providers: governed by daily budget cap ($10/day max)
- Vercel: $0-20/month (Hobby/Pro)

**Total estimated: $120-300/month for moderate usage.**
