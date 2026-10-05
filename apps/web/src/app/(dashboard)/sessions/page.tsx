"use client";

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { listSessions } from '@/lib/api/sessions';
import type { SessionResponse } from '@/lib/api/types';
import { ApiError } from '@/lib/api/client';

function statusBadge(status: string) {
  const classes: Record<string, string> = {
    completed: 'bg-green-900/30 text-green-300',
    active: 'bg-blue-900/30 text-blue-300',
    pending: 'bg-yellow-900/30 text-yellow-300',
    failed: 'bg-red-900/30 text-red-300',
  };
  const cls = classes[status] ?? 'bg-gray-800 text-gray-300';
  return (
    <span className={`px-2 py-1 rounded-full text-xs font-bold ${cls}`}>
      {status.toUpperCase()}
    </span>
  );
}

export default function SessionsPage() {
  const [sessions, setSessions] = useState<SessionResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listSessions(undefined, 50)
      .then(page => setSessions(page.items))
      .catch(err => {
        setError(err instanceof ApiError ? `${err.status}: ${err.message}` : String(err));
      })
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-6">
      <h1 className="text-3xl font-bold">Practice Sessions</h1>

      {loading && <p className="text-gray-400">Loading…</p>}
      {error && (
        <div className="bg-red-900/20 border border-red-800 text-red-300 p-4 rounded">
          Failed to load sessions: {error}
        </div>
      )}

      {!loading && !error && sessions.length === 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded p-12 text-center text-gray-400">
          <p className="text-lg mb-2">No sessions yet.</p>
          <p className="text-sm">Open the PRAXIS desktop app to start your first practice interview.</p>
        </div>
      )}

      {sessions.length > 0 && (
        <div className="bg-gray-900 rounded border border-gray-800 overflow-hidden">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-gray-800 border-b border-gray-700">
                <th className="p-4 text-xs uppercase tracking-widest text-gray-400 font-semibold">Date</th>
                <th className="p-4 text-xs uppercase tracking-widest text-gray-400 font-semibold">Mode</th>
                <th className="p-4 text-xs uppercase tracking-widest text-gray-400 font-semibold">Type</th>
                <th className="p-4 text-xs uppercase tracking-widest text-gray-400 font-semibold">Duration</th>
                <th className="p-4 text-xs uppercase tracking-widest text-gray-400 font-semibold">Status</th>
                <th className="p-4 text-xs uppercase tracking-widest text-gray-400 font-semibold">Debrief</th>
              </tr>
            </thead>
            <tbody>
              {sessions.map(s => (
                <tr key={s.id} className="border-b border-gray-800 hover:bg-gray-800/50">
                  <td className="p-4 font-mono text-sm text-gray-300">
                    {s.created_at ? new Date(s.created_at).toLocaleDateString() : '—'}
                  </td>
                  <td className="p-4 text-sm text-gray-300 capitalize">{s.mode ?? '—'}</td>
                  <td className="p-4 text-sm text-gray-300 capitalize">{s.interview_type ?? '—'}</td>
                  <td className="p-4 text-sm font-mono text-gray-300">
                    {s.duration_s != null ? `${Math.round(s.duration_s / 60)}m` : '—'}
                  </td>
                  <td className="p-4">{statusBadge(s.status)}</td>
                  <td className="p-4">
                    {s.status === 'completed' ? (
                      <Link
                        href={`/sessions/${s.id}/debrief`}
                        className="text-indigo-400 hover:text-indigo-300 text-sm font-semibold"
                      >
                        View →
                      </Link>
                    ) : (
                      <span className="text-gray-600 text-sm">—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
