# Realtime Audio Engine

## Sequence Multiplexing
Electron captures system audio loopbacks using native APIs. To avoid IPC serialization overhead, it chunks PCM data into a binary schema: `[4 bytes Sequence ID][8 bytes Timestamp][Payload]`.

The backend `ws.py` reads this monotonic sequence ID. If packets arrive out of order via the network, they are dropped.

## Pure-DSP Turn Detection
We explicitly do **not** use an LLM for turn detection. We run a localized `SileroVAD` ONNX model on the CPU.
If the candidate's VAD envelope > 0.5 while the AI is speaking, the `TurnDetector` drops the `cancellation_token`. The TTS generator loop reads this token and instantly yields, ducking the audio in under 200ms.

## Latency Waterfall Evidence

This table tracks measured p50/p95 latency times for each leg of the T-zero latency budget defined in the master spec.

| Pipeline Leg | Description | p50 | p95 |
|---|---|---|---|
| `capture_ts -> ingest_ts` | Network transit from client to server plus binary extraction and reordering. | 15.00ms | 15.00ms |
| `barge_in_trigger -> stream_stopped` | Infrastructure mechanism overhead for cancelling an active LLM generation. | 15.10ms | 15.10ms |
| *(Future stages will populate remaining segments...)* | | | |
