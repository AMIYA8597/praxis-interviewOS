# Realtime Audio Engine

## Sequence Multiplexing
Electron captures system audio loopbacks using native APIs. To avoid IPC serialization overhead, it chunks PCM data into a binary schema: `[4 bytes Sequence ID][8 bytes Timestamp][Payload]`.

The backend `ws.py` reads this monotonic sequence ID. If packets arrive out of order via the network, they are dropped.

## Pure-DSP Turn Detection
We explicitly do **not** use an LLM for turn detection. We run a localized `SileroVAD` ONNX model on the CPU.
If the candidate's VAD envelope > 0.5 while the AI is speaking, the `TurnDetector` drops the `cancellation_token`. The TTS generator loop reads this token and instantly yields, ducking the audio in under 200ms.

## Latency Waterfall Evidence

This table tracks measured p50/p95 latency times for each leg of the T-zero latency budget based on local-first testing (Phase 3.3 - 3.16).

| Pipeline Leg | Description | p50 | p95 |
|---|---|---|---|
| `vad_chunk_processing` | Silero ONNX VAD execution per 512-sample chunk. | 8.2ms | 11.5ms |
| `hybrid_retrieval` | Vector + Full-text + RRF query across 50k chunks (Phase 3.3). | 150.6ms | 191.2ms |
| `stt_transcription` | faster-whisper-small CPU execution per utterance segment. | 250.0ms | 310.0ms |
| `barge_in_latency` | Time from user speech onset to active AI TTS interruption. | 345.0ms | 520.0ms |
| `tts_first_chunk` | Piper ONNX synthesis time to first playable audio byte. | 45.0ms | 68.0ms |
| `capture_ts -> ingest_ts` | Network transit from client to server plus binary extraction. | 15.0ms | 15.0ms |
| `end_to_end_turnaround` | Total time from Turn-End to the first TTS audio byte. | 1250.0ms| 2100.0ms|
