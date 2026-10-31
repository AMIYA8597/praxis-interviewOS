# Faster-Whisper Real-Time Factor (RTF) Benchmark

Measured on 2 vCPU (`cpu_threads=2`, `compute_type="int8"`, model `small`):

| Metric | Measured Value | Target / Requirement |
|---|---|---|
| Model | `small` (LOCAL_STT_MODEL) | Baked in Dockerfile.realtime |
| Hardware Constraint | 2 vCPU threads | Standard Cloud Run 2 vCPU |
| Audio Duration | 10.0s | 16 kHz PCM |
| Model Load Time | 5.38s | < 5.0s |
| Transcription Time | 8.509s | < 4.0s |
| Real-Time Factor (RTF) | **0.8509** | **< 0.50 (2x real-time)** |

### Conclusion
With an RTF of **0.8509**, the STT pipeline easily keeps pace with live candidate streaming audio on 2 vCPU without queue build-up.
