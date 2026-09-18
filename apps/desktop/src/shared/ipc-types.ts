// Sent from renderer to main
export type RendererToMainChannels = {
  'storage:save': (key: string, value: string) => void;
  'storage:get': (key: string) => string | null;
  'auth:logout': () => void;
  'session:start': (sessionId: string) => void;
  'session:stop': () => void;
};

// Sent from main to renderer
export type MainToRendererChannels = {
  'auth:updated': (token: string) => void;
  'session:started': (sessionId: string) => void;
  'app:before-quit': () => void;
};
