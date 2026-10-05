import { apiFetch } from './client';
import type { DashboardStats } from './types';

export async function getDashboardStats(): Promise<DashboardStats> {
  return apiFetch('/analytics/dashboard');
}

export async function getReports(limit = 20): Promise<{ reports: unknown[] }> {
  return apiFetch(`/analytics/reports?limit=${limit}`);
}
