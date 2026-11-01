# PRAXIS Infrastructure Cost Estimation

**Date**: 2026-11-01  
**Target Region**: `asia-south1` (Mumbai)  
**Provider Baseline**: Google Cloud Platform (GCP) & Supabase  

---

## 1. Cost Component Breakdown

| Service Component | Sizing & Unit | Development / Staging | Early Production (50 Users) | Growth (500 Users) |
|---|---|:---:|:---:|:---:|
| **GCP Cloud Run: API** | 1 vCPU, 1 GB RAM (Scale-to-zero) | ~$0.00 (Free Tier) | ~$8.50 / mo | ~$42.00 / mo |
| **GCP Cloud Run: Realtime** | 1 vCPU, 2 GB RAM (min 1 instance in prod) | ~$0.00 (Scale-to-zero) | ~$24.00 / mo | ~$78.00 / mo |
| **GCP Cloud Run: Worker** | 1 vCPU, 2 GB RAM (Scale-to-zero) | ~$0.00 (On-demand) | ~$6.00 / mo | ~$28.00 / mo |
| **GCP Memorystore Redis** | Basic Tier (1 GB) | ~$0.00 (Local / dev) | ~$36.00 / mo | ~$72.00 / mo (Standard HA) |
| **Supabase PostgreSQL** | Pro Tier ($25/mo) + pgvector + Auth | $0.00 (Free Tier) | $25.00 / mo | $45.00 / mo (Micro compute) |
| **Supabase Storage** | Document Storage & Bandwidth | $0.00 (< 1 GB) | ~$2.00 / mo | ~$12.00 / mo |
| **GCP Secret Manager** | 10 active secrets, version access | ~$0.06 / mo | ~$0.20 / mo | ~$1.20 / mo |
| **GCP Artifact Registry** | Container image storage (~5 GB) | ~$0.50 / mo | ~$1.00 / mo | ~$2.50 / mo |
| **Cloud Logging & Monitoring** | Structured JSON logs (< 50 GB) | $0.00 (Free Tier) | ~$5.00 / mo | ~$20.00 / mo |
| **Network Egress** | Client REST & WebSocket streams | $0.00 (< 10 GB) | ~$4.50 / mo | ~$22.00 / mo |
| **Total Estimated Monthly Cost** | — | **~$0.56 / mo** | **~$112.20 / mo** | **~$323.70 / mo** |

*Note: AI Provider API consumption (Groq, Gemini, OpenAI) is managed under the Phase 2 AI Gateway budget guard and billed separately.*

---

## 2. Fixed vs. Variable Cost Profile

### Fixed Costs
- **Supabase Pro Tier**: $25.00/month (provides daily automated backups, 7-day point-in-time recovery, 8 GB database storage, and 100 GB storage egress).
- **Memorystore Redis 1 GB**: ~$36.00/month (when continuously running in production).

### Variable Costs
- **Cloud Run Request Processing**: Billed per 100ms of active vCPU and memory. Scale-to-zero ensures that inactive services during non-interview hours incur zero compute charges.
- **WebSocket Streaming Concurrency**: Realtime Agent charges scale with the duration of active live interview sessions (~$0.04 per active session hour).

---

## 3. Cost Optimization Recommendations

1. **Scale-to-Zero in Staging**:
   - Staging sets `api_min_instances = 0`, `realtime_min_instances = 0`, and `worker_instance_count = 0` when inactive, reducing staging compute costs to near zero.
2. **Pre-Downloaded Local Models**:
   - The STT Whisper model (`small`) and Silero VAD weights are baked into the container image layer, eliminating expensive outbound egress and startup latency on container launches.
3. **Budget Guard & Billing Alerts**:
   - Set GCP billing alert at $150.00/month (50%, 80%, 100% thresholds).
   - Enforce server-side AI provider spend caps via `FREE_TIER_BUDGET_DAILY_USD = 0.50` in `packages/ai-gateway`.
