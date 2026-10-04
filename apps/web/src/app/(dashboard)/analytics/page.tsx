"use client";

import React, { useEffect, useState } from 'react';
import { getDashboardStats } from '@/lib/api/analytics';
import type { DashboardStats } from '@/lib/api/types';
import { ApiError } from '@/lib/api/client';

function StatCard({
  label,
  value,
  unit,
  note,
}: {
  label: string;
  value: number | null | undefined;
  unit?: string;
  note?: string;
}) {
  return (
    <div className="bg-gray-900 p-6 rounded shadow-lg shadow-black/50 border border-gray-800">
      <h3 className="text-gray-400 font-semibold mb-2">{label}</h3>
      {value != null ? (
        <div className="text-3xl font-mono font-bold text-gray-100">
          {value}{unit && <span className="text-lg text-gray-400 ml-1">{unit}</span>}
        </div>
      ) : (
        <>
          <div className="text-xl font-mono text-gray-600 italic">Unavailable</div>
          <div className="text-gray-500 text-sm mt-2">{note ?? 'Complete more sessions to view this metric.'}</div>
        </>
      )}
    </div>
  );
}

export default function AnalyticsPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getDashboardStats()
      .then(setStats)
      .catch(err => {
        setError(err instanceof ApiError ? `${err.status}: ${err.message}` : String(err));
      })
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-8">
      <div>
        <h1 className="text-3xl font-bold">Candidate Analytics</h1>
        <p className="text-gray-300 mt-2">Aggregate trends across your practice sessions.</p>
      </div>

      {loading && <p className="text-gray-400">Loading analytics…</p>}
      {error && (
        <div className="bg-red-900/20 border border-red-800 text-red-300 p-4 rounded">
          Failed to load analytics: {error}
        </div>
      )}

      {!loading && !error && stats && (
        <>
          <div className="grid grid-cols-2 gap-4 mb-2">
            <div className="bg-gray-900 p-4 rounded border border-gray-800 flex items-center justify-between">
              <span className="text-gray-400 text-sm">Sessions Completed</span>
              <span className="text-2xl font-mono font-bold">{stats.interviews_completed}</span>
            </div>
            <div className="bg-gray-900 p-4 rounded border border-gray-800 flex items-center justify-between">
              <span className="text-gray-400 text-sm">Total Sessions</span>
              <span className="text-2xl font-mono font-bold">{stats.total_sessions}</span>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-6">
            <StatCard
              label="Average Pace"
              value={stats.average_pace_wpm > 0 ? stats.average_pace_wpm : null}
              unit="WPM"
              note="Complete a session with coaching data."
            />
            <StatCard
              label="Filler Word Density"
              value={stats.filler_word_density > 0 ? stats.filler_word_density : null}
              unit="%"
              note="Filler detection requires at least one completed session."
            />
            <StatCard
              label="STAR Consistency"
              value={stats.star_consistency}
              unit="%"
              note="Complete behavioral interview sessions to measure STAR structure."
            />
          </div>

          <div className="grid grid-cols-1 gap-6">
            <StatCard
              label="Average Score"
              value={stats.average_score > 0 ? +(stats.average_score * 100).toFixed(0) : null}
              unit="/100"
              note="Scores appear after sessions are evaluated."
            />
          </div>
        </>
      )}

      {!loading && !error && stats?.total_sessions === 0 && (
        <div className="bg-gray-900 p-8 rounded border border-gray-800 text-center text-gray-500">
          <p className="italic">Complete practice sessions in the PRAXIS desktop app to view trend graphs.</p>
        </div>
      )}
    </div>
  );
}
