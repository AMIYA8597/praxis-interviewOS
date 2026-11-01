# PRAXIS InterviewOS — Phase 3 Audio Experience & Protocol

**Milestone**: Phase 3 — Web & Desktop Client Engineering  
**Branch**: `phase3-web-desktop`  
**Date**: 2026-11-01  
**Classification**: AUDIO & SPEECH PROTOCOL SPECIFICATION  

---

## 1. Audio Architecture & Pipeline

PRAXIS captures candidate speech at **16,000 Hz Mono** to feed directly into the backend `faster-whisper` automatic speech recognition (ASR) engine.

```
[ Microphone Input ]
         |
         v
[ Web Audio Context (16kHz Mono) ]
         |
         +---> [ AnalyserNode (256 FFT) ] ---> Visual Level Meter (0-100%)
         |
         v
[ ScriptProcessor / AudioWorklet (4096 samples) ]
         |
         v
[ Float32 to PCM16 Clamping ]
         |
         v
[ Binary Framing (>BBIdI 18-Byte Header) ]
         |
         v
[ WebSocket Binary Transmission to Port 8001 ]
```

---

## 2. Binary Frame Protocol (`>BBIdI`)

Binary frames stream over WebSocket with an 18-byte big-endian header followed by raw PCM16 samples:

| Offset | Type | Field Name | Description |
| :--- | :--- | :--- | :--- |
| `0` | `uint8` | `proto_ver` | Protocol version (always `1`) |
| `1` | `uint8` | `frame_type` | Frame type (`1` = `AUDIO_FRAME`) |
| `2-5` | `uint32` | `client_seq` | Monotonically increasing sequence number |
| `6-13`| `float64`| `capture_ts` | Epoch timestamp (seconds) at client capture |
| `14-17`| `uint32`| `payload_len`| Length of raw PCM16 audio bytes |
| `18+` | `int16[]`| `payload` | 16-bit signed PCM samples (`-32768` to `32767`) |

### Sample Conversion Code:
```typescript
export function float32ToPCM16(float32Array: Float32Array): Int16Array {
  const pcm16 = new Int16Array(float32Array.length);
  for (let i = 0; i < float32Array.length; i++) {
    const sample = Math.max(-1, Math.min(1, float32Array[i]));
    pcm16[i] = sample < 0 ? sample * 0x8000 : sample * 0x7fff;
  }
  return pcm16;
}
```

---

## 3. Audio Preflight Check

Both web and desktop clients include an audio preflight workflow:
1. Microphone enumeration via `navigator.mediaDevices.enumerateDevices()`.
2. Explicit permission request before entering practice.
3. Visual level meter animation confirming that the microphone is receiving acoustic input.
4. Fallback text input mode (`candidate.text_answer`) in case the candidate lacks a functioning microphone.
