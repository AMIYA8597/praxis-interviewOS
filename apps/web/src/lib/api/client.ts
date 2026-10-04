import { supabase } from '@/lib/supabase';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
    public readonly body?: unknown,
  ) {
    super(message);
  }
}

async function getAuthHeader(): Promise<Record<string, string>> {
  const { data: { session } } = await supabase.auth.getSession();
  if (!session?.access_token) return {};
  return { Authorization: `Bearer ${session.access_token}` };
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const authHeaders = await getAuthHeader();
  // Don't force Content-Type for FormData — browser sets it with boundary.
  const isFormData = options.body instanceof FormData;
  const headers: Record<string, string> = {
    ...authHeaders,
    ...(options.headers as Record<string, string>),
  };
  if (!isFormData) {
    headers['Content-Type'] = 'application/json';
  }
  const res = await fetch(`${API_BASE}/api/v1${path}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    let body: unknown;
    try { body = await res.json(); } catch { /* ignore */ }
    const detail = (body as { detail?: string })?.detail ?? res.statusText;
    throw new ApiError(res.status, detail, body);
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}
