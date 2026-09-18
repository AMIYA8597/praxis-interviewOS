export interface CoachingMetrics {
  wpm: number;
  filler_words_count: number;
  longest_pause_ms: number;
  is_speaking: boolean;
}

export interface SessionRecord {
  id: string;
  candidate_id: string;
  created_at: string;
  status: 'active' | 'completed';
}

export interface AnswerScore {
  relevance: number;
  correctness: number;
  structure: number;
  grounding: number;
  specificity: number;
  conciseness: number;
  overall: number;
  rationale: string;
}
