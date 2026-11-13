"use client";

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { listSessions, createSession } from '@/lib/api/sessions';
import type { SessionResponse } from '@/lib/api/types';
import { ApiError } from '@/lib/api/client';
import { Modal } from '@praxis/ui';

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
  const router = useRouter();
  const [sessions, setSessions] = useState<SessionResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // New session modal state
  const [showModal, setShowModal] = useState(false);
  const [interviewType, setInterviewType] = useState('system_design');
  const [difficulty, setDifficulty] = useState('standard');
  const [creating, setCreating] = useState(false);

  const fetchSessions = () => {
    setLoading(true);
    listSessions(undefined, 50)
      .then((page) => setSessions(page.items))
      .catch((err) => {
        setError(err instanceof ApiError ? `${err.status}: ${err.message}` : String(err));
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchSessions();
  }, []);

  const handleCreateSession = async () => {
    setCreating(true);
    try {
      const created = await createSession({
        interview_type: interviewType,
        difficulty,
        mode: 'mock_interview',
      });
      setShowModal(false);
      router.push(`/sessions/${created.id}`);
    } catch (err: any) {
      setError(`Failed to create practice session: ${err.message || String(err)}`);
      setCreating(false);
    }
  };

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Practice Sessions</h1>
          <p className="text-sm text-gray-400 mt-1">
            Real-time interactive mock interviews with speech intelligence & rubric evaluation.
          </p>
        </div>

        <button
          type="button"
          onClick={() => setShowModal(true)}
          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-md text-sm font-semibold shadow-sm transition-colors"
        >
          + Start Practice Session
        </button>
      </div>

      {loading && <p className="text-gray-400">Loading…</p>}
      {error && (
        <div className="bg-red-900/20 border border-red-800 text-red-300 p-4 rounded">
          Failed to load sessions: {error}
        </div>
      )}

      {!loading && !error && sessions.length === 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded p-12 text-center text-gray-400 space-y-4">
          <p className="text-lg">No sessions yet.</p>
          <p className="text-sm max-w-md mx-auto">
            Ready to practice? Launch a new live session directly in your browser or through the PRAXIS desktop client.
          </p>
          <button
            type="button"
            onClick={() => setShowModal(true)}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-md text-sm font-semibold shadow-sm"
          >
            Start Your First Practice Session
          </button>
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
                <th className="p-4 text-xs uppercase tracking-widest text-gray-400 font-semibold">Action</th>
              </tr>
            </thead>
            <tbody>
              {sessions.map((s) => (
                <tr key={s.id} className="border-b border-gray-800 hover:bg-gray-800/50">
                  <td className="p-4 font-mono text-sm text-gray-300">
                    {s.created_at ? new Date(s.created_at).toLocaleDateString() : '—'}
                  </td>
                  <td className="p-4 text-sm text-gray-300 capitalize">{s.mode ?? '—'}</td>
                  <td className="p-4 text-sm text-gray-300 capitalize">{s.interview_type?.replace('_', ' ') ?? '—'}</td>
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
                        Debrief →
                      </Link>
                    ) : s.status === 'active' || s.status === 'pending' ? (
                      <Link
                        href={`/sessions/${s.id}`}
                        className="text-emerald-400 hover:text-emerald-300 text-sm font-semibold flex items-center gap-1"
                      >
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                        Enter Room →
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

      {/* Start Session Modal */}
      {showModal && (
        <Modal
          isOpen={showModal}
          onClose={() => setShowModal(false)}
          title="Start Live Practice Session"
        >
          <div className="space-y-4 pt-2">
            <div>
              <label className="block text-xs font-semibold text-gray-300 mb-1">
                Interview Domain & Focus:
              </label>
              <select
                value={interviewType}
                onChange={(e) => setInterviewType(e.target.value)}
                className="w-full bg-gray-800 border border-gray-700 text-gray-100 rounded px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-indigo-500"
              >
                <option value="system_design">System Architecture & Design</option>
                <option value="technical">Coding & Algorithms</option>
                <option value="behavioral">Behavioral (STAR Method)</option>
                <option value="mixed">Full-Stack Engineering</option>
                <option value="screening">Screening Interview</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-300 mb-1">
                Target Difficulty:
              </label>
              <select
                value={difficulty}
                onChange={(e) => setDifficulty(e.target.value)}
                className="w-full bg-gray-800 border border-gray-700 text-gray-100 rounded px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-indigo-500"
              >
                <option value="warmup">Foundational (Junior / Associate)</option>
                <option value="standard">Standard (Mid-Level Engineer)</option>
                <option value="senior">Advanced (Senior / Staff Engineer)</option>
              </select>
            </div>

            <div className="pt-4 border-t border-gray-800 flex justify-end gap-3">
              <button
                type="button"
                onClick={() => setShowModal(false)}
                className="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded text-xs font-medium"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleCreateSession}
                disabled={creating}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded text-xs font-semibold disabled:opacity-50"
              >
                {creating ? 'Starting...' : 'Enter Arena'}
              </button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}
