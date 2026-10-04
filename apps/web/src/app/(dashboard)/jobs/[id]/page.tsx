"use client";

import React, { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { getJob } from '@/lib/api/jobs';
import type { JobDetailResponse } from '@/lib/api/types';
import { ApiError } from '@/lib/api/client';

function StatusBadge({ status }: { status: string }) {
  const classes: Record<string, string> = {
    ready: 'bg-green-900/30 text-green-300',
    pending: 'bg-yellow-900/30 text-yellow-300',
    processing: 'bg-blue-900/30 text-blue-300',
    failed: 'bg-red-900/30 text-red-300',
  };
  return (
    <span className={`px-2 py-1 rounded-full text-xs font-bold ${classes[status] ?? 'bg-gray-800 text-gray-300'}`}>
      {status.toUpperCase()}
    </span>
  );
}

export default function JobMatchPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;

  const [job, setJob] = useState<JobDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    getJob(id)
      .then(setJob)
      .catch(err => setError(err instanceof ApiError ? `${err.status}: ${err.message}` : String(err)))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <div className="p-8 text-gray-400">Loading job…</div>;
  if (error) return (
    <div className="p-8">
      <div className="bg-red-900/20 border border-red-800 text-red-300 p-4 rounded">
        Failed to load job: {error}
      </div>
    </div>
  );
  if (!job) return null;

  const blueprint = job.blueprints?.[0];
  const match = job.matches?.[0];

  return (
    <div className="p-8 max-w-5xl mx-auto space-y-8">

      {/* Header */}
      <div className="bg-gray-900 p-6 rounded border border-gray-800">
        <div className="flex justify-between items-start mb-3">
          <div>
            <h1 className="text-3xl font-bold">{job.role_title}</h1>
            <p className="text-gray-400 text-lg mt-1">{job.company}</p>
          </div>
          <StatusBadge status={job.processing_status} />
        </div>

        {blueprint?.likely_topics && blueprint.likely_topics.length > 0 && (
          <div className="flex flex-wrap gap-2 mt-4">
            {blueprint.likely_topics.map((t, i) => (
              <span key={i} className="bg-indigo-900/30 text-indigo-300 px-3 py-1 rounded-full text-sm font-semibold">
                {t}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Processing state */}
      {job.processing_status === 'processing' && (
        <div className="bg-blue-900/20 border border-blue-800 rounded p-4 text-blue-300">
          <p className="font-semibold">Analyzing job description…</p>
          <p className="text-sm text-blue-400 mt-1">Blueprint and match score will appear when ready.</p>
        </div>
      )}
      {job.processing_status === 'failed' && (
        <div className="bg-red-900/20 border border-red-800 rounded p-4 text-red-300">
          <p className="font-semibold">Processing failed</p>
          {job.error_message && <p className="text-sm mt-1">{job.error_message}</p>}
        </div>
      )}

      {/* Match score */}
      {match?.overall_score != null && (
        <div className="bg-gray-900 p-6 rounded border border-gray-800">
          <h2 className="text-xl font-bold mb-2">
            Candidate Match:{' '}
            <span className={match.overall_score >= 0.7 ? 'text-green-400' : match.overall_score >= 0.4 ? 'text-yellow-400' : 'text-red-400'}>
              {Math.round(match.overall_score * 100)}%
            </span>
          </h2>
          {match.methodology_version && (
            <p className="text-xs text-gray-600">Methodology: {match.methodology_version}</p>
          )}
          <p className="text-xs text-gray-500 mt-2 italic">
            PRAXIS readiness estimate — not a guarantee of hiring outcomes.
          </p>
        </div>
      )}

      {/* Blueprint summary */}
      {blueprint?.summary && (
        <div className="bg-gray-900 p-6 rounded border border-gray-800">
          <h2 className="text-lg font-bold mb-3">Job Blueprint</h2>
          <p className="text-gray-300 leading-relaxed whitespace-pre-wrap">{blueprint.summary}</p>
        </div>
      )}

      {/* Requirements */}
      {blueprint?.requirements && blueprint.requirements.length > 0 && (
        <div className="bg-gray-900 p-6 rounded border border-gray-800">
          <h2 className="text-lg font-bold mb-4">Requirements</h2>
          <div className="space-y-3">
            {blueprint.requirements.map(req => (
              <div key={req.id} className="flex items-start gap-3 text-sm">
                <span className={`mt-0.5 ${req.priority === 'required' ? 'text-red-400' : 'text-yellow-400'}`}>
                  {req.priority === 'required' ? '●' : '○'}
                </span>
                <div>
                  <span className="text-gray-200">{req.skill_text}</span>
                  {req.category && (
                    <span className="ml-2 text-xs text-gray-500 uppercase tracking-wider">{req.category}</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* No data yet */}
      {job.processing_status === 'ready' && !blueprint && !match && (
        <div className="bg-gray-900 border border-gray-800 rounded p-8 text-center text-gray-400">
          <p>Blueprint not yet generated. Trigger analysis from the PRAXIS CLI or wait for the background worker.</p>
        </div>
      )}
    </div>
  );
}
