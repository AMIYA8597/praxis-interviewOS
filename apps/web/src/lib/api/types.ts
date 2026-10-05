// Shared API response types mirroring backend Pydantic schemas.

export interface CandidateResponse {
  id: string;
  profile_id: string;
  full_name: string;
  headline: string | null;
  location: string | null;
  years_experience: number | null;
  target_roles: string[];
  onboarding_step: string | null;
  onboarding_completed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface SessionResponse {
  id: string;
  session_id: string;
  candidate_id: string;
  job_id: string | null;
  status: string;
  focus_area: string | null;
  mode: string | null;
  interview_type: string | null;
  difficulty: string | null;
  started_at: string | null;
  ended_at: string | null;
  duration_s: number | null;
  turn_count: number | null;
  created_at: string | null;
}

export interface SessionTurnResponse {
  id: string;
  turn_index: number;
  speaker: string | null;
  text: string | null;
  started_at: string | null;
  ended_at: string | null;
  duration_ms: number | null;
  created_at: string | null;
}

export interface SessionDebriefResponse {
  status: 'ready' | 'pending';
  id: string | null;
  session_id: string;
  headline_metrics: HeadlineMetrics | null;
  strengths: string[];
  weaknesses: string[];
  flagged_claims: unknown | null;
  jd_coverage: unknown | null;
  generated_at: string | null;
}

export interface HeadlineMetrics {
  average_wpm: number | null;
  average_filler_rate: number | null;
  average_score: number | null;
}

export interface JobResponse {
  id: string;
  candidate_id: string;
  company: string;
  role_title: string;
  processing_status: string;
  error_message: string | null;
  created_at: string;
}

export interface JobDetailResponse extends JobResponse {
  raw_jd_text: string | null;
  blueprints: JobBlueprintResponse[];
  matches: JobMatchResponse[];
}

export interface JobBlueprintResponse {
  id: string;
  summary: string | null;
  top_skills: unknown | null;
  likely_topics: string[];
  prep_pack: unknown | null;
  requirements: JobRequirementResponse[];
}

export interface JobRequirementResponse {
  id: string;
  skill_text: string;
  category: string | null;
  priority: string | null;
  evidence_quote: string | null;
}

export interface JobMatchResponse {
  id: string;
  overall_score: number | null;
  methodology_version: string | null;
  breakdown: unknown | null;
}

export interface StudyItemResponse {
  id: string;
  topic: string;
  source: string | null;
  prompt: string;
  reference_answer: string | null;
  difficulty: string | null;
  ease_factor: number | null;
  interval_days: number | null;
  repetitions: number | null;
  next_review_at: string | null;
  created_at: string;
}

export interface DashboardStats {
  interviews_completed: number;
  total_sessions: number;
  average_pace_wpm: number;
  filler_word_density: number;
  average_score: number;
  star_consistency: number | null;
}

export interface Paginated<T> {
  items: T[];
  next_cursor: string | null;
}

export interface ApplicationResponse {
  id: string;
  job_id: string;
  company: string;
  role_title: string;
  status: string;
  applied_at: string | null;
  next_action: string | null;
  notes: string | null;
  created_at: string;
}
