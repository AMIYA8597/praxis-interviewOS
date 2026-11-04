# PRAXIS InterviewOS — Cost Optimization & Economics Report

**Document Version:** 1.0.0  
**Audit Date:** 2026-11-04  

---

## 1. Operational Cost Optimization Highlights

PRAXIS InterviewOS achieves low operating costs through a hybrid local-first + cloud architecture:

1. **Local-First Audio & Vector Processing ($0 Per-Call Cost):**
   - **Speech-to-Text:** Faster-Whisper CPU int8 runs inside `praxis-realtime` at RTF 0.097, completely avoiding $0.006/min third-party transcription APIs (saving ~$36/month per 100 hours of candidate audio).
   - **Voice Activity Detection:** Silero VAD runs locally on CPU in 0.2ms per frame (saving 100% of cloud VAD costs).
   - **Dense Embeddings:** `BAAI/bge-small-en-v1.5` embeds resume chunks locally on CPU (saving OpenAI `text-embedding-3-small` API costs).
   - **Optical Character Recognition:** Tesseract OCR processes uploaded images locally on CPU.
2. **Serverless Scale-to-Zero in Staging:**
   - `praxis-api`: Min instances = 0. When staging is idle, compute cost is $0.
   - `praxis-sandbox`: Min instances = 0. Only scales up when an active coding drill runs.
3. **Storage Lifecycle Automation:**
   - Resumes and audio recordings older than 90 days are transitioned to cold archive or purged according to candidate data retention settings (`user_settings.data_retention_days`).
4. **Log Retention Limits:**
   - Cloud Logging log sinks capped at 30-day retention in staging, preventing ingestion and storage fees.

---

## 2. Monthly Staging vs. Production Cost Projections

| Resource | Staging Cost (Low Traffic) | Production Cost (100 Active Daily Users) |
|---|---|---|
| **Cloud Run Services (API, Realtime, Worker)** | ~$36.00 / mo | ~$120.00 / mo |
| **Memorystore Redis (1 GB Basic)** | ~$36.00 / mo | ~$36.00 / mo |
| **Authoritative PostgreSQL** | $0.00 (Existing Tier) | $25.00 / mo (Pro Tier with PITR) |
| **Cloud Storage (GCS)** | ~$0.15 / mo | ~$2.50 / mo |
| **AI LLM Inference (Gateway Routed)** | ~$0.00 (Free Tier Groq/Gemini) | ~$45.00 / mo (Blended Free + Paid Fallbacks) |
| **Total Estimated Expenditure** | **~$72.15 / month** | **~$228.50 / month** |
