export type RendererToMainChannels = {
  'storage.get': (key: string) => string | null;
  'storage.set': (key: string, value: string) => void;
  'storage.delete': (key: string) => void;
  'auth.logout': () => void;
  'audio.getSources': () => any;
  'audio.startCapture': (sourceId: string) => void;
  'audio.stopCapture': () => void;
  'screen.getSources': () => any;
  'screen.captureNow': () => void;
  'shortcut.register': (name: string, accelerator: string) => void;
  'shortcut.unregister': (name: string) => void;
  'system.getStatus': () => any;
};

export type MainToRendererChannels = {
  'auth.updated': (token: string) => void;
  'audio.meterLevel': (rms: number) => void;
  'audio.frameAck': (sequence: number) => void;
  'screenshot.captureReady': (image: string) => void;
  'session.started': (sessionId: string) => void;
  'app.beforeQuit': () => void;
  'app.confirmQuit': () => void;
};
