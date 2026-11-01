# PRAXIS InterviewOS — Phase 3 Desktop Application Implementation

**Milestone**: Phase 3 — Web & Desktop Client Engineering  
**Branch**: `phase3-web-desktop`  
**Date**: 2026-11-01  
**Classification**: DESKTOP ENGINEERING SPECIFICATION  

---

## 1. Overview & Desktop Rationale

The desktop client (`apps/desktop`) provides:
- **Low-Latency Native Audio**: Direct microphone and loopback audio capture bypassing browser sandbox restrictions.
- **Dedicated Practice Arena**: Focused, distraction-free environment for intensive mock interviews.
- **Coaching HUD**: Real-time feedback window displaying speaking pace (WPM), filler word rate, and turn cadence independently of LLM turn evaluation latency.

---

## 2. Process Architecture & Sandboxing

```
+-------------------------------------------------------------+
|                     Electron Main Process                   |
| - Window Lifecycle Management                               |
| - Native Audio Pipeline (WASAPI / CoreAudio)                |
| - Desktop Capturer & System Status                          |
| - Secure Storage Management                                 |
+-------------------------------------------------------------+
                              |
                     Strict IPC Allowlist
                              |
+-------------------------------------------------------------+
|                     Preload Script Bridge                   |
| - contextIsolation: true                                    |
| - nodeIntegration: false                                    |
| - sandbox: true                                             |
| - Exposes only window.electronAPI                           |
+-------------------------------------------------------------+
                              |
+-------------------------------------------------------------+
|                    Renderer Process (UI)                    |
| - React 18, TypeScript, Tailwind                            |
| - PracticeArenaPage & CoachingHUD                           |
| - useAudioFrameStream & useRealtimeSession                  |
+-------------------------------------------------------------+
```

---

## 3. Desktop Verification & Test Results

```bash
pnpm --filter desktop test
```
All 15 tests pass across 11 test suites:
- `CoachingHUD.test.tsx`: Verifies fast-path metrics update (~1Hz) independently of LLM latency.
- `useRealtimeSession.test.ts`: Verifies WebSocket initialization and event propagation.
- `useAudioFrameStream.test.ts`: Verifies 18-byte binary framing (`>BBIdI`).
- `audioPipeline.test.ts` & `useAudioCapture.test.ts`: Verifies native audio sample processing and PCM16 clamping.
- `main.test.ts`, `ipc.test.ts`, `directory.test.ts`: Verifies IPC contracts and window configuration.
