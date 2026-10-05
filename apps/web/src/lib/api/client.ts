/**
 * Phase 115 — PRAXIS typed API client.
 *
 * Single entry point for all backend calls. Features:
 * - Auth token attached on every request (from Supabase session)
 * - Request-ID generated and propagated (X-Request-ID header)
 * - Configurable timeout via AbortController
 * - Exponential-backoff retry on 429 / 5xx (non-POST by default)
 * - Structured ApiError with status + detail
 * - Cancellation via AbortSignal
 * - Pagination helper
 */

import { supabase } from '@/lib/supabase';

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000';

const DEFAULT_TIMEOUT_MS = 15_000;
const MAX_RETRIES = 2;
const RETRY_DELAY_BASE_MS = 500;

// ── Types ─────────────────────────────────────────────────────────────────────

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
    public readonly requestId: string,
    public readonly body?: unknown,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export interface FetchOptions extends Omit<RequestInit, 'signal'> {
  /** Override timeout in ms (default 15s). */
  timeoutMs?: number;
  /** External abort signal (merged with internal timeout signal). */
  signal?: AbortSignal;
  /** Disable retry (always disabled for POST/PUT/PATCH/DELETE). */
  noRetry?: boolean;
}

export interface PagedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
}

// ── Internals ──────────────────────────────────────────────────────────────────

function generateRequestId(): string {
  return crypto.randomUUID?.() ?? Math.random().toString(36).slice(2);
}

async function getAuthHeaders(): Promise<Record<string, string>> {
  const {
    data: { session },
  } = await supabase.auth.getSession();
  if (!session?.access_token) return {};
  return { Authorization: `Bearer ${session.access_token}` };
}

function isSafeMethod(method: string): boolean {
  return ['GET', 'HEAD', 'OPTIONS'].includes(method.toUpperCase());
}

function shouldRetry(status: number, attempt: number, safe: boolean): boolean {
  if (!safe) return false;
  if (attempt >= MAX_RETRIES) return false;
  return status === 429 || status >= 500;
}

async function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// ── Core fetch ──────────────────────────────────────────────────────────────

export async function apiFetch<T>(
  path: string,
  options: FetchOptions = {},
): Promise<T> {
  const {
    timeoutMs = DEFAULT_TIMEOUT_MS,
    signal: externalSignal,
    noRetry = false,
    ...fetchOptions
  } = options;

  const method = (fetchOptions.method ?? 'GET').toUpperCase();
  const isFormData = fetchOptions.body instanceof FormData;
  const requestId = generateRequestId();

  const authHeaders = await getAuthHeaders();
  const headers: Record<string, string> = {
    'X-Request-ID': requestId,
    ...authHeaders,
    ...(fetchOptions.headers as Record<string, string>),
  };
  if (!isFormData && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json';
  }

  const url = `${API_BASE}/api/v1${path}`;

  for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), timeoutMs);

    // Merge external signal.
    if (externalSignal) {
      externalSignal.addEventListener('abort', () => controller.abort(), { once: true });
    }

    let res: Response;
    try {
      res = await fetch(url, {
        ...fetchOptions,
        method,
        headers,
        signal: controller.signal,
      });
    } catch (err: unknown) {
      clearTimeout(timeout);
      if (
        err instanceof DOMException &&
        err.name === 'AbortError' &&
        externalSignal?.aborted
      ) {
        throw err; // propagate caller-initiated cancellation
      }
      if (attempt < MAX_RETRIES && !noRetry && isSafeMethod(method)) {
        await sleep(RETRY_DELAY_BASE_MS * 2 ** attempt);
        continue;
      }
      throw new ApiError(0, 'Network error', requestId, { cause: String(err) });
    } finally {
      clearTimeout(timeout);
    }

    if (!res.ok) {
      if (shouldRetry(res.status, attempt, isSafeMethod(method) && !noRetry)) {
        const retryAfter = res.headers.get('Retry-After');
        const delay = retryAfter
          ? parseInt(retryAfter, 10) * 1000
          : RETRY_DELAY_BASE_MS * 2 ** attempt;
        await sleep(delay);
        continue;
      }

      let body: unknown;
      try {
        body = await res.json();
      } catch {
        /* ignore */
      }
      const detail = (body as { detail?: string })?.detail ?? res.statusText;
      throw new ApiError(res.status, detail, requestId, body);
    }

    if (res.status === 204) return undefined as T;
    return res.json() as Promise<T>;
  }

  // Should not reach here.
  throw new ApiError(0, 'Max retries exceeded', requestId);
}

// ── Convenience wrappers ─────────────────────────────────────────────────────

export const api = {
  get: <T>(path: string, opts?: FetchOptions) =>
    apiFetch<T>(path, { method: 'GET', ...opts }),

  post: <T>(path: string, body?: unknown, opts?: FetchOptions) =>
    apiFetch<T>(path, {
      method: 'POST',
      body: body ? JSON.stringify(body) : undefined,
      ...opts,
    }),

  put: <T>(path: string, body?: unknown, opts?: FetchOptions) =>
    apiFetch<T>(path, {
      method: 'PUT',
      body: body ? JSON.stringify(body) : undefined,
      ...opts,
    }),

  patch: <T>(path: string, body?: unknown, opts?: FetchOptions) =>
    apiFetch<T>(path, {
      method: 'PATCH',
      body: body ? JSON.stringify(body) : undefined,
      ...opts,
    }),

  delete: <T>(path: string, opts?: FetchOptions) =>
    apiFetch<T>(path, { method: 'DELETE', ...opts }),

  upload: <T>(path: string, formData: FormData, opts?: FetchOptions) =>
    apiFetch<T>(path, { method: 'POST', body: formData, ...opts }),
};
