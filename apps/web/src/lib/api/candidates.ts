import { apiFetch } from './client';
import type { CandidateResponse } from './types';

export async function getMe(): Promise<CandidateResponse> {
  return apiFetch('/candidates/me');
}

export async function updateMe(data: {
  full_name?: string;
  headline?: string;
  location?: string;
  years_experience?: number;
  target_roles?: string[];
}): Promise<CandidateResponse> {
  return apiFetch('/candidates/me', { method: 'PATCH', body: JSON.stringify(data) });
}
