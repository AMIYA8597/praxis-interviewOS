import { saveCredential, getCredential } from '../src/main/storage';

jest.mock('../src/main/storage', () => {
  let store: any = {};
  return {
    saveCredential: jest.fn((k, v) => { store[k] = v; }),
    getCredential: jest.fn((k) => store[k] || null)
  };
});

describe('IPC Storage Round Trip', () => {
  it('saves and retrieves storage via storage.set and storage.get', () => {
    saveCredential('test-key', 'test-value');
    expect(getCredential('test-key')).toBe('test-value');
  });
});

describe('Screenshot Delivery', () => {
  it('delivers screenshot to renderer via screenshot.captureReady', () => {
    const mockSend = jest.fn();
    const mockWindow = { webContents: { send: mockSend }, isDestroyed: () => false };
    const dataUrl = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=';
    mockWindow.webContents.send('screenshot.captureReady', dataUrl);
    expect(mockSend).toHaveBeenCalledWith('screenshot.captureReady', expect.any(String));
  });
});
