"use client";

import React, { useEffect, useState } from 'react';
import { apiFetch, ApiError } from '@/lib/api/client';

interface ProviderStatus {
  capabilities: {
    streaming: boolean;
    structured_output: boolean;
    vision: boolean;
    embeddings: boolean;
    is_local: boolean;
    is_free_tier: boolean;
  };
  circuit_breaker_state: string;
}

interface ProvidersResponse {
  status: string;
  providers: Record<string, ProviderStatus>;
}

export default function ProvidersSettingsPage() {
  const [providers, setProviders] = useState<ProvidersResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiFetch<ProvidersResponse>('/health/providers')
      .then(setProviders)
      .catch(err => setError(err instanceof ApiError ? `${err.status}: ${err.message}` : String(err)))
      .finally(() => setLoading(false));
  }, []);

  const cbBadge = (state: string) => {
    if (state === 'closed') return 'bg-green-900/30 text-green-300';
    if (state === 'open') return 'bg-red-900/30 text-red-300';
    return 'bg-yellow-900/30 text-yellow-300';
  };

  return (
    <div className="p-8 max-w-4xl mx-auto space-y-8">
      <div className="border-b border-gray-800 pb-4">
        <h1 className="text-3xl font-bold">AI Providers</h1>
        <p className="text-gray-400 mt-1">
          Provider routing and health status. Provider configuration is managed via server environment variables.
        </p>
      </div>

      {loading && <p className="text-gray-400">Loading provider status…</p>}
      {error && (
        <div className="bg-red-900/20 border border-red-800 text-red-300 p-4 rounded text-sm">
          Failed to load provider status: {error}
        </div>
      )}

      {providers && (
        <>
          <div className="bg-gray-900 p-4 rounded border border-gray-800 flex items-center gap-3">
            <span className={`inline-block w-2 h-2 rounded-full ${providers.status === 'ok' ? 'bg-green-400' : 'bg-red-400'}`} />
            <span className="text-sm text-gray-300">
              Gateway status: <strong className="font-mono">{providers.status}</strong>
            </span>
          </div>

          <div className="space-y-3">
            {Object.entries(providers.providers).map(([name, p]) => (
              <div key={name} className="bg-gray-900 border border-gray-800 rounded p-5">
                <div className="flex justify-between items-start mb-3">
                  <div>
                    <h3 className="font-bold text-lg capitalize">{name.replace(/_/g, ' ')}</h3>
                    <div className="flex gap-2 mt-1">
                      {p.capabilities.is_local && (
                        <span className="bg-blue-900/30 text-blue-300 text-xs px-2 py-0.5 rounded font-mono">LOCAL</span>
                      )}
                      {p.capabilities.is_free_tier && (
                        <span className="bg-green-900/30 text-green-300 text-xs px-2 py-0.5 rounded font-mono">FREE</span>
                      )}
                      {p.capabilities.streaming && (
                        <span className="bg-gray-800 text-gray-400 text-xs px-2 py-0.5 rounded font-mono">STREAM</span>
                      )}
                      {p.capabilities.vision && (
                        <span className="bg-gray-800 text-gray-400 text-xs px-2 py-0.5 rounded font-mono">VISION</span>
                      )}
                    </div>
                  </div>
                  <span className={`px-3 py-1 rounded-full text-xs font-bold uppercase ${cbBadge(p.circuit_breaker_state)}`}>
                    {p.circuit_breaker_state}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      <div className="bg-yellow-900/20 border-l-4 border-yellow-700 p-4 rounded text-sm text-yellow-300">
        <strong>Note:</strong> BYO API key management (per-user encrypted key storage) is a planned feature.
        Currently, provider keys are configured in the server environment. Contact the server administrator to add or change provider keys.
      </div>
    </div>
  );
}
