import { apiFetch } from './client';
import type { JobResponse, JobDetailResponse, Paginated } from './types';

export async function listJobs(cursor?: string, limit = 20): Promise<Paginated<JobResponse>> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (cursor) params.set('cursor', cursor);
  return apiFetch(`/jobs?${params}`);
}

export async function getJob(id: string): Promise<JobDetailResponse> {
  return apiFetch(`/jobs/${id}`);
}

export async function createJob(payload: {
  company: string;
  role_title: string;
  description: string;
}): Promise<{ id: string; status: string; message: string }> {
  return apiFetch('/jobs', { method: 'POST', body: JSON.stringify(payload) });
}
