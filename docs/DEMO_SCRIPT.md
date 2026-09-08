# PRAXIS Hackathon Demo Script (4–5 minutes)

**0:00 - The Scope Decision (15s)**
*Open on the `ARCHITECTURE_DECISIONS.md` file.*
"This is a coaching tool, not an answer-feeding cheat tool. We explicitly chose this path because building a bidirectional, low-latency, barge-in capable voice engine is a significantly harder and more honest engineering problem than a stealth-transcription script."

**0:15 - Verified Candidate Brain (30s)**
*Open the RAG Profile UI.*
"PRAXIS extracts your resume into a knowledge graph. Crucially, it requires human review. The AI proposes, you confirm. Nothing unverified is *ever* used as evidence."

**0:45 - Explainable Match (20s)**
*Open the Job Match UI.*
"When we compare your profile to a JD, we don't just spit out a black-box percentage. I can click any matched requirement and trace the exact provenance edge back to the candidate's verified chunk."

**1:05 - Live Practice Session (90s)**
*Boot the Electron App and start a session.*
"Let's practice. *[The AI asks a question in a synthesized voice].* Notice the Coaching HUD updating live with my WPM and filler words. Because this relies on pure DSP and ONNX models locally, it runs at 4Hz and never blocks on LLM latency."

**2:35 - Barge-In Interruption (15s)**
*Interrupt the AI mid-sentence.*
"I just interrupted it. Look at the Diagnostics Waterfall—barge-in ducked the audio in under 200ms."

**2:50 - Live Provider Failover (30s)**
*Open the Admin Panel on another monitor. Disable the primary provider (Groq).*
"I'm killing the primary inference provider mid-conversation. Let's keep talking. The AI Gateway's circuit breaker instantly tripped, caught the timeout, and failed over to Gemini without dropping the WebSocket session."

**3:20 - Debrief & Study Loop (30s)**
*End the session. Open the Web Dashboard.*
"Here is the Debrief. It flags ungrounded claims I made against my own resume. I'll click this weak technical answer and push it into the Spaced-Repetition Study Plan, powered by the SM-2 algorithm."

**3:50 - Close (20s)**
"This entire demo just ran on a local machine using a free-first architecture. It defaults to zero-spend, and scales up only when you provide your own keys. PRAXIS is a durable, mathematically grounded coaching platform."
