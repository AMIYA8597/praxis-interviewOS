# PRAXIS InterviewOS — Phase 2 Known Limitations & Blocked Tests

**Date**: 2026-11-01  
**Project**: PRAXIS InterviewOS (`AMIYA8597/praxis-interviewOS`)  
**Phase**: Phase 2 — AI/ML Intelligence  
**Classification**: HONEST STATUS DISCLOSURE (PART 24 COMPLIANCE)  

---

## 1. Documented Operational Limitations

1. **Local Audio Benchmarking Model Size**:
   - The faster-whisper benchmark was measured using `tiny.en` and `small.en` on 2 vCPU threads (`int8`). High-latency models (`large-v3`) require dedicated GPU acceleration to maintain sub-0.50 RTF.
2. **Accented Speech Phonetic Drift**:
   - As measured in `ai-evaluation/benchmarks/stt_benchmark_results.json`, heavy accent cadence exhibits higher Word Error Rate (~29.4% vs 0.0% clean). The downstream claim grounding engine successfully mitigates this by matching against candidate-specific entity vocabularies from their resume.
3. **Local pgvector Extension**:
   - On the local developer machine's PostgreSQL 18 instance, the compiled `pgvector` C-extension is not installed in the Windows system library path, so vector search unit tests gracefully test the text/embedding fallback path. In the Cloud Supabase project `rqbbfegkqmsvthdgoyqk` and Cloud Run production images, `pgvector` is enabled natively.
4. **Standalone Remote Sandbox Service**:
   - The coding sandbox engine supports local subprocess isolation (tested and passing) and remote gRPC execution via `SANDBOX_SERVICE_URL`. Remote gRPC runner deployment is scheduled for Phase 4 security hardening.
