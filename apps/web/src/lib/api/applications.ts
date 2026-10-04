import { apiFetch } from './client';

export interface ApplicationResponse {
  id: string;
  job_id: string | null;
  company: string | null;
  role: string | null;
  source: string | null;
  status: string | null;
  recruiter: string | null;
  interview_round: string | null;
  next_action: string | null;
  notes: string | null;
  applied_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ApplicationsPage {
  items: ApplicationResponse[];
  applications: ApplicationResponse[];
  next_cursor: string | null;
}

export async function listApplications(cursor?: string, limit = 20): Promise<ApplicationsPage> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (cursor) params.set('cursor', cursor);
  return apiFetch(`/applications?${params}`);
}

export async function createApplication(data: {
  company: string;
  role: string;
  job_id?: string;
  status?: string;
  next_action?: string;
  notes?: string;
}): Promise<ApplicationResponse> {
  return apiFetch('/applications', { method: 'POST', body: JSON.stringify(data) });
}

export async function updateApplication(id: string, data: Partial<{
  company: string;
  role: string;
  status: string;
  next_action: string;
  notes: string;
}>): Promise<ApplicationResponse> {
  return apiFetch(`/applications/${id}`, { method: 'PATCH', body: JSON.stringify(data) });
}
