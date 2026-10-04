import { apiFetch } from './client';
import type {
  SessionResponse,
  SessionTurnResponse,
  SessionDebriefResponse,
  Paginated,
} from './types';

export async function listSessions(cursor?: string, limit = 20): Promise<Paginated<SessionResponse>> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (cursor) params.set('cursor', cursor);
  return apiFetch(`/sessions?${params}`);
}

export async function getSession(id: string): Promise<SessionResponse> {
  return apiFetch(`/sessions/${id}`);
}

export async function getSessionTurns(id: string): Promise<SessionTurnResponse[]> {
  return apiFetch(`/sessions/${id}/turns`);
}

export async function getSessionDebrief(id: string): Promise<SessionDebriefResponse> {
  return apiFetch(`/sessions/${id}/debrief`);
}

export async function createSession(payload: {
  job_id?: string;
  mode?: string;
  interview_type?: string;
  difficulty?: string;
}): Promise<SessionResponse> {
  return apiFetch('/sessions', { method: 'POST', body: JSON.stringify(payload) });
}

export async function endSession(id: string): Promise<{ id: string; status: string; debrief_status: string }> {
  return apiFetch(`/sessions/${id}/end`, { method: 'POST' });
}
