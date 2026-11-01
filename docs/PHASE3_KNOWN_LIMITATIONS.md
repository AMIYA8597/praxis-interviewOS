# PRAXIS InterviewOS — Phase 3 Known Limitations & Edge Cases

**Milestone**: Phase 3 — Web & Desktop Client Engineering  
**Branch**: `phase3-web-desktop`  
**Date**: 2026-11-01  
**Classification**: SYSTEM LIMITATIONS REGISTER  

---

## 1. Known Architectural Limitations

### 1.1 Web Audio Sample Rate Resampling
- Certain mobile browsers lock hardware microphone input to 44,100 Hz or 48,000 Hz, refusing explicit 16,000 Hz capture constraints.
- *Mitigation*: The web client automatically downsamples PCM buffers to 16kHz before packing binary frames, incurring minor CPU overhead (<1%).

### 1.2 Desktop System Audio Loopback Permissions
- macOS requires explicit system permissions (Screen Recording / Audio Capture permission) to access loopback audio from meeting apps (e.g. Zoom/Meet).
- *Mitigation*: The desktop app includes preflight permission prompts and gracefully degrades to microphone-only capture if loopback permissions are declined.

### 1.3 Text Fallback Mode Latency Difference
- While speech-driven turns execute with real-time streaming hypotheses, text answers submitted via `candidate.text_answer` do not produce interim ASR hypotheses.
- *Mitigation*: The UI shows a subtle typing indicator until the evaluator completes turn analysis.

### 1.4 Cold Start Latency for Debrief Generation
- When evaluating extensive interviews (>= 15 turns) against comprehensive resumes with numerous claims, debrief generation may take 5–15 seconds while hybrid RAG and LLM rubrics execute.
- *Mitigation*: The debrief UI features an explicit pending banner with auto-refresh instructions.
