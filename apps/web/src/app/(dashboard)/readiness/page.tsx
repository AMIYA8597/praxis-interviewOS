"use client";

import React, { useCallback, useEffect, useState } from 'react';
import { apiFetch, ApiError } from '@/lib/api/client';

interface ReadinessData {
  overall_score: number | null;
  confidence: 'low' | 'medium' | 'high' | null;
  technical_score: number | null;
  system_design_score: number | null;
  behavioral_score: number | null;
  communication_score: number | null;
  grounding_score: number | null;
  jd_coverage_score: number | null;
  weakest_domain: string | null;
  recommended_action: string | null;
  computed_at: string;
}

interface PlanSession {
  order: number;
  type: string;
  interview_type: string;
  difficulty: string;
  rationale: string;
}

interface PlanData {
  plan_sessions: PlanSession[];
  generated_at: string;
  completed_count: number;
}

function ScoreBar({ label, score }: { label: string; score: number | null }) {
  const pct = score ?? 0;
  const color = pct >= 70 ? '#22c55e' : pct >= 50 ? '#f59e0b' : '#ef4444';
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-sm">
        <span className="text-gray-400">{label}</span>
        <span className="font-mono" style={{ color }}>{score !== null ? `${score.toFixed(0)}/100` : '—'}</span>
      </div>
      <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${pct}%`, background: color }}
        />
      </div>
    </div>
  );
}

export default function ReadinessPage() {
  const [readiness, setReadiness] = useState<ReadinessData | null>(null);
  const [plan, setPlan] = useState<PlanData | null>(null);
  const [loading, setLoading] = useState(true);
  const [planLoading, setPlanLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiFetch<ReadinessData>('/readiness')
      .then(setReadiness)
      .catch(err => {
        if (err instanceof ApiError && err.status === 404) {
          setReadiness(null);
        } else {
          setError(err instanceof ApiError ? err.message : String(err));
        }
      })
      .finally(() => setLoading(false));

    apiFetch<PlanData>('/readiness/plan')
      .then(setPlan)
      .catch(() => setPlan(null));
  }, []);

  const generatePlan = useCallback(() => {
    setPlanLoading(true);
    apiFetch<PlanData>('/readiness/plan', { method: 'POST' })
      .then(setPlan)
      .catch(err => setError(err instanceof ApiError ? err.message : String(err)))
      .finally(() => setPlanLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center min-h-64">
        <div className="text-gray-400">Loading readiness data…</div>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-4xl mx-auto space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Interview Readiness</h1>
        {readiness && (
          <span className="text-sm text-gray-500">
            Last computed {new Date(readiness.computed_at).toLocaleDateString()}
          </span>
        )}
      </div>

      {error && (
        <div className="bg-red-900/20 border border-red-800 rounded-lg p-4 text-red-300">{error}</div>
      )}

      {!readiness && !loading ? (
        <div className="bg-gray-900 border border-gray-700 rounded-xl p-8 text-center space-y-4">
          <div className="text-5xl">📊</div>
          <h2 className="text-xl font-semibold">No readiness data yet</h2>
          <p className="text-gray-400">Complete at least one practice session to see your readiness score.</p>
        </div>
      ) : readiness ? (
        <>
          {/* Overall score card */}
          <div className="bg-gray-900 border border-gray-700 rounded-xl p-6 flex items-center gap-6">
            <div className="text-center">
              <div
                className="text-5xl font-bold"
                style={{
                  color: (readiness.overall_score ?? 0) >= 70 ? '#22c55e'
                    : (readiness.overall_score ?? 0) >= 50 ? '#f59e0b'
                    : '#ef4444',
                }}
              >
                {readiness.overall_score !== null ? readiness.overall_score.toFixed(0) : '—'}
              </div>
              <div className="text-gray-400 text-sm mt-1">Overall</div>
            </div>
            <div className="flex-1 space-y-1">
              <div className="flex items-center gap-2">
                <span className="font-semibold">Confidence:</span>
                <span className={
                  readiness.confidence === 'high' ? 'text-green-400'
                  : readiness.confidence === 'medium' ? 'text-yellow-400'
                  : 'text-red-400'
                }>{readiness.confidence ?? '—'}</span>
              </div>
              {readiness.weakest_domain && (
                <div className="text-gray-400 text-sm">
                  Weakest area: <span className="text-orange-400">{readiness.weakest_domain}</span>
                </div>
              )}
              {readiness.recommended_action && (
                <div className="text-sm text-blue-300 mt-2">{readiness.recommended_action}</div>
              )}
            </div>
          </div>

          {/* Dimension scores */}
          <div className="bg-gray-900 border border-gray-700 rounded-xl p-6 space-y-4">
            <h2 className="font-semibold text-lg">Score Breakdown</h2>
            <ScoreBar label="Technical" score={readiness.technical_score} />
            <ScoreBar label="System Design" score={readiness.system_design_score} />
            <ScoreBar label="Behavioral" score={readiness.behavioral_score} />
            <ScoreBar label="Communication" score={readiness.communication_score} />
            <ScoreBar label="Answer Grounding" score={readiness.grounding_score} />
            {readiness.jd_coverage_score !== null && (
              <ScoreBar label="JD Coverage" score={readiness.jd_coverage_score} />
            )}
          </div>
        </>
      ) : null}

      {/* Preparation plan */}
      <div className="bg-gray-900 border border-gray-700 rounded-xl p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold text-lg">Preparation Plan</h2>
          <button
            onClick={generatePlan}
            disabled={planLoading}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white rounded-lg text-sm transition-colors"
          >
            {planLoading ? 'Generating…' : plan ? 'Regenerate Plan' : 'Generate Plan'}
          </button>
        </div>

        {plan ? (
          <div className="space-y-3">
            <div className="text-sm text-gray-500">
              Generated {new Date(plan.generated_at).toLocaleDateString()} · {plan.completed_count} sessions completed
            </div>
            {plan.plan_sessions.map((s: PlanSession) => (
              <div
                key={s.order}
                className="flex items-start gap-4 p-4 bg-gray-800 rounded-lg"
              >
                <div className="flex-shrink-0 w-8 h-8 bg-blue-900 text-blue-300 rounded-full flex items-center justify-center text-sm font-bold">
                  {s.order}
                </div>
                <div className="flex-1 space-y-1">
                  <div className="font-medium capitalize">
                    {s.interview_type.replace('_', ' ')} {s.type.replace('_', ' ')}
                  </div>
                  <div className="text-sm text-gray-400 capitalize">{s.difficulty} difficulty</div>
                  <div className="text-sm text-gray-300">{s.rationale}</div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-gray-400 text-sm">
            No plan generated yet. Click "Generate Plan" to get a personalized practice schedule.
          </div>
        )}
      </div>
    </div>
  );
}
