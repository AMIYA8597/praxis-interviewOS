import { app, BrowserWindow, ipcMain } from 'electron';
import * as path from 'path';
import { getAudioSources } from './audio';

let mainWindow: BrowserWindow | null = null;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      preload: path.join(__dirname, '../preload/index.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });

  // For Phase 1, just load the Next.js dev server URL if in dev mode
  mainWindow.loadURL('http://localhost:3000');
}

app.whenReady().then(() => {
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

// IPC Health check for Phase 1
ipcMain.handle('get-system-status', () => {
  return {
    os: process.platform,
    electron: process.versions.electron,
    node: process.versions.node
  };
});

// IPC Audio
ipcMain.handle('get-audio-sources', async () => {
  return await getAudioSources();
});
