# PRAXIS InterviewOS — Phase 3 Electron Security Baseline

**Milestone**: Phase 3 — Web & Desktop Client Engineering  
**Branch**: `phase3-web-desktop`  
**Date**: 2026-11-01  
**Classification**: SECURITY AUDIT & SPECIFICATION  

---

## 1. Security Invariants & Compliance

The desktop application is built in strict adherence to Chromium and Electron security best practices.

### 1.1 Process Isolation Invariants
| Setting | Configured Value | Security Purpose |
| :--- | :--- | :--- |
| `contextIsolation` | `true` | Prevents renderer scripts from tampering with Electron internals |
| `nodeIntegration` | `false` | Disables Node.js runtime access inside the DOM / renderer |
| `sandbox` | `true` | Restricts renderer to OS-level sandboxing limits |
| `webSecurity` | `true` | Enforces standard Same-Origin Policy (SOP) |
| `allowRunningInsecureContent` | `false` | Blocks mixed-content HTTP scripts inside HTTPS |

### 1.2 IPC Channel Allowlist
Renderer access to Electron capabilities is strictly constrained to the exposed `electronAPI` methods in `apps/desktop/src/preload/index.ts`:
- Storage: `storageGet`, `storageSet`, `storageDelete`
- Auth: `authLogout`
- Audio: `audioGetSources`, `audioStartCapture`, `audioStopCapture`
- Screen: `screenGetSources`, `screenCaptureNow`
- System: `systemGetStatus`
- Shortcuts: `shortcutRegister`, `shortcutUnregister`
- Listeners: `onAuthUpdated`, `onAudioMeterLevel`, `onAudioFrameAck`, `onScreenshotCaptureReady`, `onSessionStarted`, `onAppConfirmQuit`

No raw `ipcRenderer.send()` or `ipcRenderer.on()` is accessible to renderer scripts.

---

## 2. Ethical Compliance: Zero Proctor Evasion (ADR-001)

PRAXIS is designed exclusively for transparent candidate preparation and coaching.
The application explicitly does NOT and will NEVER contain:
- Proctor evasion or concealment techniques.
- Undetectable transparency or window cloaking against screen sharing.
- Audio interception designed to hide AI assistance during formal assessments.
- Deceptive identity spoofing or automated answer generation during live interviews.
