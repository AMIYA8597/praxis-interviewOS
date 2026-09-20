import { contextBridge, ipcRenderer } from 'electron';

contextBridge.exposeInMainWorld('electronAPI', {
  // Renderer to Main
  storageGet: (key: string) => ipcRenderer.invoke('storage.get', key),
  storageSet: (key: string, value: string) => ipcRenderer.invoke('storage.set', key, value),
  storageDelete: (key: string) => ipcRenderer.invoke('storage.delete', key),
  
  authLogout: () => ipcRenderer.invoke('auth.logout'),
  
  audioGetSources: () => ipcRenderer.invoke('audio.getSources'),
  audioStartCapture: (sourceId: string) => ipcRenderer.invoke('audio.startCapture', sourceId),
  audioStopCapture: () => ipcRenderer.invoke('audio.stopCapture'),
  
  screenGetSources: () => ipcRenderer.invoke('screen.getSources'),
  screenCaptureNow: () => ipcRenderer.invoke('screen.captureNow'),
  
  shortcutRegister: (name: string, accelerator: string) => ipcRenderer.invoke('shortcut.register', name, accelerator),
  shortcutUnregister: (name: string) => ipcRenderer.invoke('shortcut.unregister', name),
  
  systemGetStatus: () => ipcRenderer.invoke('system.getStatus'),

  // Main to Renderer Listeners
  onAuthUpdated: (callback: (token: string) => void) => {
    ipcRenderer.on('auth.updated', (_event, token) => callback(token));
  },
  onAudioMeterLevel: (callback: (rms: number) => void) => {
    ipcRenderer.on('audio.meterLevel', (_event, rms) => callback(rms));
  },
  onAudioFrameAck: (callback: (sequence: number) => void) => {
    ipcRenderer.on('audio.frameAck', (_event, sequence) => callback(sequence));
  },
  onScreenshotCaptureReady: (callback: (image: string) => void) => {
    ipcRenderer.on('screenshot.captureReady', (_event, image) => callback(image));
  },
  onSessionStarted: (callback: (sessionId: string) => void) => {
    ipcRenderer.on('session.started', (_event, sessionId) => callback(sessionId));
  },
  onAppBeforeQuit: (callback: () => void) => {
    ipcRenderer.on('app.beforeQuit', () => callback());
  },
  onAppConfirmQuit: (callback: () => void) => {
    ipcRenderer.on('app.confirmQuit', () => callback());
  },
});
