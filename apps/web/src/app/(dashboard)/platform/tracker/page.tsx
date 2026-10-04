"use client";

import React, { useEffect, useState } from 'react';
import { listApplications, createApplication, updateApplication } from '@/lib/api/applications';
import type { ApplicationResponse } from '@/lib/api/applications';
import { ApiError } from '@/lib/api/client';

const STATUS_OPTIONS = ['applied', 'screening', 'interview', 'onsite', 'offer', 'rejected', 'withdrawn'];

const STATUS_CLASSES: Record<string, string> = {
  applied: 'bg-gray-800 text-gray-300',
  screening: 'bg-blue-900/30 text-blue-300',
  interview: 'bg-indigo-900/30 text-indigo-300',
  onsite: 'bg-purple-900/30 text-purple-300',
  offer: 'bg-green-900/30 text-green-300',
  rejected: 'bg-red-900/30 text-red-300',
  withdrawn: 'bg-gray-900 text-gray-500',
};

export default function ApplicationTrackerPage() {
  const [apps, setApps] = useState<ApplicationResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ company: '', role: '', status: 'applied', next_action: '' });
  const [submitting, setSubmitting] = useState(false);

  const load = () =>
    listApplications(undefined, 50)
      .then(p => setApps(p.items))
      .catch(err => setError(err instanceof ApiError ? err.message : String(err)))
      .finally(() => setLoading(false));

  useEffect(() => { load(); }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await createApplication(form);
      setForm({ company: '', role: '', status: 'applied', next_action: '' });
      setShowForm(false);
      setLoading(true);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  };

  const handleStatusChange = async (id: string, status: string) => {
    try {
      const updated = await updateApplication(id, { status });
      setApps(prev => prev.map(a => a.id === id ? { ...a, ...updated } : a));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : String(err));
    }
  };

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">Application Tracker</h1>
        <button
          onClick={() => setShowForm(s => !s)}
          className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded font-bold transition"
        >
          {showForm ? 'Cancel' : '+ New Application'}
        </button>
      </div>

      {error && (
        <div className="bg-red-900/20 border border-red-800 text-red-300 p-4 rounded text-sm">{error}</div>
      )}

      {showForm && (
        <form onSubmit={handleCreate} className="bg-gray-900 border border-gray-800 rounded p-6 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-gray-400 mb-1">Company</label>
              <input
                type="text"
                value={form.company}
                onChange={e => setForm(f => ({ ...f, company: e.target.value }))}
                className="w-full p-2 bg-gray-800 border border-gray-700 rounded text-white"
                required
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Role</label>
              <input
                type="text"
                value={form.role}
                onChange={e => setForm(f => ({ ...f, role: e.target.value }))}
                className="w-full p-2 bg-gray-800 border border-gray-700 rounded text-white"
                required
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Status</label>
              <select
                value={form.status}
                onChange={e => setForm(f => ({ ...f, status: e.target.value }))}
                className="w-full p-2 bg-gray-800 border border-gray-700 rounded text-white"
              >
                {STATUS_OPTIONS.map(s => (
                  <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Next Action</label>
              <input
                type="text"
                value={form.next_action}
                onChange={e => setForm(f => ({ ...f, next_action: e.target.value }))}
                className="w-full p-2 bg-gray-800 border border-gray-700 rounded text-white"
                placeholder="e.g. Follow up on Thursday"
              />
            </div>
          </div>
          <button
            type="submit"
            disabled={submitting}
            className="px-6 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold rounded transition disabled:opacity-50"
          >
            {submitting ? 'Adding…' : 'Add Application'}
          </button>
        </form>
      )}

      {loading && <p className="text-gray-400">Loading…</p>}

      {!loading && apps.length === 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded p-10 text-center text-gray-400">
          <p>No applications yet. Add your first one above.</p>
        </div>
      )}

      {apps.length > 0 && (
        <div className="bg-gray-900 rounded border border-gray-800 overflow-hidden">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-gray-800 border-b border-gray-700">
                <th className="p-4 text-xs uppercase tracking-widest text-gray-400 font-semibold">Company &amp; Role</th>
                <th className="p-4 text-xs uppercase tracking-widest text-gray-400 font-semibold">Status</th>
                <th className="p-4 text-xs uppercase tracking-widest text-gray-400 font-semibold">Applied</th>
                <th className="p-4 text-xs uppercase tracking-widest text-gray-400 font-semibold">Next Action</th>
              </tr>
            </thead>
            <tbody>
              {apps.map(app => (
                <tr key={app.id} className="border-b border-gray-800 hover:bg-gray-800/50">
                  <td className="p-4">
                    <div className="font-bold">{app.company ?? '—'}</div>
                    <div className="text-sm text-gray-400">{app.role ?? '—'}</div>
                  </td>
                  <td className="p-4">
                    <select
                      value={app.status ?? 'applied'}
                      onChange={e => handleStatusChange(app.id, e.target.value)}
                      className={`px-2 py-1 rounded text-xs font-bold border-0 cursor-pointer ${STATUS_CLASSES[app.status ?? 'applied'] ?? 'bg-gray-800 text-gray-300'}`}
                    >
                      {STATUS_OPTIONS.map(s => (
                        <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
                      ))}
                    </select>
                  </td>
                  <td className="p-4 text-sm text-gray-400 font-mono">
                    {app.applied_at ? new Date(app.applied_at).toLocaleDateString() : '—'}
                  </td>
                  <td className="p-4 text-sm text-gray-300">{app.next_action ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="bg-gray-900 border border-gray-800 rounded p-6">
        <h2 className="text-lg font-bold text-indigo-200 mb-3">Cold Outreach Generator</h2>
        <p className="text-gray-400 text-sm mb-4">
          Generate a personalized outreach draft for a hiring manager. PRAXIS will never auto-send emails or fabricate recipient facts.
        </p>
        <div className="flex space-x-3">
          <input
            type="text"
            placeholder="Company name"
            className="border border-gray-700 bg-gray-800 p-2 rounded flex-1 text-white text-sm"
          />
          <input
            type="text"
            placeholder="Specific detail (e.g. recent product launch)"
            className="border border-gray-700 bg-gray-800 p-2 rounded flex-1 text-white text-sm"
          />
          <button className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded font-bold text-sm transition">
            Generate Draft
          </button>
        </div>
        <p className="text-xs text-yellow-600 mt-3">
          ⚠ Review and edit all AI-generated outreach before sending. PRAXIS never sends messages on your behalf.
        </p>
      </div>
    </div>
  );
}
