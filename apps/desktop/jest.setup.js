// Provide valid placeholder env vars so supabase-js URL validation passes in Jest.
// These never reach a real Supabase instance; they just satisfy the URL format check.
process.env.VITE_SUPABASE_URL = 'https://placeholder.supabase.co';
process.env.VITE_SUPABASE_ANON_KEY = 'placeholder-anon-key';
process.env.VITE_API_URL = 'http://localhost:8000';
process.env.VITE_WS_URL = 'ws://localhost:8001';
