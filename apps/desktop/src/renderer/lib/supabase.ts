import { createClient } from '@supabase/supabase-js';

// Use process.env in Jest/Node; Vite replaces import.meta.env at build time.
// This pattern avoids a SyntaxError when ts-jest parses import.meta in CommonJS mode.
declare const __VITE_SUPABASE_URL__: string | undefined;
declare const __VITE_SUPABASE_ANON_KEY__: string | undefined;

function getEnv(key: 'VITE_SUPABASE_URL' | 'VITE_SUPABASE_ANON_KEY'): string {
  if (typeof process !== 'undefined' && process.env[key]) {
    return process.env[key] as string;
  }
  // At runtime in Electron/Vite the values are inlined at build time.
  // The fallback 'missing' causes Supabase to fail clearly rather than silently.
  return 'missing';
}

const customStorage = {
  getItem: async (key: string): Promise<string | null> => {
    if (typeof window !== 'undefined' && window.electronAPI?.storageGet) {
      return window.electronAPI.storageGet(key);
    }
    return null;
  },
  setItem: async (key: string, value: string): Promise<void> => {
    if (typeof window !== 'undefined' && window.electronAPI?.storageSet) {
      await window.electronAPI.storageSet(key, value);
    }
  },
  removeItem: async (key: string): Promise<void> => {
    if (typeof window !== 'undefined' && window.electronAPI?.storageDelete) {
      await window.electronAPI.storageDelete(key);
    }
  },
};

export const supabase = createClient(
  getEnv('VITE_SUPABASE_URL'),
  getEnv('VITE_SUPABASE_ANON_KEY'),
  {
    auth: {
      storage: customStorage,
      autoRefreshToken: true,
      persistSession: true,
      detectSessionInUrl: false,
    },
  },
);
