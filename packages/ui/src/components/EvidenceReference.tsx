import React, { useState } from 'react';
import type { ClaimGrounding, ClaimClassification } from '@praxis/types';

export interface EvidenceReferenceProps {
  claim?: ClaimGrounding;
  claimText?: string;
  classification?: ClaimClassification;
  confidence?: number;
  sourceExcerpt?: string | null;
  sourceChunkId?: string | null;
  sourceProjectId?: string | null;
  className?: string;
}

const CLASSIFICATION_CONFIG: Record<
  ClaimClassification,
  { label: string; badgeClass: string; borderClass: string }
> = {
  SUPPORTED: {
    label: 'Verified Fact',
    badgeClass: 'bg-emerald-100 text-emerald-800 border-emerald-300 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-700',
    borderClass: 'border-l-emerald-500',
  },
  PARTIALLY_SUPPORTED: {
    label: 'Partially Supported',
    badgeClass: 'bg-amber-100 text-amber-800 border-amber-300 dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-700',
    borderClass: 'border-l-amber-500',
  },
  UNSUPPORTED: {
    label: 'Unverified',
    badgeClass: 'bg-slate-100 text-slate-800 border-slate-300 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700',
    borderClass: 'border-l-slate-400',
  },
  CONTRADICTED: {
    label: 'Contradicted',
    badgeClass: 'bg-rose-100 text-rose-800 border-rose-300 dark:bg-rose-950/40 dark:text-rose-300 dark:border-rose-700',
    borderClass: 'border-l-rose-500',
  },
  UNCERTAIN: {
    label: 'Needs Clarification',
    badgeClass: 'bg-indigo-100 text-indigo-800 border-indigo-300 dark:bg-indigo-950/40 dark:text-indigo-300 dark:border-indigo-700',
    borderClass: 'border-l-indigo-400',
  },
};

export const EvidenceReference: React.FC<EvidenceReferenceProps> = ({
  claim,
  claimText: propClaimText,
  classification: propClassification,
  confidence: propConfidence,
  sourceExcerpt: propExcerpt,
  sourceChunkId: propChunkId,
  sourceProjectId: propProjectId,
  className = '',
}) => {
  const [isExpanded, setIsExpanded] = useState(false);

  const claimText = claim?.claim_text || propClaimText || 'Unspecified statement';
  const classification = claim?.classification || propClassification || 'UNCERTAIN';
  const confidence = claim?.confidence ?? propConfidence ?? 0;
  const sourceExcerpt = claim?.source_excerpt || propExcerpt;
  const chunkId = claim?.source_chunk_id || propChunkId;
  const projectId = claim?.source_project_id || propProjectId;

  const config = CLASSIFICATION_CONFIG[classification] || CLASSIFICATION_CONFIG.UNCERTAIN;
  const confidencePercent = Math.round(confidence * 100);

  return (
    <div
      data-testid="evidence-reference"
      className={`border rounded-md p-3.5 my-2.5 bg-white dark:bg-zinc-900 border-zinc-200 dark:border-zinc-800 border-l-4 ${config.borderClass} ${className}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1">
          <p className="text-sm font-medium text-zinc-900 dark:text-zinc-100 leading-snug">
            "{claimText}"
          </p>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <span
            data-testid="classification-badge"
            className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold border ${config.badgeClass}`}
          >
            {config.label}
          </span>
          {confidence > 0 && (
            <span className="text-xs text-zinc-500 font-mono" title="AI Verification Confidence">
              {confidencePercent}%
            </span>
          )}
        </div>
      </div>

      {sourceExcerpt && (
        <div className="mt-2.5 pt-2 border-t border-zinc-100 dark:border-zinc-800/80">
          <button
            type="button"
            onClick={() => setIsExpanded(!isExpanded)}
            aria-expanded={isExpanded}
            className="text-xs font-medium text-blue-600 dark:text-blue-400 hover:underline flex items-center gap-1 focus:outline-none"
          >
            <span>{isExpanded ? 'Hide source excerpt' : 'View grounded source excerpt'}</span>
            <span aria-hidden="true">{isExpanded ? '▴' : '▾'}</span>
          </button>

          {isExpanded && (
            <div
              data-testid="evidence-excerpt"
              className="mt-2 p-2.5 bg-zinc-50 dark:bg-zinc-800/50 rounded text-xs text-zinc-700 dark:text-zinc-300 font-serif border border-zinc-200/60 dark:border-zinc-700/50"
            >
              <div className="text-[10px] uppercase tracking-wider text-zinc-400 font-sans font-semibold mb-1">
                Matched Document Passage:
              </div>
              <p className="italic">"{sourceExcerpt}"</p>
              {(chunkId || projectId) && (
                <div className="mt-1.5 pt-1 border-t border-zinc-200/40 text-[10px] text-zinc-400 font-mono">
                  {projectId && <span>Project: {projectId.slice(0, 8)} </span>}
                  {chunkId && <span>• Chunk: {chunkId.slice(0, 8)}</span>}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
