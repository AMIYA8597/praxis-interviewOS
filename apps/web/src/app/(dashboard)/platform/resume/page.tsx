"use client";

import React, { useEffect, useState } from 'react';
import { apiFetch, ApiError } from '@/lib/api/client';

interface ResumeResponse {
  id: string;
  original_filename: string;
  processing_status: string;
  error_message: string | null;
  created_at: string;
}

export default function ResumeBuilderPage() {
  const [resumes, setResumes] = useState<ResumeResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [file, setFile] = useState<File | null>(null);

  const load = () =>
    apiFetch<{ items: ResumeResponse[] }>('/resumes')
      .then(p => setResumes(p.items))
      .catch(err => setError(err instanceof ApiError ? `${err.status}: ${err.message}` : String(err)))
      .finally(() => setLoading(false));

  useEffect(() => { load(); }, []);

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;
    setUploading(true);
    try {
      const form = new FormData();
      form.append('file', file);
      await apiFetch('/resumes/upload', { method: 'POST', body: form });
      setFile(null);
      setLoading(true);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : String(err));
    } finally {
      setUploading(false);
    }
  };

  const statusColor = (s: string) => {
    if (s === 'ready') return 'text-green-400';
    if (s === 'failed') return 'text-red-400';
    return 'text-yellow-400';
  };

  return (
    <div className="p-8 max-w-4xl mx-auto space-y-8">
      <h1 className="text-3xl font-bold">Resume</h1>

      {error && (
        <div className="bg-red-900/20 border border-red-800 text-red-300 p-4 rounded text-sm">{error}</div>
      )}

      {/* Upload */}
      <form onSubmit={handleUpload} className="bg-gray-900 border border-gray-800 rounded p-6 space-y-4">
        <h2 className="text-lg font-bold">Upload Resume</h2>
        <p className="text-gray-400 text-sm">
          Upload a PDF, DOCX, or TXT file. PRAXIS will extract your experience, skills, and claims for grounding during practice.
        </p>
        <div className="flex gap-4 items-end">
          <input
            type="file"
            accept=".pdf,.docx,.txt"
            onChange={e => setFile(e.target.files?.[0] || null)}
            className="flex-1 p-2 bg-gray-800 border border-gray-700 rounded text-gray-300 text-sm"
          />
          <button
            type="submit"
            disabled={!file || uploading}
            className="px-6 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold rounded transition disabled:opacity-50"
          >
            {uploading ? 'Uploading…' : 'Upload'}
          </button>
        </div>
      </form>

      {/* Resume list */}
      {loading && <p className="text-gray-400">Loading…</p>}

      {!loading && resumes.length === 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded p-10 text-center text-gray-400">
          <p>No resumes uploaded yet.</p>
        </div>
      )}

      {resumes.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-lg font-bold">Uploaded Resumes</h2>
          {resumes.map(r => (
            <div key={r.id} className="bg-gray-900 border border-gray-800 rounded p-4 flex justify-between items-center">
              <div>
                <div className="font-semibold text-gray-200">{r.original_filename}</div>
                <div className="text-xs text-gray-500 mt-1">{new Date(r.created_at).toLocaleString()}</div>
              </div>
              <div className={`text-sm font-mono font-bold uppercase ${statusColor(r.processing_status)}`}>
                {r.processing_status}
                {r.error_message && (
                  <div className="text-xs text-red-400 font-normal normal-case mt-1 max-w-xs">{r.error_message}</div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="bg-yellow-900/20 border-l-4 border-yellow-700 p-4 rounded text-sm text-yellow-300">
        <strong>Note:</strong> The tailored resume builder (AI-powered bullet rewriting for specific JDs) is planned for a future release.
        Currently PRAXIS uses your resume for claim grounding during practice sessions.
      </div>
    </div>
  );
}
