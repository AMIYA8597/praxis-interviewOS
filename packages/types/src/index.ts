/**
 * PRAXIS InterviewOS — Core Integration Types
 * Authoritative contracts matching docs/PHASE2_HANDOFF_PHASE3.md
 */

// ==========================================
// 1. Metrics & Coaching
// ==========================================

export type MeasurementStatus = 'MEASURED' | 'ESTIMATED' | 'DEGRADED' | 'UNAVAILABLE';

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
  duration_s?: number;
  measurement_status?: MeasurementStatus;
}

// ==========================================
// 2. Realtime Transcripts
// ==========================================

export interface TranscriptSegment {
  segment_id: string;
  is_interim: boolean;
  speaker: string;
  text: string;
  confidence: number;
  timestamp?: number;
}

// ==========================================
// 3. Evidence Grounding & Claims
// ==========================================

export type ClaimClassification =
  | 'SUPPORTED'
  | 'PARTIALLY_SUPPORTED'
  | 'UNSUPPORTED'
  | 'CONTRADICTED'
  | 'UNCERTAIN';

export interface ClaimGrounding {
  claim_text: string;
  classification: ClaimClassification;
  supported: boolean;
  confidence: number;
  source_chunk_id?: string | null;
  source_project_id?: string | null;
  source_excerpt?: string | null;
}

// ==========================================
// 4. Answer Evaluation & STAR Completeness
// ==========================================

export interface STARCompleteness {
  situation: boolean;
  task: boolean;
  action: boolean;
  result: boolean;
}

export interface EvaluationScore {
  rubric_version: string;
  measurement_status: MeasurementStatus;
  relevance: number | null;
  correctness: number | null;
  structure: number | null;
  specificity: number | null;
  grounding: number | null;
  conciseness: number | null;
  overall: number | null;
  rationale: string;
  star_completeness?: STARCompleteness;
  claims?: ClaimGrounding[];
}

// ==========================================
// 5. PRAXIS Readiness Estimate
// ==========================================

export interface ReadinessDimension {
  name: string;
  score: number | null;
  confidence: number;
  description?: string;
}

export type ReadinessStatus = 'MEASURED' | 'ESTIMATED' | 'INSUFFICIENT_EVIDENCE';

export interface ReadinessResponse {
  candidate_id: string;
  readiness_score: number | null;
  status: ReadinessStatus;
  disclaimer: string;
  session_count: number;
  dimensions: Record<string, ReadinessDimension>;
  recommended_actions: string[];
  updated_at?: string;
}

// ==========================================
// 6. Realtime WebSocket Events
// ==========================================

export type RealtimeClientEventType =
  | 'audio.frame'
  | 'candidate.text_answer'
  | 'session.complete';

export type RealtimeServerEventType =
  | 'audio.frame_ack'
  | 'transcript.partial'
  | 'transcript.final'
  | 'coaching.metrics'
  | 'interviewer.text'
  | 'state.transitioned';

export type RealtimeEventType = RealtimeClientEventType | RealtimeServerEventType;

export interface RealtimeEvent<T = any> {
  type: RealtimeEventType;
  session_id: string;
  sequence: number;
  payload: T;
}

// ==========================================
// 7. Session States
// ==========================================

export type SessionState =
  | 'INITIALIZING'
  | 'AWAITING_ANSWER'
  | 'CANDIDATE_TURN'
  | 'ANALYZING_TURN'
  | 'INTERVIEWER_TURN'
  | 'COMPLETED'
  | 'FAILED';
