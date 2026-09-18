export interface SessionMetrics {
  wpm?: number;
  filler_rate?: number;
  longest_pause_ms?: number;
  hedge_count?: number;
  sentence_count?: number;
  avg_sentence_length?: number;
  pause_ratio?: number;
  time_to_first_word_ms?: number;
  wpm_variance?: number;
}

export interface TranscriptSegment {
  segment_id: string;
  is_interim: boolean;
  speaker: string;
  text: string;
  confidence: number;
}
