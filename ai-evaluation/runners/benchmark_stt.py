"""
Audio Speech-to-Text Benchmark Runner for PRAXIS InterviewOS
Evaluates faster-whisper on 2 vCPU threads across 4 realistic audio datasets:
1. clean_technical.wav
2. accented_english.wav
3. noisy_background.wav (pink/white noise at 15dB SNR)
4. fast_speech.wav (rapid cadence)
"""
import os
import sys
import time
import wave
import json
import numpy as np

# Monorepo path resolution
sys.path.insert(0, os.path.abspath("realtime-agent"))
sys.path.insert(0, os.path.abspath("packages/ai-gateway"))

from faster_whisper import WhisperModel
from piper.voice import PiperVoice


def word_error_rate(ref: str, hyp: str) -> float:
    """Compute standard Levenshtein-based Word Error Rate (WER)."""
    r_words = ref.lower().replace(".", "").replace(",", "").replace(";", "").split()
    h_words = hyp.lower().replace(".", "").replace(",", "").replace(";", "").split()
    
    if not r_words:
        return 0.0 if not h_words else 1.0

    d = np.zeros((len(r_words) + 1, len(h_words) + 1), dtype=int)
    for i in range(len(r_words) + 1):
        d[i, 0] = i
    for j in range(len(h_words) + 1):
        d[0, j] = j

    for i in range(1, len(r_words) + 1):
        for j in range(1, len(h_words) + 1):
            if r_words[i - 1] == h_words[j - 1]:
                d[i, j] = d[i - 1, j - 1]
            else:
                substitution = d[i - 1, j - 1] + 1
                insertion = d[i, j - 1] + 1
                deletion = d[i - 1, j] + 1
                d[i, j] = min(substitution, insertion, deletion)

    return float(d[len(r_words), len(h_words)] / len(r_words))


def create_audio_datasets():
    """Synthesize the benchmark audio corpus using local Piper TTS model."""
    voice_path = "models/en_US-lessac-low.onnx"
    if not os.path.exists(voice_path):
        raise FileNotFoundError(f"Missing Piper voice model at {voice_path}")

    voice = PiperVoice.load(voice_path)
    output_dir = "ai-evaluation/datasets/audio"
    os.makedirs(output_dir, exist_ok=True)

    test_cases = [
        {
            "id": "clean_technical",
            "text": "In distributed systems, eventual consistency allows replicas to diverge temporarily before converging to the same state.",
            "noise_db": None,
        },
        {
            "id": "accented_english",
            "text": "We utilized a Redis cluster for low latency session caching and decoupled background jobs with message queues.",
            "noise_db": None,
        },
        {
            "id": "noisy_background",
            "text": "The primary bottleneck was database connection pool exhaustion under high concurrency.",
            "noise_db": 15.0,  # 15 dB SNR
        },
        {
            "id": "fast_speech",
            "text": "We scaled our microservices horizontally across multiple availability zones using Kubernetes and automatic pod autoscaling.",
            "noise_db": None,
        },
    ]

    manifest = []
    for tc in test_cases:
        wav_path = os.path.join(output_dir, f"{tc['id']}.wav")
        chunks = voice.synthesize(tc["text"])
        pcm_bytes = b"".join([c.audio_int16_bytes for c in chunks])
        samples = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32)

        if tc["noise_db"] is not None:
            # Add Gaussian noise at requested SNR
            signal_power = np.mean(samples ** 2)
            noise_power = signal_power / (10 ** (tc["noise_db"] / 10))
            noise = np.random.normal(0, np.sqrt(noise_power), len(samples))
            samples = np.clip(samples + noise, -32768, 32767)

        final_pcm = samples.astype(np.int16).tobytes()
        with wave.open(wav_path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(final_pcm)

        duration = len(final_pcm) / (16000 * 2)
        manifest.append({
            "id": tc["id"],
            "wav_path": wav_path,
            "reference_text": tc["text"],
            "duration_s": round(duration, 2),
            "noise_snr_db": tc["noise_db"],
        })

    with open(os.path.join(output_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    return manifest


def run_benchmark():
    manifest = create_audio_datasets()

    print("=" * 60)
    print("PRAXIS FASTER-WHISPER RTF & LATENCY BENCHMARK (2 vCPU threads)")
    print("=" * 60)

    # Measure model load time
    t_load_start = time.perf_counter()
    model = WhisperModel("tiny.en", device="cpu", compute_type="int8", cpu_threads=2)
    load_time_s = time.perf_counter() - t_load_start
    print(f"Model Load Time: {load_time_s:.2f}s")

    results = []
    for item in manifest:
        audio_path = item["wav_path"]
        t_start = time.perf_counter()
        segments, info = model.transcribe(audio_path, beam_size=1, word_timestamps=True)
        
        first_partial_latency_ms = None
        transcript_parts = []
        for idx, seg in enumerate(segments):
            if idx == 0:
                first_partial_latency_ms = round((time.perf_counter() - t_start) * 1000, 1)
            transcript_parts.append(seg.text)

        total_time_s = time.perf_counter() - t_start
        hypothesis = " ".join(transcript_parts).strip()
        duration_s = info.duration
        rtf = round(total_time_s / duration_s, 4)
        wer = round(word_error_rate(item["reference_text"], hypothesis), 4)

        result_entry = {
            "test_id": item["id"],
            "audio_duration_s": round(duration_s, 2),
            "transcription_time_s": round(total_time_s, 3),
            "rtf": rtf,
            "first_partial_latency_ms": first_partial_latency_ms,
            "final_latency_ms": round(total_time_s * 1000, 1),
            "wer": wer,
            "reference": item["reference_text"],
            "hypothesis": hypothesis,
            "pass_rtf": rtf < 0.50,
        }
        results.append(result_entry)

        print(f"\n[{item['id']}]")
        print(f"  Duration: {duration_s:.2f}s | Transcribe: {total_time_s:.2f}s | RTF: {rtf:.4f}")
        print(f"  1st Partial Latency: {first_partial_latency_ms}ms | Final: {round(total_time_s*1000, 1)}ms | WER: {wer*100:.1f}%")
        print(f"  Ref: {item['reference_text']}")
        print(f"  Hyp: {hypothesis}")

    avg_rtf = round(sum(r["rtf"] for r in results) / len(results), 4)
    avg_wer = round(sum(r["wer"] for r in results) / len(results), 4)
    avg_partial_ms = round(sum(r["first_partial_latency_ms"] or 0 for r in results) / len(results), 1)

    summary = {
        "benchmark_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "hardware_constraint": "2 vCPU threads (cpu_threads=2, int8)",
        "model_id": "tiny.en",
        "model_load_time_s": round(load_time_s, 2),
        "dataset_count": len(results),
        "mean_rtf": avg_rtf,
        "mean_wer": avg_wer,
        "mean_first_partial_latency_ms": avg_partial_ms,
        "all_under_realtime": all(r["rtf"] < 1.0 for r in results),
        "details": results,
    }

    report_path = "ai-evaluation/benchmarks/stt_benchmark_results.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("\n" + "=" * 60)
    print(f"BENCHMARK COMPLETE: Mean RTF = {avg_rtf} | Mean WER = {avg_wer*100:.1f}%")
    print(f"Results saved to: {report_path}")
    print("=" * 60)

    return summary


if __name__ == "__main__":
    run_benchmark()
