import { apiFetch } from './client';
import type { StudyItemResponse, Paginated } from './types';

export async function listStudyItems(cursor?: string, limit = 20): Promise<Paginated<StudyItemResponse>> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (cursor) params.set('cursor', cursor);
  return apiFetch(`/study/items?${params}`);
}

export async function getDueItems(): Promise<Paginated<StudyItemResponse>> {
  return apiFetch('/study/items/due');
}

export async function reviewItem(id: string, quality: number): Promise<{
  status: string;
  id: string;
  interval_days: number;
  repetitions: number;
  ease_factor: number;
  next_review_at: string;
}> {
  return apiFetch(`/study/items/${id}/review`, {
    method: 'POST',
    body: JSON.stringify({ quality }),
  });
}
