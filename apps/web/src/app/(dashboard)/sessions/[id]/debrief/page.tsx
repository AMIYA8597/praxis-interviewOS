"use client";

import React, { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { getSessionDebrief, getSession, getSessionTurns } from '@/lib/api/sessions';
import type { SessionDebriefResponse, SessionResponse, SessionTurnResponse } from '@/lib/api/types';
import { ApiError } from '@/lib/api/client';

function MetricCell({ label, value, unit }: { label: string; value: number | null | undefined; unit?: string }) {
  return (
    <div className="bg-gray-900 p-4 rounded border border-gray-800 text-center">
      <div className="text-xs uppercase tracking-widest text-gray-500 mb-1">{label}</div>
      {value != null ? (
        <div className="text-2xl font-mono font-bold text-gray-100">
          {typeof value === 'number' ? value.toFixed(value % 1 === 0 ? 0 : 1) : value}
          {unit && <span className="text-sm text-gray-400 ml-1">{unit}</span>}
        </div>
      ) : (
        <div className="text-lg font-mono text-gray-600 italic">Unavailable</div>
      )}
    </div>
  );
}

export default function DebriefPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;

  const [session, setSession] = useState<SessionResponse | null>(null);
  const [debrief, setDebrief] = useState<SessionDebriefResponse | null>(null);
  const [turns, setTurns] = useState<SessionTurnResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    Promise.all([getSession(id), getSessionDebrief(id), getSessionTurns(id)])
      .then(([s, d, t]) => {
        setSession(s);
        setDebrief(d);
        setTurns(t);
      })
      .catch(err => {
        setError(err instanceof ApiError ? `${err.status}: ${err.message}` : String(err));
      })
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <div className="p-8 text-gray-400">Loading debrief…</div>;
  if (error) return (
    <div className="p-8">
      <div className="bg-red-900/20 border border-red-800 text-red-300 p-4 rounded">
        Failed to load debrief: {error}
      </div>
    </div>
  );

  const hm = debrief?.headline_metrics;
  const interviewer = turns.filter(t => t.speaker === 'interviewer');
  const candidate = turns.filter(t => t.speaker === 'candidate');

  return (
    <div className="p-8 max-w-4xl mx-auto space-y-8">

      <div className="flex justify-between items-end border-b border-gray-800 pb-6">
        <div>
          <h1 className="text-3xl font-bold">Session Debrief</h1>
          {session?.interview_type && (
            <p className="text-gray-400 mt-1 capitalize">{session.interview_type.replace('_', ' ')} interview</p>
          )}
          {session?.created_at && (
            <p className="text-gray-500 text-sm mt-1">{new Date(session.created_at).toLocaleString()}</p>
          )}
        </div>
        {session?.status && (
          <span className="text-sm font-bold uppercase tracking-widest text-gray-400">{session.status}</span>
        )}
      </div>

      {/* Headline metrics */}
      <div className="grid grid-cols-3 gap-4">
        <MetricCell label="Avg Pace" value={hm?.average_wpm ?? null} unit="WPM" />
        <MetricCell
          label="Filler Rate"
          value={hm?.average_filler_rate != null ? +(hm.average_filler_rate * 100).toFixed(1) : null}
          unit="%"
        />
        <MetricCell
          label="Avg Score"
          value={hm?.average_score != null ? +(hm.average_score * 100).toFixed(0) : null}
          unit="/100"
        />
      </div>

      {/* Debrief pending */}
      {debrief?.status === 'pending' && (
        <div className="bg-yellow-900/20 border border-yellow-800 rounded p-6 text-yellow-300">
          <p className="font-semibold">Debrief is being generated…</p>
          <p className="text-sm mt-1 text-yellow-500">Refresh in a few seconds.</p>
        </div>
      )}

      {/* Strengths & Weaknesses */}
      {debrief?.status === 'ready' && (
        <>
          {debrief.strengths.length > 0 && (
            <div className="bg-gray-900 p-6 rounded border border-gray-800">
              <h2 className="text-lg font-bold text-green-400 mb-3">Strengths</h2>
              <ul className="space-y-2">
                {debrief.strengths.map((s, i) => (
                  <li key={i} className="flex items-start gap-2 text-gray-300">
                    <span className="text-green-500 mt-0.5">✓</span>
                    {s}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {debrief.weaknesses.length > 0 && (
            <div className="bg-gray-900 p-6 rounded border border-gray-800">
              <h2 className="text-lg font-bold text-red-400 mb-3">Areas to Improve</h2>
              <ul className="space-y-2">
                {debrief.weaknesses.map((w, i) => (
                  <li key={i} className="flex items-start gap-2 text-gray-300">
                    <span className="text-red-500 mt-0.5">✗</span>
                    {w}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}

      {/* Turn transcript */}
      {turns.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-xl font-bold">Turn Transcript</h2>
          {turns.map(t => (
            <div
              key={t.id}
              className={`border rounded p-4 ${
                t.speaker === 'interviewer'
                  ? 'border-indigo-800 bg-indigo-900/10'
                  : 'border-gray-700 bg-gray-900'
              }`}
            >
              <div className="flex justify-between items-center mb-2">
                <span className="text-xs uppercase tracking-widest font-bold text-gray-500">
                  {t.speaker ?? 'unknown'}
                </span>
                {t.duration_ms != null && (
                  <span className="text-xs text-gray-600 font-mono">{(t.duration_ms / 1000).toFixed(1)}s</span>
                )}
              </div>
              <p className="text-gray-300">{t.text ?? <span className="italic text-gray-600">—</span>}</p>
            </div>
          ))}
        </div>
      )}

      {/* Summary stats */}
      {turns.length > 0 && (
        <div className="grid grid-cols-2 gap-4 pt-4 border-t border-gray-800">
          <div className="text-center">
            <div className="text-2xl font-mono font-bold">{interviewer.length}</div>
            <div className="text-xs uppercase text-gray-500 mt-1">Interviewer turns</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-mono font-bold">{candidate.length}</div>
            <div className="text-xs uppercase text-gray-500 mt-1">Your turns</div>
          </div>
        </div>
      )}
    </div>
  );
}
