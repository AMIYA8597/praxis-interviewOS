/**
 * Phase 117 — Desktop Production Configuration.
 *
 * All endpoints come from environment variables set at build time.
 * No localhost fallbacks in production builds.
 * No mock tokens.
 */

function requireEnv(name: string, devFallback?: string): string {
  const value = process.env[name] ?? import.meta.env?.[name];
  if (value) return value;
  if (devFallback && process.env.NODE_ENV === 'development') {
    console.warn(`[config] ${name} not set — using dev fallback: ${devFallback}`);
    return devFallback;
  }
  throw new Error(
    `[PRAXIS] Required environment variable ${name} is not set. ` +
    'Production desktop builds require all endpoint variables to be configured.'
  );
}

export const appConfig = {
  /** Supabase project URL for authentication. */
  supabaseUrl: requireEnv('VITE_SUPABASE_URL', 'http://localhost:54321'),

  /** Supabase anon key (public, safe in desktop). */
  supabaseAnonKey: requireEnv('VITE_SUPABASE_ANON_KEY', 'local-anon-key'),

  /** REST API base URL. */
  apiUrl: requireEnv('VITE_API_URL', 'http://localhost:8000'),

  /** WebSocket realtime URL. */
  realtimeUrl: requireEnv('VITE_REALTIME_URL', 'ws://localhost:8080'),

  /** Web app URL loaded in the Electron window in production. */
  webAppUrl: requireEnv('VITE_WEB_APP_URL', 'http://localhost:5173'),

  /** App environment. */
  appEnv: (process.env.VITE_APP_ENV ?? 'development') as 'development' | 'staging' | 'production',

  isProduction(): boolean {
    return this.appEnv === 'production';
  },

  isDevelopment(): boolean {
    return this.appEnv === 'development';
  },
} as const;
