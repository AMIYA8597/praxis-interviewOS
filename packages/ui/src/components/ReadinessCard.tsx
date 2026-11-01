import React from 'react';
import type { ReadinessResponse, ReadinessStatus } from '@praxis/types';

export interface ReadinessCardProps {
  data?: ReadinessResponse | null;
  candidateId?: string;
  readinessScore?: number | null;
  status?: ReadinessStatus;
  sessionCount?: number;
  disclaimer?: string;
  recommendedActions?: string[];
  dimensions?: Record<string, { name: string; score: number | null; confidence: number; description?: string }>;
  onStartSession?: () => void;
  className?: string;
}

const DEFAULT_DISCLAIMER =
  'PRAXIS Readiness Estimate is a calibrated preparatory indicator, not an employment guarantee.';

export const ReadinessCard: React.FC<ReadinessCardProps> = ({
  data,
  candidateId: propCandidateId,
  readinessScore: propScore,
  status: propStatus,
  sessionCount: propCount,
  disclaimer: propDisclaimer,
  recommendedActions: propActions,
  dimensions: propDimensions,
  onStartSession,
  className = '',
}) => {
  const status: ReadinessStatus = data?.status || propStatus || 'INSUFFICIENT_EVIDENCE';
  const score = data?.readiness_score ?? propScore;
  const sessionCount = data?.session_count ?? propCount ?? 0;
  const disclaimer = data?.disclaimer || propDisclaimer || DEFAULT_DISCLAIMER;
  const actions = data?.recommended_actions || propActions || [];
  const dimensions = data?.dimensions || propDimensions || {};

  const isInsufficient = status === 'INSUFFICIENT_EVIDENCE' || sessionCount < 1 || score === null || score === undefined;

  return (
    <div
      data-testid="readiness-card"
      className={`bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl p-6 shadow-sm ${className}`}
    >
      {/* Title & Badge */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-zinc-100 dark:border-zinc-800 gap-2">
        <div>
          <h2 className="text-lg font-bold text-zinc-900 dark:text-zinc-100">
            PRAXIS Readiness Estimate
          </h2>
          <p className="text-xs text-zinc-500 mt-0.5">
            Calibrated multi-session predictive interview evaluation
          </p>
        </div>

        <span
          data-testid="readiness-status-badge"
          className={`self-start sm:self-auto px-3 py-1 text-xs font-semibold rounded-full border ${
            status === 'MEASURED'
              ? 'bg-emerald-50 text-emerald-800 border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-800'
              : status === 'ESTIMATED'
              ? 'bg-amber-50 text-amber-800 border-amber-200 dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-800'
              : 'bg-zinc-100 text-zinc-600 border-zinc-300 dark:bg-zinc-800 dark:text-zinc-400 dark:border-zinc-700'
          }`}
        >
          {status.replace('_', ' ')}
        </span>
      </div>

      {/* Main Body */}
      {isInsufficient ? (
        <div data-testid="insufficient-evidence" className="py-8 text-center">
          <div className="w-12 h-12 mx-auto rounded-full bg-zinc-100 dark:bg-zinc-800 flex items-center justify-center text-zinc-400 mb-3 text-lg font-semibold">
            !
          </div>
          <h3 className="text-sm font-semibold text-zinc-800 dark:text-zinc-200">
            Insufficient Evidence
          </h3>
          <p className="text-xs text-zinc-500 max-w-sm mx-auto mt-1 mb-4">
            Complete your first mock interview practice session to compute a calibrated readiness estimate backed by real speech and rubric evidence.
          </p>
          {onStartSession && (
            <button
              type="button"
              onClick={onStartSession}
              className="inline-flex items-center px-4 py-2 text-xs font-semibold rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              Start First Practice Session
            </button>
          )}
        </div>
      ) : (
        <div className="py-4">
          <div className="flex flex-col md:flex-row items-center gap-6 my-2">
            {/* Overall Score Circle */}
            <div className="flex flex-col items-center justify-center p-4 rounded-xl bg-zinc-50 dark:bg-zinc-800/40 border border-zinc-200/60 dark:border-zinc-800 min-w-[140px]">
              <span className="text-xs font-semibold text-zinc-500 uppercase tracking-wide">
                Calibrated Score
              </span>
              <span
                data-testid="readiness-score-value"
                className="text-4xl font-extrabold text-blue-600 dark:text-blue-400 font-mono my-1"
              >
                {Math.round((score ?? 0) * 100)}%
              </span>
              <span className="text-[11px] text-zinc-400">
                Based on {sessionCount} {sessionCount === 1 ? 'session' : 'sessions'}
              </span>
            </div>

            {/* Dimension Breakdown */}
            <div className="flex-1 w-full space-y-2.5">
              {Object.entries(dimensions).length > 0 ? (
                Object.entries(dimensions).map(([key, dim]) => {
                  const dimPercent = dim.score !== null ? Math.round(dim.score * 100) : 0;
                  return (
                    <div key={key} data-testid={`readiness-dimension-${key}`}>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="font-medium text-zinc-700 dark:text-zinc-300">
                          {dim.name || key}
                        </span>
                        <span className="font-mono font-semibold text-zinc-900 dark:text-zinc-100">
                          {dim.score !== null ? `${dimPercent}%` : 'N/A'}
                        </span>
                      </div>
                      <div className="w-full bg-zinc-100 dark:bg-zinc-800 h-2 rounded-full overflow-hidden">
                        <div
                          className="bg-blue-600 h-full rounded-full transition-all duration-300"
                          style={{ width: `${dimPercent}%` }}
                        />
                      </div>
                    </div>
                  );
                })
              ) : (
                <div className="text-xs text-zinc-400 italic">
                  Dimension breakdown will populate as more answers are scored.
                </div>
              )}
            </div>
          </div>

          {/* Recommended Actions */}
          {actions.length > 0 && (
            <div className="mt-4 pt-4 border-t border-zinc-100 dark:border-zinc-800">
              <h4 className="text-xs font-semibold text-zinc-800 dark:text-zinc-200 uppercase tracking-wider mb-2">
                Recommended Focus Areas
              </h4>
              <ul className="space-y-1.5">
                {actions.map((act, idx) => (
                  <li
                    key={idx}
                    className="text-xs text-zinc-600 dark:text-zinc-400 flex items-start gap-2"
                  >
                    <span className="text-blue-500 font-bold">•</span>
                    <span>{act}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Mandatory Regulatory / Ethical Disclaimer */}
      <div
        data-testid="readiness-disclaimer"
        className="mt-4 pt-3 border-t border-zinc-100 dark:border-zinc-800 text-[11px] text-zinc-500 dark:text-zinc-400 italic leading-snug"
      >
        {disclaimer}
      </div>
    </div>
  );
};
