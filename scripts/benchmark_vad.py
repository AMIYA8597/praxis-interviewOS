import time
import numpy as np
import uuid

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'realtime-agent'))

from realtime_agent.app.audio.vad import VoiceActivityDetector

def main():
    print("Initializing VAD...")
    vad = VoiceActivityDetector()
    
    # Generate 5000 frames (512 samples each, 16kHz int16)
    num_frames = 5000
    print(f"Generating {num_frames} synthetic frames for benchmarking...")
    
    # 512 samples * 2 bytes = 1024 bytes
    fake_frames = [np.random.randint(-32768, 32767, 512, dtype=np.int16).tobytes() for _ in range(num_frames)]
    
    # Warmup
    for i in range(10):
        vad.process_frame(fake_frames[i])
        
    latencies = []
    
    print("Running benchmark...")
    for frame in fake_frames:
        start = time.perf_counter()
        vad.process_frame(frame)
        end = time.perf_counter()
        latencies.append((end - start) * 1000)
        
    p50 = np.percentile(latencies, 50)
    p95 = np.percentile(latencies, 95)
    
    print(f"VAD Latency Benchmark (over {num_frames} frames):")
    print(f"  p50: {p50:.2f} ms")
    print(f"  p95: {p95:.2f} ms")
    
if __name__ == "__main__":
    main()
