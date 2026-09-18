import { app, BrowserWindow, ipcMain, Menu, globalShortcut } from 'electron';
import * as path from 'path';
import isDev from 'electron-is-dev';
import { getAudioSources } from './audio';
import { getCredential, saveCredential } from './storage';

let mainWindow: BrowserWindow | null = null;
let isSessionActive = false; // Mock for now

const createWindow = () => {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    webPreferences: {
      preload: path.join(__dirname, '../preload/index.js'),
      contextIsolation: true,
      // @ts-ignore
      enableRemoteModule: false,
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
      mainWindow?.webContents.send('app:confirm-quit');
    }
  });
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

  globalShortcut.register('CmdOrCtrl+Shift+I', () => {
    mainWindow?.webContents.send('hotkey:toggle-interview');
  });

  app.on('activate', () => {
    if (mainWindow === null) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});

// IPC Handlers
ipcMain.handle('get-system-status', () => {
  return {
    os: process.platform,
    electron: process.versions.electron,
    node: process.versions.node
  };
});

ipcMain.handle('get-audio-sources', async () => {
  return await getAudioSources();
});

ipcMain.handle('storage:save', (_event, key: string, value: string) => {
  saveCredential(key, value);
});

ipcMain.handle('storage:get', (_event, key: string) => {
  return getCredential(key);
});

ipcMain.handle('auth:logout', (_event) => {
  saveCredential('auth-token', '');
  mainWindow?.webContents.send('auth:updated', '');
});
