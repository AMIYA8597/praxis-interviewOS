import pytest
import struct
import time
import asyncio
import os
from realtime_agent.audio.transport import TransportPipeline, HEADER_FORMAT

@pytest.mark.asyncio
async def test_frame_ingest_happy_path():
    processed_frames = []
    
    async def on_frame(frame):
        processed_frames.append(frame)
        
    pipeline = TransportPipeline("test-session", on_frame)
    
    # Generate 50 frames, 20ms apart
    for i in range(1, 51):
        capture_ts = time.time() * 1000.0 - 15.0 # Simulated 15ms network latency
        pcm = os.urandom(640) # e.g. 20ms of 16kHz 16-bit mono
        header = struct.pack(HEADER_FORMAT, i, capture_ts, len(pcm))
        
        await pipeline.receive_raw(header + pcm)
        # We don't sleep here because it's a synchronous test feeding fast,
        # but the latency calculation uses real time.
        
    assert len(processed_frames) == 50
    assert pipeline.dropped_frame_count == 0
    
    metrics = pipeline.get_metrics()
    assert metrics["latency_p50_ms"] > 0
    assert metrics["latency_p95_ms"] > 0
    
    print(f"\n[Happy Path] p50: {metrics['latency_p50_ms']:.2f}ms, p95: {metrics['latency_p95_ms']:.2f}ms")

@pytest.mark.asyncio
async def test_frame_ingest_out_of_order():
    processed_frames = []
    
    async def on_frame(frame):
        processed_frames.append(frame)
        
    pipeline = TransportPipeline("test-session", on_frame)
    
    def make_frame(seq):
        capture_ts = time.time() * 1000.0 - 15.0
        pcm = os.urandom(640)
        return struct.pack(HEADER_FORMAT, seq, capture_ts, len(pcm))
        
    # Send seq 1
    await pipeline.receive_raw(make_frame(1))
    assert len(processed_frames) == 1
    
    # Send seq 3 (out of order, buffer it)
    await pipeline.receive_raw(make_frame(3))
    assert len(processed_frames) == 1
    
    # Send seq 4 (out of order, buffer it)
    await pipeline.receive_raw(make_frame(4))
    assert len(processed_frames) == 1
    
    # Send seq 2 (fills gap, should flush 2, 3, 4)
    await pipeline.receive_raw(make_frame(2))
    assert len(processed_frames) == 4
    
    assert [f.sequence for f in processed_frames] == [1, 2, 3, 4]
    assert pipeline.dropped_frame_count == 0

@pytest.mark.asyncio
async def test_frame_ingest_too_late():
    processed_frames = []
    
    async def on_frame(frame):
        processed_frames.append(frame)
        
    pipeline = TransportPipeline("test-session", on_frame)
    
    def make_frame(seq):
        capture_ts = time.time() * 1000.0 - 15.0
        pcm = os.urandom(640)
        return struct.pack(HEADER_FORMAT, seq, capture_ts, len(pcm))
        
    # Send seq 1, 2, 3
    await pipeline.receive_raw(make_frame(1))
    await pipeline.receive_raw(make_frame(2))
    await pipeline.receive_raw(make_frame(3))
    
    # expected_sequence is now 4
    
    # Send seq 2 (arrived too late!)
    await pipeline.receive_raw(make_frame(2))
    
    assert pipeline.dropped_frame_count == 1
    assert len(processed_frames) == 3
