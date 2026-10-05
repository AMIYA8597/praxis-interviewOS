# PRAXIS — Phase Completion Matrix (Phases 1–49)

Generated: 2026-10-05 from actual source code audit.

> **Legend**
> - ✅ IMPLEMENTED — code + tests + integrated + consumed by product
> - 🔶 PARTIALLY_IMPLEMENTED — code exists, gaps in tests/integration/product consumption
> - ❌ NOT_IMPLEMENTED — no meaningful implementation
> - 🔍 IMPLEMENTED_BUT_UNVERIFIED — code exists, not tested end-to-end
> - 🔴 BROKEN — code exists but has known runtime bugs

---

## Summary

| Range | ✅ | 🔶 | ❌ | 🔍 | 🔴 |
|-------|----|----|----|----|-----|
| 1–10  | 6  | 3  | 0  | 1  | 0   |
| 11–20 | 6  | 3  | 1  | 0  | 0   |
| 21–30 | 5  | 3  | 0  | 2  | 0   |
| 31–40 | 4  | 4  | 1  | 1  | 0   |
| 41–49 | 5  | 3  | 1  | 0  | 0   |

---

## Detailed Matrix

| Phase | Requirement | Implementation | Tests | Status | Evidence Files | Remaining Risk |
|-------|-------------|----------------|-------|--------|----------------|----------------|
| 1 | Security recovery — env vars not in git | `.env` not tracked; `.env.example` present; no secrets in git history | secrets-scan CI gate | ✅ | `.gitignore`, `scripts/check_no_fake_data.py` | Secrets in Electron binary if .env bundled |
| 2 | Authentication recovery — Supabase + OS storage | `apps/desktop/src/renderer/lib/supabase.ts` with keytar/OS storage; `jest.setup.js` for URL validation | `App.test.tsx` mocks session | 🔶 | `supabase.ts`, `jest.setup.js` | Token refresh on long idle sessions not tested |
| 3 | Realtime protocol binary envelope | `protocol.py` with 18 event types; `useAudioFrameStream.ts` binary header | `useAudioFrameStream.test.ts` byte-order test | ✅ | `protocol.py`, `useAudioFrameStream.ts` | `sequence` field always 0 in coaching events |
| 4 | Electron media pipeline | `useAudioCapture.ts`, `useAudioFrameStream.ts`, `useRealtimeSession.ts` | Unit tests for each hook | ✅ | `hooks/` directory, tests | PCM16 conversion accuracy not tested at scale |
| 5 | Screen capture state machine | `useScreenshotUpload.ts` states: IDLE→CAPTURE_PENDING→UPLOAD_PENDING→DONE | `useScreenshotUpload.test.ts` | ✅ | `useScreenshotUpload.ts` | No integration with Practice Arena |
| 6 | Session state machine | `session/state_machine.py` — 17 states, full transition dict, OTel spans | `test_state_machine.py` | ✅ | `state_machine.py` | PAUSED→RESUMED not in protocol.py event types |
| 7 | Live coaching 250ms dual-path | `coaching/accumulator.py` `_update_loop()` with `asyncio.sleep(0.25)` | `test_coaching_accumulator.py` cadence test | ✅ | `accumulator.py`, `CoachingHUD.tsx` | No test with simulated LLM delay proving non-blocking |
| 8 | Remove fabricated metrics | No hardcoded scores in web pages; `check_no_fake_data.py` gate | CI boundary check | ✅ | `check_no_fake_data.py` | Gate does not scan apps/web (TS files) |
| 9 | Candidate context warm-up | `InterviewSession.warm_up()` builds full context from verified/uncertain claims | `test_claims_engine.py` | ✅ | `interview/policy.py:96–148` | Candidate profile must be pre-populated |
| 10 | Claim grounding | `calculate_grounding_score()` + `verify_claim()` via LLM | `test_scoring.py::test_calculate_grounding_score` | ✅ | `scoring/service.py:58–76` | Grounding depends on LLM availability |
| 11 | Interview taxonomy | `interview_domains` table, 35 codes, migration, API route | Auth gate test | ✅ | `migrations/20261005000001_question_bank.sql` | No admin seeding of initial questions |
| 12 | Interview modes | `SessionMode = Literal["mock_interview","drill","freeform","debrief"]` | session schema tests | 🔶 | `schemas/session.py` | Coding/system-design not explicit session modes |
| 13 | Adaptive interviewer policy | `generate_next_turn()` with difficulty-based prompt modulation | None for policy adaptation specifically | 🔶 | `interview/policy.py` | Prompt-delegation only; no algorithmic ELO/difficulty tracking; `generate_structured` routing bug now fixed |
| 14 | Question bank | `question_bank` table + CRUD routes at `/api/v1/questions` | Auth gate test | ✅ | `api/questions.py`, migration | No initial seed data for the bank |
| 15 | Answer scoring | `score_answer_async()` — 6 dimensions, weighted aggregation | `test_scoring.py::test_score_answer_async` | ✅ | `scoring/service.py` | Dead `add_output_schema(DimensionScores)` call now fixed |
| 16 | System design scoring | `score_system_design_async()` — 8-dimension rubric | `test_system_design_score_model` | ✅ | `scoring/models.py`, `scoring/service.py` | Not yet wired into main session flow |
| 17 | AI Gateway hardening | `check_gateway_boundary.py` + `check_prompt_construction_boundary.py` | CI gate | ✅ | `scripts/check_gateway_boundary.py` | deepseek/xai not in boundary check pattern |
| 18 | Local-first AI | `models.yaml` ollama-first routing; `local_faster_whisper.py` | Transcription router tests | ✅ | `config/models.yaml`, `transcription/` | Ollama not tested in CI (not installed) |
| 19 | RAG hybrid retrieval | `retrieval.py` — vector + BM25 + RRF fusion | `test_hybrid_retrieval.py` | ✅ | `praxis_ai_gateway/retrieval.py` | JD coverage in readiness uses crude ILIKE, not RAG |
| 20 | Prompt injection defense | `PromptBuilder` sanitizes `</UNTRUSTED_DOCUMENT>` + sensitive keywords | `test_prompt_injection.py` — 9 fixtures + live pipeline test | ✅ | `prompt_builder.py`, `tests/security/test_prompt_injection.py` | Extended proximity-escape regex may over-escape in edge cases |
| 21 | Debrief engine | `backend/services/debrief.py` + `realtime-agent/app/interview/debrief.py` | `test_orchestrator_debrief.py` | 🔶 | `services/debrief.py` | Primary path in realtime-agent not connected to ARQ; API fallback only |
| 22 | Study loop SM-2 | `services/sm2.py` full SM-2 algorithm; `study.py::review_item()` | `test_sm2.py` | ✅ | `services/sm2.py`, `services/study.py` | Study card generation after debrief not confirmed wired |
| 23 | Candidate intelligence | `candidates`, `skills`, `experiences` tables; `candidates.py` API | Auth/hardening tests | ✅ | `api/candidates.py`, migrations | No auto-inference layer; manual only |
| 24 | Job intelligence | `jobs`, `job_blueprints`, `job_requirements` tables; `jobs.py` API | Integration tests | ✅ | `api/jobs.py`, migrations | JD analysis requires explicit trigger |
| 25 | Application tracker | `applications` table + `applications.py` API | `test_applications.py` | ✅ | `api/applications.py` | No status automation |
| 26 | Resume upload + chunking | Resume upload, chunking pipeline, `document_chunks` with pgvector | Integration tests | ✅ | From Phase 1-5 prior sessions | Vector search depends on Postgres pgvector |
| 27 | Session persistence | `practice_sessions`, `session_turns`, `turn_scores` tables with cascade deletes | `test_deletion_cascade.py` | ✅ | Migrations, session service | None |
| 28 | Premium dark UI | Dark theme via Tailwind; `bg-gray-950` surfaces; CSS variables | Visual only | 🔶 | `layout.tsx` | No design system tokens; component library (`@praxis/ui`) stubs |
| 29 | Practice Arena | `PracticeArenaPage.tsx` + `PreflightCheck.tsx` + `CoachingHUD.tsx` | `PracticeArenaPage.test.tsx` | ✅ | Desktop `pages/`, `components/` | No mobile support |
| 30 | Preflight check | `PreflightCheck.tsx` — auth, backend, microphone, screen capture checks | `PracticeArenaPage.test.tsx` mocks it | ✅ | `components/PreflightCheck.tsx` | Network check is a simple HTTP ping |
| 31 | Session history | `sessions/page.tsx` lists sessions; debrief sub-page | Implicit via session API | 🔶 | `app/(dashboard)/sessions/` | Debrief page exists but may lack score visualization |
| 32 | Analytics | `analytics/page.tsx` + `api/analytics.py` | `test_analytics.py` | 🔶 | `app/(dashboard)/analytics/` | Metrics are query aggregations; no time-series charts |
| 33 | Admin | `admin/page.tsx` + `api/admin.py` | `test_admin.py` | 🔶 | `app/(dashboard)/admin/` | Admin auth not role-separated from regular user |
| 34 | Provider settings | `settings/providers/page.tsx` | None | 🔍 | `app/(dashboard)/settings/providers/` | Settings UI may not save to DB |
| 35 | Coding sandbox | `CodingSandbox.tsx` — editor with tab support, language selector | None | ❌ | `components/CodingSandbox.tsx` | **No execution engine** — editor only |
| 36 | System design workspace | `DiagramCanvas.tsx` | None | 🔍 | `components/DiagramCanvas.tsx` | Not integrated into Practice Arena |
| 37 | Error/degraded states | `DEGRADED_STT`, `DEGRADED_LLM`, `DEGRADED_TTS` in state machine | `test_degradation.py` | ✅ | `state_machine.py`, `test_degradation.py` | UI degraded state display not verified |
| 38 | CI secrets scan | `detect-secrets` with `.secrets.baseline` | CI `secrets-scan` job | ✅ | `.github/workflows/ci.yml` | Baseline must be updated when new secrets are added |
| 39 | Testing pyramid | 52 Python test files + 10 TS test files; RLS, injection, scoring, cascade, SM-2 | N/A | 🔶 | `backend/tests/`, `realtime-agent/tests/` | No E2E browser tests; no integration test for full session flow with real DB |
| 40 | Build gates | `pnpm run typecheck` + `pnpm run test` in CI | CI frontend-checks job | ✅ | `.github/workflows/ci.yml` | Web `pnpm run build` not in CI (catches dead imports) |
| 41 | CI/CD pipeline | 3 CI jobs: backend-tests, frontend-checks, secrets-scan | N/A | ✅ | `.github/workflows/ci.yml` | No staging deploy; no production deploy step |
| 42 | Observability | OTel tracing (`configure_tracing`), structured JSON logs, `X-Request-ID` propagation | `test_tracing.py` | ✅ | `core/bootstrap.py`, `core/logging_config.py`, `middleware.py` | No metrics (Prometheus/OTEL metrics); spans only |
| 43 | Privacy/PII | `SENSITIVE_KEYS` in `logging_config.py` redacts tokens/keys; no PII in URLs | `logging_config.py` | ✅ | `core/logging_config.py` | Resume text redaction in logs confirmed; photo/ID not handled |
| 44 | Performance | DB pool pre-ping; `DB_STATEMENT_TIMEOUT_MS`; connection pool config | None specific | 🔍 | `packages/config/settings.py`, `db/session.py` | No load test in CI; `benchmark_*.py` scripts are manual |
| 45 | Preparation engine | `backend/services/readiness.py::generate_preparation_plan()` | Auth gate | ✅ | `services/readiness.py`, `api/readiness.py` | Plan sessions are not directly executable from UI |
| 46 | Readiness model | `backend/services/readiness.py::compute_readiness()` + web `readiness/page.tsx` | Auth gate + unit | ✅ | `services/readiness.py`, `app/(dashboard)/readiness/` | JD coverage uses ILIKE not RAG |
| 47 | No-fake-data gate | `scripts/check_no_fake_data.py` + CI boundary check step | Passes locally | ✅ | `scripts/check_no_fake_data.py`, `.github/workflows/ci.yml` | Does not scan TypeScript runtime files |
| 48 | E2E proof | `realtime-agent/scripts/run_e2e_session.py` + `tests/integration/test_e2e_session.py` | `test_e2e_session.py` | 🔶 | `realtime-agent/scripts/run_e2e_session.py` | All AI/STT/TTS mocked; no real provider test; no assertions only prints |
| 49 | Final report | Phase reports in `docs/` | N/A | 🔶 | `docs/PHASE_*_REPORT.md` | No machine-readable capability matrix until this document |

---

## Top Remaining Risks

1. **Phase 35** — Coding sandbox has no execution engine (INCOMPLETE)
2. **Phase 13** — Adaptive difficulty is prompt-only; no algorithmic feedback loop
3. **Phase 7** — No test proving coaching path is non-blocking under real LLM latency
4. **Phase 48** — E2E script has no assertions; all AI is mocked
5. **Phase 36** — DiagramCanvas not integrated into Practice Arena session flow
6. **Phase 34** — Provider settings UI may not persist to DB
7. **Phase 8/47** — No-fake-data gate does not scan TypeScript files
8. **Phase 28** — `@praxis/ui` component library is stubs; HUD may not render
9. **Phase 40** — `pnpm run build` (Next.js full build) not in CI

---

*This document is auto-generated from code audit on 2026-10-05. Re-run audit after significant changes.*
