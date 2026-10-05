"use client";

import React, { useEffect, useState } from 'react';
import { apiFetch, ApiError } from '@/lib/api/client';

interface HealthResponse {
  status: string;
  components?: Record<string, { status: string; reason?: string }>;
}

export default function AdminPage() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiFetch<HealthResponse>('/health/ready')
      .then(setHealth)
      .catch(err => setError(err instanceof ApiError ? `${err.status}: ${err.message}` : String(err)))
      .finally(() => setLoading(false));
  }, []);

  const statusDot = (s: string) =>
    s === 'ok' || s === 'healthy'
      ? <span className="inline-block w-2 h-2 rounded-full bg-green-400 mr-2" />
      : <span className="inline-block w-2 h-2 rounded-full bg-red-400 mr-2" />;

  return (
    <div className="p-8 max-w-4xl mx-auto space-y-8">
      <h1 className="text-3xl font-bold">Admin</h1>

      <section>
        <h2 className="text-lg font-bold mb-4 text-gray-400 uppercase tracking-widest text-sm">System Status</h2>
        {loading && <p className="text-gray-400">Checking status…</p>}
        {error && (
          <div className="bg-red-900/20 border border-red-800 text-red-300 p-4 rounded text-sm">
            Health check failed: {error}
          </div>
        )}
        {health && (
          <div className="bg-gray-900 border border-gray-800 rounded p-6 space-y-3">
            <div className="flex items-center">
              {statusDot(health.status)}
              <span className="text-gray-300">API</span>
              <span className="ml-auto font-mono text-sm text-gray-400">{health.status}</span>
            </div>
            {health.components && Object.entries(health.components).map(([name, comp]) => (
              <div key={name} className="flex items-center">
                {statusDot(comp.status)}
                <span className="text-gray-300 capitalize">{name}</span>
                <span className="ml-auto font-mono text-sm text-gray-400">{comp.status}</span>
                {comp.reason && <span className="text-xs text-red-400 ml-2">{comp.reason}</span>}
              </div>
            ))}
          </div>
        )}
      </section>

      <div className="bg-yellow-900/20 border-l-4 border-yellow-700 p-4 rounded text-sm text-yellow-300">
        Full admin functionality (user management, usage audit, provider health history) requires backend admin authorization.
        This page shows system health only.
      </div>
    </div>
  );
}
