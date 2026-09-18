### 1. `faster-whisper`
- **Installation on Windows:** Requires careful matching of CUDA, cuDNN, and `ctranslate2` versions.
  - For CUDA 12 + cuDNN 9, the default latest `ctranslate2` works.
  - CPU builds are viable for `tiny.en` and `small.en`.
  - For this desktop setup (no GPU detected), CPU execution (`compute_type='int8'`) with multiple threads (e.g., 8 threads) is recommended.

### 2. `silero-vad`
- **Usage Pattern:** The ONNX runtime path is highly preferred over the raw PyTorch path for desktop apps, avoiding a full PyTorch install (2GB+). 
- **Loading API:** Use `torch.hub.load(..., onnx=True, trust_repo=True)` to get the models. It requires `onnxruntime`.

### 3. Piper TTS
- **Release Process:** Active development is at `OHF-Voice/piper1-gpl`. It ships as a Python package wrapper `piper-tts` or standalone binary using ONNX.
- **English Voice Models:** Models are ONNX-based (an `.onnx` and `.onnx.json` config).
- **Download URLs (example):** `https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/low/en_US-lessac-low.onnx`

### 4. `sentence-transformers`
- **Current Version:** `3.0+`
- **Model Recommendation:** `BAAI/bge-small-en-v1.5` remains the recommended lightweight general-purpose embedding model. It outputs 384-dimensional vectors, matching the `pgvector` schema dimension configured in Stage 1.

### 5. Ollama Models
- **Catalog:**
  - `qwen2.5:3b` (fast_classify): ~1.9 GB disk space, requires at least 4 GB RAM.
  - `qwen2.5:14b` (reasoning): ~9.0 GB disk space, requires at least 11-12 GB VRAM (GPU) or 16+ GB RAM (CPU-only).
- **Recommendation:** Since this system has 7.84 GB RAM and no GPU, `qwen2.5:3b` is recommended for both reasoning and fast_classify to prevent OOM errors.

### 6. Groq
- **Whisper Endpoint:** `whisper-large-v3` is available on the free tier.
- **Chat Catalog:** Matches Stage 2's adapters (e.g., `llama-3.1-8b-instant`, `llama-3.1-70b-versatile`).

### Smoke Tests Evidence
```text
--- Testing faster-whisper ---
Transcription: ''
faster-whisper test passed.

--- Testing silero-vad ---
Detected speech segments: []
silero-vad test passed.

--- Testing Piper TTS ---
Piper output WAV created successfully.

--- Testing sentence-transformers ---
Embedding dimension: 384 (Expected: 384)
Similarity (related): 0.8143
Similarity (unrelated): 0.4431
sentence-transformers test passed.
```
