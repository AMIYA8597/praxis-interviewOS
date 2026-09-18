
## ADR-005: Local-First AI/ML Stack Selection

**Date:** 2026-09-08

**Context:** 
We require highly responsive local inference models for the PRAXIS realtime audio pipeline and background processing. These models must be performant enough to meet the 2-second turnaround time budget for a complete STT -> Planning -> TTS loop, even on a CPU-only developer machine if necessary.

**Decision:**
We explicitly selected the following AI/ML primitives based on strict performance and architecture constraints:

1. **faster-whisper over openai-whisper (STT):**
   The `CTranslate2` backend gives materially faster inference, especially on CPU. This is not a marginal optimization; it is the difference between a usable and unusable local STT path. Standard `whisper` is too slow for realtime interactions unless heavily accelerated by top-tier GPUs, which breaks the local-first ethos.

2. **Silero VAD over WebRTC VAD (VAD):**
   Silero is substantially more accurate at distinguishing speech from background noise or silence at a similar computational cost. This matters directly because a false-positive VAD trigger would incorrectly fire Stage 2's barge-in controller, rudely interrupting the interviewer or assuming the user has spoken when they haven't. ONNX execution keeps it under ~2MB and extremely fast.

3. **Piper over heavy neural TTS (TTS):**
   Piper trades a small amount of voice naturalness for genuinely real-time synthesis speed and an incredibly small memory footprint. For an interviewer persona that needs to start speaking quickly to emulate natural conversational flow, this is the correct trade-off compared to a heavier, higher-quality narrator model which could introduce seconds of latency.

4. **BAAI/bge-small-en-v1.5 over larger embedding models (Embeddings):**
   This model outputs 384 dimensions, keeping the HNSW index from Stage 1 fast and small at portfolio data volumes. Retrieval quality at this scale is dominated by chunking and retrieval-strategy quality more than by marginal embedding-model quality gains. Fixing it at 384 dimensions is a considered trade-off for speed and minimal indexing overhead, rather than an unexamined default.

5. **Ollama qwen2.5 (Local LLMs):**
   For local classification and reasoning, the `qwen2.5` model family provides a strong balance of context length, reasoning capability, and footprint. `qwen2.5:3b` runs comfortably on ~4GB RAM, providing a fallback fast-classify endpoint, while `qwen2.5:14b` offers high reasoning quality where hardware (12GB+ VRAM or 16GB+ System RAM) permits.
