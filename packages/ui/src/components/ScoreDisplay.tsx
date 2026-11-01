import React from 'react';
import type { EvaluationScore, MeasurementStatus, STARCompleteness } from '@praxis/types';

export interface ScoreDisplayProps {
  evaluation?: EvaluationScore;
  overall?: number | null;
  relevance?: number | null;
  correctness?: number | null;
  structure?: number | null;
  specificity?: number | null;
  grounding?: number | null;
  conciseness?: number | null;
  rationale?: string;
  measurementStatus?: MeasurementStatus;
  starCompleteness?: STARCompleteness;
  className?: string;
}

const DIMENSIONS: Array<{ key: keyof EvaluationScore; label: string }> = [
  { key: 'relevance', label: 'Relevance' },
  { key: 'correctness', label: 'Technical Correctness' },
  { key: 'structure', label: 'Structure & Delivery' },
  { key: 'specificity', label: 'Specificity & Detail' },
  { key: 'grounding', label: 'Evidence Grounding' },
  { key: 'conciseness', label: 'Conciseness & Clarity' },
];

export const ScoreDisplay: React.FC<ScoreDisplayProps> = ({
  evaluation,
  overall: propOverall,
  relevance: propRelevance,
  correctness: propCorrectness,
  structure: propStructure,
  specificity: propSpecificity,
  grounding: propGrounding,
  conciseness: propConciseness,
  rationale: propRationale,
  measurementStatus: propStatus,
  starCompleteness: propStar,
  className = '',
}) => {
  const status: MeasurementStatus = evaluation?.measurement_status || propStatus || 'MEASURED';
  const overall = evaluation?.overall ?? propOverall;
  const rationale = evaluation?.rationale || propRationale;
  const star = evaluation?.star_completeness || propStar;

  const getDimensionScore = (key: string): number | null => {
    if (evaluation && key in evaluation) {
      const val = (evaluation as any)[key];
      return typeof val === 'number' ? val : null;
    }
    const propMap: Record<string, number | null | undefined> = {
      relevance: propRelevance,
      correctness: propCorrectness,
      structure: propStructure,
      specificity: propSpecificity,
      grounding: propGrounding,
      conciseness: propConciseness,
    };
    return propMap[key] ?? null;
  };

  const isUnavailable = status === 'UNAVAILABLE';
  const isEstimated = status === 'ESTIMATED';
  const isDegraded = status === 'DEGRADED';

  const formatScore = (val: number | null | undefined): string => {
    if (val === null || val === undefined || isUnavailable) return 'N/A';
    return `${Math.round(val * 100)}%`;
  };

  return (
    <div
      data-testid="score-display"
      className={`bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-lg p-5 shadow-sm ${className}`}
    >
      {/* Header with Overall & Status */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-zinc-100 dark:border-zinc-800 gap-3">
        <div>
          <h3 className="text-base font-semibold text-zinc-900 dark:text-zinc-100">
            Answer Evaluation Breakdown
          </h3>
          <p className="text-xs text-zinc-500">
            Multi-dimensional rubric scoring backed by Phase 2 AI Gateway
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Status Badge */}
          <span
            data-testid="measurement-status-badge"
            className={`px-2.5 py-1 text-xs font-semibold rounded-full border ${
              status === 'MEASURED'
                ? 'bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-800'
                : isEstimated
                ? 'bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-800'
                : isDegraded
                ? 'bg-orange-50 text-orange-700 border-orange-200 dark:bg-orange-950/40 dark:text-orange-300 dark:border-orange-800'
                : 'bg-zinc-100 text-zinc-600 border-zinc-200 dark:bg-zinc-800 dark:text-zinc-400'
            }`}
          >
            {status}
          </span>

          {/* Overall Score Badge */}
          <div className="flex items-baseline gap-1 bg-zinc-50 dark:bg-zinc-800/60 px-3 py-1.5 rounded-md border border-zinc-200/70 dark:border-zinc-700/60">
            <span className="text-xs text-zinc-500 font-medium">Overall:</span>
            <span
              data-testid="overall-score"
              className={`text-lg font-bold font-mono ${
                isUnavailable
                  ? 'text-zinc-400'
                  : (overall ?? 0) >= 0.75
                  ? 'text-emerald-600 dark:text-emerald-400'
                  : (overall ?? 0) >= 0.5
                  ? 'text-amber-600 dark:text-amber-400'
                  : 'text-rose-600 dark:text-rose-400'
              }`}
            >
              {formatScore(overall)}
            </span>
          </div>
        </div>
      </div>

      {/* Degradation Warning Banner */}
      {isDegraded && (
        <div className="mt-3 p-2.5 bg-orange-50 border border-orange-200 text-orange-800 dark:bg-orange-950/40 dark:border-orange-800 dark:text-orange-200 rounded text-xs">
          Evaluation ran in degraded mode. Some speech or context signals were unavailable.
        </div>
      )}

      {/* 6 Dimensions Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3.5 my-4">
        {DIMENSIONS.map(({ key, label }) => {
          const score = getDimensionScore(key);
          const percent = score !== null ? Math.round(score * 100) : 0;
          return (
            <div
              key={key}
              data-testid={`dimension-${key}`}
              className="p-3 bg-zinc-50 dark:bg-zinc-800/40 rounded-md border border-zinc-200/60 dark:border-zinc-800"
            >
              <div className="flex justify-between items-center mb-1.5">
                <span className="text-xs font-medium text-zinc-700 dark:text-zinc-300">{label}</span>
                <span className="text-xs font-mono font-semibold text-zinc-900 dark:text-zinc-100">
                  {formatScore(score)}
                </span>
              </div>
              <div className="w-full bg-zinc-200 dark:bg-zinc-700 h-1.5 rounded-full overflow-hidden">
                <div
                  className={`h-full transition-all duration-300 ${
                    isUnavailable || score === null
                      ? 'w-0'
                      : percent >= 75
                      ? 'bg-emerald-500'
                      : percent >= 50
                      ? 'bg-amber-500'
                      : 'bg-rose-500'
                  }`}
                  style={{ width: isUnavailable ? '0%' : `${percent}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>

      {/* STAR Framework Completeness */}
      {star && (
        <div className="mt-3 pt-3 border-t border-zinc-100 dark:border-zinc-800">
          <div className="text-xs font-semibold text-zinc-700 dark:text-zinc-300 mb-2">
            STAR Method Coverage:
          </div>
          <div className="flex flex-wrap gap-2">
            {(['situation', 'task', 'action', 'result'] as const).map((step) => {
              const present = star[step];
              return (
                <span
                  key={step}
                  data-testid={`star-${step}`}
                  className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-medium border ${
                    present
                      ? 'bg-emerald-50 text-emerald-800 border-emerald-200 dark:bg-emerald-950/30 dark:text-emerald-300 dark:border-emerald-800'
                      : 'bg-zinc-100 text-zinc-500 border-zinc-200 dark:bg-zinc-800 dark:text-zinc-400 dark:border-zinc-700'
                  }`}
                >
                  <span aria-hidden="true">{present ? '✓' : '✗'} </span>
                  <span>{step.charAt(0).toUpperCase() + step.slice(1)}</span>
                </span>
              );
            })}
          </div>
        </div>
      )}

      {/* Rationale Excerpt */}
      {rationale && (
        <div className="mt-4 pt-3 border-t border-zinc-100 dark:border-zinc-800">
          <div className="text-xs font-semibold text-zinc-700 dark:text-zinc-300 mb-1">
            Evaluator Rationale:
          </div>
          <p className="text-xs text-zinc-600 dark:text-zinc-400 italic leading-relaxed">
            "{rationale}"
          </p>
        </div>
      )}
    </div>
  );
};
