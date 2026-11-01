# PRAXIS InterviewOS — Electron Desktop Security Specification

**Milestone**: Phase 4 — Enterprise Security Engineering  
**Branch**: `phase4-security`  
**Date**: 2026-11-01  
**Classification**: DESKTOP SECURITY AUDIT & SPECIFICATION  

---

## 1. Electron Security Configuration

The desktop application (`apps/desktop`) enforces all Chromium and Electron security baselines in `apps/desktop/src/main/index.ts`:

```typescript
const createWindow = () => {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    webPreferences: {
      preload: path.join(__dirname, '../preload/index.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      webSecurity: true,
      allowRunningInsecureContent: false,
    }
  });
};
```

---

## 2. IPC Privilege Separation & Allowlist

The preload bridge (`apps/desktop/src/preload/index.ts`) exposes only a minimal, explicit IPC surface via `contextBridge.exposeInMainWorld('electronAPI', ...)`:
- `storageGet(key)`, `storageSet(key, value)`, `storageDelete(key)`
- `authLogout()`
- `audioGetSources()`, `audioStartCapture(sourceId)`, `audioStopCapture()`
- `screenGetSources()`, `screenCaptureNow()`
- `systemGetStatus()`
- `shortcutRegister(name, accel)`, `shortcutUnregister(name)`

### Security Rules Enforced:
1. **No Direct `ipcRenderer` Access**: Renderer cannot invoke arbitrary IPC channels.
2. **No Shell Execution**: No child process execution or command line spawning is reachable from renderer.
3. **No Unrestricted Filesystem Access**: File operations are constrained to encrypted credentials storage.
4. **Zero Proctor Evasion (ADR-001)**: No screen-recording bypasses, window invisibility hooks, or proctor evasion capabilities exist.
