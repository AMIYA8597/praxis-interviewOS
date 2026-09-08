import struct
import time
import logging
from typing import Optional, Callable, Awaitable, Dict, List
import numpy as np
from opentelemetry import trace

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

# Frame Header Schema:
# 16 bytes total:
# - 4 bytes (uint32): sequence number
# - 8 bytes (float64): capture timestamp in epoch ms
# - 4 bytes (uint32): frame length (PCM bytes)
#
# WHY THE CAPTURE TIMESTAMP MUST BE SET CLIENT-SIDE:
# This timestamp is the anchor for the entire latency budget. It represents T-zero.
# If we set this server-side at the moment of receipt (`ingest_ts`), we would silently
# exclude client-to-server network transit time from all downstream latency numbers.
# That would make any "sub-2-second" claim dishonestly optimistic by hiding the
# potentially worst variable in the pipeline (the user's network).

HEADER_FORMAT = "!IdI"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

class AudioFrame:
    def __init__(self, sequence: int, capture_ts: float, ingest_ts: float, pcm_data: bytes):
        self.sequence = sequence
        self.capture_ts = capture_ts
        self.ingest_ts = ingest_ts
        self.pcm_data = pcm_data
        
    @property
    def latency_ms(self) -> float:
        return self.ingest_ts - self.capture_ts

class TransportPipeline:
    def __init__(self, session_id: str, on_frame_ready: Callable[[AudioFrame], Awaitable[None]]):
        self.session_id = session_id
        self.on_frame_ready = on_frame_ready
        
        self.expected_sequence = 1
        self.buffer_size = 5
        self.reorder_buffer: Dict[int, AudioFrame] = {}
        
        # Metrics
        self.dropped_frame_count = 0
        self.latencies: List[float] = []
        self.start_time = time.time()
        self.frame_count = 0

    def parse_frame(self, raw_bytes: bytes) -> Optional[AudioFrame]:
        ingest_ts = time.time() * 1000.0  # ms
        
        if len(raw_bytes) < HEADER_SIZE:
            logger.warning(f"Frame too small: {len(raw_bytes)} bytes")
            return None
            
        header = raw_bytes[:HEADER_SIZE]
        try:
            sequence, capture_ts, frame_length = struct.unpack(HEADER_FORMAT, header)
        except struct.error:
            logger.warning("Failed to unpack frame header")
            return None
            
        pcm_data = raw_bytes[HEADER_SIZE:HEADER_SIZE+frame_length]
        
        return AudioFrame(sequence, capture_ts, ingest_ts, pcm_data)

    async def receive_raw(self, raw_bytes: bytes):
        frame = self.parse_frame(raw_bytes)
        if not frame:
            return
            
        with tracer.start_as_current_span("frame_ingest") as span:
            span.set_attribute("session.id", self.session_id)
            span.set_attribute("frame.sequence", frame.sequence)
            span.set_attribute("latency.ms", frame.latency_ms)
            
            self.latencies.append(frame.latency_ms)
            # keep latencies bounded for rolling window
            if len(self.latencies) > 1000:
                self.latencies = self.latencies[-1000:]
                
            self.frame_count += 1
            
            await self._process_frame(frame)

    async def _process_frame(self, frame: AudioFrame):
        if frame.sequence < self.expected_sequence:
            # Arrived too late
            self.dropped_frame_count += 1
            logger.warning(f"[{self.session_id}] Dropped frame {frame.sequence} (expected {self.expected_sequence}). Total drops: {self.dropped_frame_count}")
            return
            
        if frame.sequence == self.expected_sequence:
            # In order
            await self.on_frame_ready(frame)
            self.expected_sequence += 1
            # Flush any contiguous buffered frames
            while self.expected_sequence in self.reorder_buffer:
                buffered_frame = self.reorder_buffer.pop(self.expected_sequence)
                await self.on_frame_ready(buffered_frame)
                self.expected_sequence += 1
        else:
            # Out of order, sequence > expected
            if frame.sequence > self.expected_sequence + self.buffer_size:
                # Buffer overrun, we have to skip ahead to not stall forever
                logger.warning(f"[{self.session_id}] Buffer overrun. Expected {self.expected_sequence}, got {frame.sequence}. Skipping ahead.")
                # We drop whatever was expected
                skipped = frame.sequence - self.expected_sequence
                self.dropped_frame_count += skipped
                
                # Deliver this frame immediately
                await self.on_frame_ready(frame)
                self.expected_sequence = frame.sequence + 1
                
                # Clear buffer of any older things
                stale_keys = [k for k in self.reorder_buffer.keys() if k < self.expected_sequence]
                for k in stale_keys:
                    del self.reorder_buffer[k]
                    
            else:
                # Store in buffer
                self.reorder_buffer[frame.sequence] = frame

    def get_metrics(self) -> dict:
        p50 = np.percentile(self.latencies, 50) if self.latencies else 0.0
        p95 = np.percentile(self.latencies, 95) if self.latencies else 0.0
        
        elapsed = time.time() - self.start_time
        arrival_rate = self.frame_count / elapsed if elapsed > 0 else 0.0
        
        return {
            "latency_p50_ms": p50,
            "latency_p95_ms": p95,
            "dropped_frames": self.dropped_frame_count,
            "arrival_rate_fps": arrival_rate
        }
