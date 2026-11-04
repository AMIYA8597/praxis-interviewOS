import asyncio
import time
import os
import sys
sys.path.extend([".", "backend", "realtime-agent", "packages/ai-gateway"])
from dotenv import load_dotenv
load_dotenv()
import psutil
import numpy as np
from sqlalchemy import text
from backend.app.db.session import _get_factory
from faster_whisper import WhisperModel
from realtime_agent.app.audio.vad import VoiceActivityDetector

def run_benchmarks():
    results = {}
    
    # 1. System Metrics
    mem = psutil.virtual_memory()
    cpu_pct = psutil.cpu_percent(interval=1.0)
    results["cpu_utilization_pct"] = cpu_pct
    results["ram_total_gb"] = round(mem.total / (1024**3), 2)
    results["ram_used_gb"] = round(mem.used / (1024**3), 2)
    results["ram_percent"] = mem.percent

    # 2. Database Query Latency
    async def bench_db():
        factory = _get_factory()
        async with factory() as db:
            latencies = []
            for _ in range(50):
                t0 = time.perf_counter()
                await db.execute(text("SELECT 1"))
                latencies.append((time.perf_counter() - t0) * 1000)
            return {
                "db_ping_p50_ms": round(float(np.percentile(latencies, 50)), 2),
                "db_ping_p95_ms": round(float(np.percentile(latencies, 95)), 2),
                "db_ping_p99_ms": round(float(np.percentile(latencies, 99)), 2),
            }
    results["database"] = asyncio.run(bench_db())

    # 3. Audio Processing Latency (Silero VAD)
    vad = VoiceActivityDetector()
    frame_512 = np.zeros(512, dtype=np.int16).tobytes()
    vad_latencies = []
    for _ in range(100):
        t0 = time.perf_counter()
        vad.process_frame(frame_512)
        vad_latencies.append((time.perf_counter() - t0) * 1000)
    results["vad"] = {
        "vad_frame_p50_ms": round(float(np.percentile(vad_latencies, 50)), 3),
        "vad_frame_p95_ms": round(float(np.percentile(vad_latencies, 95)), 3),
    }

    # 4. Faster-Whisper Inference Latency (tiny.en on CPU)
    t0 = time.perf_counter()
    model = WhisperModel("tiny.en", device="cpu", compute_type="int8")
    results["whisper_load_s"] = round(time.perf_counter() - t0, 3)

    wav_path = "ai-evaluation/datasets/audio/clean_technical.wav"
    if os.path.exists(wav_path):
        t0 = time.perf_counter()
        segments, info = model.transcribe(wav_path, beam_size=1)
        text_out = " ".join([s.text for s in segments])
        results["whisper_transcription_s"] = round(time.perf_counter() - t0, 3)
        results["audio_duration_s"] = round(info.duration, 2)
        results["realtime_factor_rtf"] = round(results["whisper_transcription_s"] / info.duration, 3)
        results["transcribed_sample"] = text_out[:60] + "..."

    return results

if __name__ == "__main__":
    import json
    data = run_benchmarks()
    print(json.dumps(data, indent=2))
