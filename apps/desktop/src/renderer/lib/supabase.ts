import { createClient } from '@supabase/supabase-js';

const customStorage = {
  getItem: async (key: string) => {
    return await window.electronAPI.storageGet(key);
  },
  setItem: async (key: string, value: string) => {
    await window.electronAPI.storageSet(key, value);
  },
  removeItem: async (key: string) => {
    await window.electronAPI.storageDelete(key);
  }
};

export const supabase = createClient(
  import.meta.env.VITE_SUPABASE_URL || 'missing',
  import.meta.env.VITE_SUPABASE_ANON_KEY || 'missing',
  {
    auth: {
      storage: customStorage,
      autoRefreshToken: true,
      persistSession: true,
      detectSessionInUrl: false
    }
  }
);
