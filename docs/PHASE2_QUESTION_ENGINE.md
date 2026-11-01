# PRAXIS InterviewOS — Phase 2 Question Intelligence Engine

**Date**: 2026-11-01  
**Project**: PRAXIS InterviewOS (`AMIYA8597/praxis-interviewOS`)  
**Workstream**: WORKSTREAM D — QUESTION INTELLIGENCE ENGINE  
**Classification**: PRODUCTION ARCHITECTURE SPECIFICATION  

---

## 1. Overview & Dynamic Probing

The Question Intelligence Engine (`realtime_agent/app/interview/policy.py`) generates context-aware, adaptive interview questions tailored to the candidate's background, the target job description, and previous answer quality:

1. **Session Warm-Up**:
   - Pre-fetches verified candidate facts, verified projects, and job description blueprints once at session initialization.
   - Prevents database query storms on every conversational turn.
2. **Follow-Up Graph**:
   - Tracks parent-child turn relationships (`session_turns.parent_turn_id`).
   - If an answer leaves technical ambiguities or unsubstantiated claims, the interviewer initiates targeted follow-up probing rather than jumping abruptly to an unrelated topic.
3. **Adaptive Difficulty Modulation**:
   - `backend/app/services/adaptive_difficulty.py`: Implements Item Response Theory (IRT) difficulty tracking:
     - Correct + deep answer: Increases difficulty level (`STEP_UP = 0.08`, `DOUBLE_STEP_UP = 0.15` on streak).
     - Correct + shallow answer: Maintains current difficulty level.
     - Incorrect answer: Decreases difficulty level (`STEP_DOWN = 0.12`, floor `0.10`).
   - Modulates interviewer persona: `warmup` (foundational, encouraging), `standard`, `senior`, or `stress` (rigorous, adversarial edge-case probing).
4. **Context Window Compression**:
   - Automatically summarizes older turns after 6 conversational exchanges, retaining the last 3 turns intact in short-term memory to keep LLM context tightly bounded.
