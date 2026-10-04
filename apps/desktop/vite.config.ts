import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
// @ts-ignore
import electronVitePlugin from 'electron-vite'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  return {
    plugins: [react(), electronVitePlugin()],
    build: {
      target: 'chrome120',
    },
    // Expose VITE_* vars via process.env so that the safe getEnv() helper
    // in supabase.ts and hooks works in both Vite and Jest (CommonJS) contexts.
    define: {
      'process.env.VITE_SUPABASE_URL': JSON.stringify(env.VITE_SUPABASE_URL ?? ''),
      'process.env.VITE_SUPABASE_ANON_KEY': JSON.stringify(env.VITE_SUPABASE_ANON_KEY ?? ''),
      'process.env.VITE_API_URL': JSON.stringify(env.VITE_API_URL ?? ''),
      'process.env.VITE_WS_URL': JSON.stringify(env.VITE_WS_URL ?? ''),
    },
  }
})
