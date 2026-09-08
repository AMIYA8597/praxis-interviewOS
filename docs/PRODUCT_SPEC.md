A Realtime, Multimodal AI Interview Coaching & Candidate Intelligence Platform

Windows 11 primary • Electron desktop • Next.js 15 web • Python/FastAPI backend • Supabase Free Tier • Free/local-first AI with BYO provider adapters

How to use this document. It is two things at once:

An engineering mandate. Paste each PHASE N block, in order, into an autonomous coding agent (Claude Code, Codex, Cursor Agent, Antigravity, Warp, Gemini CLI). Each phase assumes the repository state left by the previous one. Do not skip ahead — Phase 6 will not work if Phase 5's audio capability detector was faked.
A portfolio artifact. This file itself goes in docs/ in the repo. Most side projects have no system design document. Recruiters and interviewers notice when one exists, and it gives you a script for explaining the project under pressure.

Verification note — read before writing a single line of code. This spec sits on top of fast-moving third-party surfaces: free-tier quotas, model catalogs, realtime API shapes, and Windows audio APIs. Everything in §3 was accurate to the best of my knowledge as of May 2026, and this document was authored in September 2026. Model IDs, free-tier limits, and endpoint shapes change on their own schedule. Every phase below that touches an external API begins with a mandatory documentation-verification step. A spec that hardcodes a stale model ID is worse than a spec that says "go look it up," because the stale one fails silently at 2 a.m. during your demo.

TABLE OF CONTENTS

PART 0 — Positioning, scope, and why this shape wins PART 1 — Product definition PART 2 — System design PART 3 — Free-first tool map and verification protocol PART 4 — Data model PART 5 — Security, privacy, and abuse-resistance PART 6 — The phased build prompts (Phase 0 → Phase 14) PART 7 — Testing, evaluation, and benchmarking PART 8 — Hackathon demo script PART 9 — Resume and interview write-up PART 10 — Appendices

PART 0 — POSITIONING, SCOPE, AND WHY THIS SHAPE WINS
0.1 One-line description

PRAXIS is a realtime AI interview coach. It runs a live, voice-driven mock interview on your desktop with sub-second turn-taking, listens to your answers as you speak them, grounds every piece of feedback in your actual resume and projects, and produces a measured debrief with a spaced-repetition study plan. It runs entirely on free tiers and local models, and fails over across five AI providers.

0.2 The scope decision, stated explicitly

There are two products you could build with a realtime audio pipeline and a candidate knowledge graph:

	Answer-feeding copilot	PRAXIS (this spec)
Listens to	The interviewer, in a real interview	The candidate, in a practice session
Output	An answer to read aloud	Coaching, scoring, and a study plan
Who is deceived	The employer	Nobody
Demoable to judges	No — ethics DQ risk	Yes — it's the whole demo
Sayable in an interview	No	Yes, and it's a strong opener
Harder engineering?	No — one-way pipeline	Yes — bidirectional, barge-in, turn-taking, prosody analysis

The second column is not a watered-down version of the first. It is a strictly larger engineering problem, because a one-way "audio in → answer out" pipeline never has to solve turn-taking, barge-in cancellation, speaker-conditioned VAD, or realtime prosodic feature extraction. Those are the parts a technically literate judge will ask you about.

Write this in docs/ARCHITECTURE_DECISIONS.md as ADR-001. Being able to say "we deliberately scoped away live-interview assistance, here is the reasoning" is itself an engineering-judgment signal.

0.3 The four differentiators to build the demo around

Do not try to win on feature count. Win on these four, and make each one visible in under 30 seconds of demo:

Measured latency, displayed live. A ● LIVE — 412 ms badge fed by a real OpenTelemetry span, not a setTimeout. Show the timeline waterfall in developer mode. Almost nobody does this.
Grounding with provenance. Every candidate-specific claim in generated feedback traces to a resume line, page number, and confidence. Click a claim → see the source. This is your anti-hallucination story made visual.
Barge-in that actually works. Interrupt the AI interviewer mid-sentence; it stops within ~200 ms and yields the turn. This is the single most impressive live moment available to you.
Provider failover under live load. Kill the primary provider from the admin panel during the demo. The session survives, the badge switches to the fallback, latency ticks up, nothing crashes.
0.4 What this is not
Not a chatbot with a microphone.
Not a tool for use during a real interview. There is no hidden window, no capture-evasion, no proctoring bypass, and no "stealth mode." The overlay behaves like a normal OS window and appears in screen shares like any other window. This is a hard product boundary, enforced in code review.
Not a claim of enterprise reliability. Free-tier infrastructure is free-tier infrastructure. Say so.
PART 1 — PRODUCT DEFINITION
1.1 The five surfaces
PRAXIS
│
├── 1. CANDIDATE BRAIN      Resume → structured, reviewed, embedded candidate graph
├── 2. JOB BRAIN            JD → blueprint, explainable match, prep plan
├── 3. PRACTICE ARENA       Realtime AI interviewer + live coaching  ← THE CORE
├── 4. STUDY WORKBENCH      Screenshot/problem solver with a hint ladder
└── 5. CAREER OPS           Resume builder, outreach, application tracker, analytics

Priority is strict. Surface 3 must be excellent before Surface 5 exists at all.

1.2 P0 / P1 / P2
P0 — must work end-to-end before anything else is touched
Windows 11 Electron desktop app with real microphone + loopback capability detection
Realtime streaming STT of the candidate's voice (local faster-whisper primary, cloud adapter fallback)
Voice activity detection, turn detection, barge-in cancellation
AI interviewer that asks a question, listens, and asks a grounded follow-up
Candidate Brain: resume upload → parse → structured facts → human review → embeddings
Job Brain: JD paste → blueprint → explainable match
Realtime delivery analytics: WPM, filler rate, pause distribution, answer duration
Answer scoring with provenance-linked grounding
Follow-up memory graph (question N+1 knows what you said in answer N)
Multi-provider gateway with capability registry, routing, and failover
Latency instrumentation, end-to-end, displayed
Post-session debrief report
P1 — the platform around the core

Screenshot study workbench • coding/SQL/ML/system-design solvers with hint ladder • session history and transcript viewer • spaced-repetition study plan • resume builder • JD-tailored resume • cold outreach • application tracker • company intelligence • analytics dashboards • admin panel

P2 — advanced

Adaptive model routing by measured quality • hallucination detection • claim-consistency engine • personalized speaking-style modeling • skill-gap → curriculum generation • model evaluation lab • cost optimizer • organization workspaces

1.3 Compliance boundary (non-negotiable, enforced in code review)

Build: user-initiated capture, visible capture indicators, normal OS windowing, transparent permissions, explicit consent screens, local-first data handling.

Never build: proctoring bypass, screen-recording evasion, monitoring-detection avoidance, hidden or capture-excluded windows, conferencing-platform manipulation, fake webcam presence, credential capture, background persistence, or any feature whose value depends on a third party not knowing it is running.

Onboarding must show, and require acknowledgement of:

PRAXIS is a practice and preparation tool. It is designed for mock interviews, self-review, and study. Do not use it to receive assistance during a live interview, assessment, or exam.

Add a CI check: grep the repo for stealth, undetectable, bypass_proctor, hide_from_capture, setContentProtection, WDA_EXCLUDEFROMCAPTURE. Any hit fails the build with a link to this section.
