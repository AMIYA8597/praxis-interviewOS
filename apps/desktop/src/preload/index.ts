import { contextBridge, ipcRenderer } from 'electron';

contextBridge.exposeInMainWorld('electronAPI', {
  getSystemStatus: () => ipcRenderer.invoke('get-system-status'),
  getAudioSources: () => ipcRenderer.invoke('get-audio-sources')
});
