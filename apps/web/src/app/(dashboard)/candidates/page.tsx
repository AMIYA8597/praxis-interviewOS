"use client";

import React, { useEffect, useState } from 'react';
import { getMe, updateMe } from '@/lib/api/candidates';
import type { CandidateResponse } from '@/lib/api/types';
import { ApiError } from '@/lib/api/client';

export default function CandidatesPage() {
  const [candidate, setCandidate] = useState<CandidateResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({ full_name: '', headline: '', location: '', years_experience: '' });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    getMe()
      .then(c => {
        setCandidate(c);
        setForm({
          full_name: c.full_name ?? '',
          headline: c.headline ?? '',
          location: c.location ?? '',
          years_experience: c.years_experience != null ? String(c.years_experience) : '',
        });
      })
      .catch(err => setError(err instanceof ApiError ? `${err.status}: ${err.message}` : String(err)))
      .finally(() => setLoading(false));
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const updated = await updateMe({
        full_name: form.full_name,
        headline: form.headline || undefined,
        location: form.location || undefined,
        years_experience: form.years_experience ? Number(form.years_experience) : undefined,
      });
      setCandidate(updated);
      setEditing(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : String(err));
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div className="p-8 text-gray-400">Loading profile…</div>;
  if (error && !candidate) return (
    <div className="p-8">
      <div className="bg-red-900/20 border border-red-800 text-red-300 p-4 rounded">
        Failed to load profile: {error}
      </div>
    </div>
  );

  return (
    <div className="p-8 max-w-4xl mx-auto space-y-8">
      <div className="flex justify-between items-start">
        <h1 className="text-3xl font-bold">Candidate Profile</h1>
        {!editing && (
          <button
            onClick={() => setEditing(true)}
            className="px-4 py-2 bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded text-sm font-semibold transition"
          >
            Edit
          </button>
        )}
      </div>

      {error && (
        <div className="bg-red-900/20 border border-red-800 text-red-300 p-3 rounded text-sm">{error}</div>
      )}

      {candidate && !editing && (
        <div className="bg-gray-900 border border-gray-800 rounded p-6 space-y-4">
          <div>
            <div className="text-xs uppercase tracking-widest text-gray-500 mb-1">Name</div>
            <div className="text-xl font-bold">{candidate.full_name}</div>
          </div>
          {candidate.headline && (
            <div>
              <div className="text-xs uppercase tracking-widest text-gray-500 mb-1">Headline</div>
              <div className="text-gray-300">{candidate.headline}</div>
            </div>
          )}
          {candidate.location && (
            <div>
              <div className="text-xs uppercase tracking-widest text-gray-500 mb-1">Location</div>
              <div className="text-gray-300">{candidate.location}</div>
            </div>
          )}
          {candidate.years_experience != null && (
            <div>
              <div className="text-xs uppercase tracking-widest text-gray-500 mb-1">Experience</div>
              <div className="text-gray-300">{candidate.years_experience} years</div>
            </div>
          )}
          {candidate.target_roles.length > 0 && (
            <div>
              <div className="text-xs uppercase tracking-widest text-gray-500 mb-2">Target Roles</div>
              <div className="flex flex-wrap gap-2">
                {candidate.target_roles.map((r, i) => (
                  <span key={i} className="bg-indigo-900/30 text-indigo-300 px-3 py-1 rounded-full text-sm">{r}</span>
                ))}
              </div>
            </div>
          )}
          <div className="text-xs text-gray-600 pt-2">
            Member since {new Date(candidate.created_at).toLocaleDateString()}
          </div>
        </div>
      )}

      {editing && (
        <form onSubmit={handleSave} className="bg-gray-900 border border-gray-800 rounded p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">Full Name</label>
            <input
              type="text"
              value={form.full_name}
              onChange={e => setForm(f => ({ ...f, full_name: e.target.value }))}
              className="w-full p-2 bg-gray-800 border border-gray-700 rounded text-white"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">Headline</label>
            <input
              type="text"
              value={form.headline}
              onChange={e => setForm(f => ({ ...f, headline: e.target.value }))}
              className="w-full p-2 bg-gray-800 border border-gray-700 rounded text-white"
              placeholder="e.g. Senior Software Engineer"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">Location</label>
            <input
              type="text"
              value={form.location}
              onChange={e => setForm(f => ({ ...f, location: e.target.value }))}
              className="w-full p-2 bg-gray-800 border border-gray-700 rounded text-white"
              placeholder="e.g. San Francisco, CA"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">Years of Experience</label>
            <input
              type="number"
              min="0"
              max="80"
              step="0.5"
              value={form.years_experience}
              onChange={e => setForm(f => ({ ...f, years_experience: e.target.value }))}
              className="w-full p-2 bg-gray-800 border border-gray-700 rounded text-white"
            />
          </div>
          <div className="flex gap-3 pt-2">
            <button
              type="submit"
              disabled={saving}
              className="px-6 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold rounded transition disabled:opacity-50"
            >
              {saving ? 'Saving…' : 'Save'}
            </button>
            <button
              type="button"
              onClick={() => setEditing(false)}
              className="px-6 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 font-semibold rounded transition border border-gray-700"
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      <div className="bg-yellow-900/20 border-l-4 border-yellow-700 p-4 rounded">
        <p className="text-yellow-300 text-sm">
          <strong>Resume extraction and fact verification</strong> are processed automatically after you upload a resume.
          Skill verification and STAR story management are in development.
        </p>
      </div>
    </div>
  );
}
