import { app, ipcMain } from 'electron';

jest.mock('electron', () => ({
  app: { 
    on: jest.fn(), 
    quit: jest.fn(), 
    whenReady: jest.fn().mockResolvedValue(undefined),
    getPath: jest.fn().mockReturnValue('/mock/path')
  },
  BrowserWindow: jest.fn().mockImplementation(() => ({
    loadURL: jest.fn(),
    on: jest.fn(),
    webContents: {
      send: jest.fn(),
      openDevTools: jest.fn()
    }
  })),
  ipcMain: { handle: jest.fn(), on: jest.fn() },
  Menu: { setApplicationMenu: jest.fn(), buildFromTemplate: jest.fn() },
  globalShortcut: { register: jest.fn() },
  safeStorage: { 
    encryptString: jest.fn().mockReturnValue(Buffer.from('encrypted')), 
    decryptString: jest.fn().mockReturnValue('decrypted') 
  }
}));

// Mock audio to prevent issues with desktopCapturer
jest.mock('../src/main/audio', () => ({
  getAudioSources: jest.fn(),
  setupAudioCapture: jest.fn()
}));

jest.mock('../src/main/capture', () => ({
  setupScreenshotCapture: jest.fn(),
  cleanupScreenshotCapture: jest.fn()
}));

jest.mock('electron-is-dev', () => true);

describe('Main Process', () => {
  it('registers IPC handler for storage.set', () => {
    require('../src/main/index');
    expect(ipcMain.handle).toHaveBeenCalledWith(
      'storage.set',
      expect.any(Function)
    );
  });
});
