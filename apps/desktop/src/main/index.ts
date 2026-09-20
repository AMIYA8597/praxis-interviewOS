import { app, BrowserWindow, ipcMain, Menu, globalShortcut, desktopCapturer } from 'electron';
import * as path from 'path';
import isDev from 'electron-is-dev';
import { getAudioSources, setupAudioCapture } from './audio';
import { getCredential, saveCredential } from './storage';
import { setupScreenshotCapture, cleanupScreenshotCapture } from './capture';

let mainWindow: BrowserWindow | null = null;
let isSessionActive = false; // Mock for now

const createWindow = () => {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    webPreferences: {
      preload: path.join(__dirname, '../preload/index.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true
    }
  });
  
  const startUrl = isDev
    ? 'http://localhost:5173'  // Vite dev server
    : `file://${path.join(__dirname, '../renderer/index.html')}`;
  
  mainWindow.loadURL(startUrl);
  if (isDev) mainWindow.webContents.openDevTools();

  mainWindow.on('close', (event) => {
    if (isSessionActive) {
      event.preventDefault();
      mainWindow?.webContents.send('app.confirmQuit');
    }
  });

  setupScreenshotCapture(mainWindow);
  setupAudioCapture();
};

app.whenReady().then(() => {
  createWindow();

  const menu = Menu.buildFromTemplate([
    {
      label: 'File',
      submenu: [
        { label: 'Exit', accelerator: 'CmdOrCtrl+Q', click: () => app.quit() }
      ]
    },
    ...(isDev ? [{
      label: 'Dev',
      submenu: [
        { role: 'toggleDevTools' as const }
      ]
    }] : [])
  ]);
  
  Menu.setApplicationMenu(menu);

  app.on('activate', () => {
    if (mainWindow === null) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});

app.on('will-quit', () => {
  cleanupScreenshotCapture();
});

// IPC Handlers
ipcMain.handle('system.getStatus', () => {
  return {
    os: process.platform,
    electron: process.versions.electron,
    node: process.versions.node
  };
});

ipcMain.handle('audio.getSources', async () => {
  return await getAudioSources();
});

ipcMain.handle('audio.startCapture', (_event, sourceId: string) => {
  // Stub for audio start capture
});

ipcMain.handle('audio.stopCapture', () => {
  // Stub for audio stop capture
});

ipcMain.handle('screen.getSources', async () => {
  try {
    const sources = await desktopCapturer.getSources({ types: ['screen', 'window'] });
    return sources.map(s => ({ id: s.id, name: s.name }));
  } catch (e) {
    return [];
  }
});

ipcMain.handle('screen.captureNow', async () => {
  // Explicitly trigger a capture without global shortcut
  try {
    const sources = await desktopCapturer.getSources({ types: ['screen'], thumbnailSize: { width: 1920, height: 1080 } });
    if (sources.length > 0) {
      const dataUrl = sources[0].thumbnail.toDataURL();
      mainWindow?.webContents.send('screenshot.captureReady', dataUrl);
    }
  } catch (e) {
    console.error("Manual capture failed:", e);
  }
});

ipcMain.handle('shortcut.register', (_event, name: string, accelerator: string) => {
  globalShortcut.register(accelerator, () => {
    mainWindow?.webContents.send(`shortcut.${name}`);
  });
});

ipcMain.handle('shortcut.unregister', (_event, name: string) => {
  // Can't easily map name to accelerator here without state, but stub for now.
});

ipcMain.handle('storage.set', (_event, key: string, value: string) => {
  saveCredential(key, value);
});

ipcMain.handle('storage.get', (_event, key: string) => {
  return getCredential(key);
});

ipcMain.handle('storage.delete', (_event, key: string) => {
  saveCredential(key, '');
});

ipcMain.handle('auth.logout', (_event) => {
  saveCredential('auth-token', '');
  mainWindow?.webContents.send('auth.updated', '');
});

// Keep backward compatible session handling temporarily if renderer still uses it?
// Actually phase 4.3 handles fixing the renderer.
ipcMain.handle('session.start', (_event, sessionId: string) => {
  isSessionActive = true;
  mainWindow?.webContents.send('session.started', sessionId);
});

ipcMain.handle('session.stop', () => {
  isSessionActive = false;
});
