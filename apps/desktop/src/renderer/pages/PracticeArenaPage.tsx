import React, { useState } from 'react';
import { CoachingHUD } from '../components/CoachingHUD';
import { PreflightCheck } from '../components/PreflightCheck';
import { supabase } from '../lib/supabase';

export function PracticeArenaPage() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sessionLive, setSessionLive] = useState(false);
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showPreflight, setShowPreflight] = useState(false);

  const handleStartPractice = async (modePayload: string) => {
    try {
      setError(null);

      const { data: { session } } = await supabase.auth.getSession();
      if (!session?.access_token) {
        setError('Not authenticated. Please sign in again.');
        setShowPreflight(false);
        return;
      }

      const apiUrl = (typeof process !== 'undefined' ? process.env.VITE_API_URL : undefined) || 'http://localhost:8000';
      const modeData = JSON.parse(modePayload);
      const response = await fetch(`${apiUrl}/api/v1/sessions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session.access_token}`,
        },
        body: JSON.stringify({ target_job_id: selectedJobId, ...modeData }),
      });

      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.detail ?? `Server returned ${response.status}`);
      }

      const data = await response.json();
      if (!data.session_id) {
        throw new Error('No session_id in response');
      }
      setSessionId(data.session_id);
      setSessionLive(true);
      setShowPreflight(false);
    } catch (e) {
      console.error('Failed to create session', e);
      setError((e as Error).message);
      setShowPreflight(false);
    }
  };

  return (
    <div className="h-screen bg-gray-900 p-4 flex flex-col relative overflow-hidden">
      <h1 className="text-2xl font-bold text-gray-100 mb-4 uppercase tracking-widest">Practice Arena</h1>

      {sessionLive && sessionId ? (
        <CoachingHUD sessionId={sessionId} isLive={true} />
      ) : showPreflight ? (
        <div className="flex flex-col items-center justify-center h-full absolute inset-0 bg-gray-950/80 backdrop-blur-sm z-10">
          <PreflightCheck 
            onReady={handleStartPractice} 
            onCancel={() => setShowPreflight(false)} 
          />
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center h-full">
          {error && (
            <div className="mb-4 p-4 bg-red-900/30 border border-red-800 text-red-300 rounded max-w-lg w-full text-center">
              <h3 className="font-bold">Failed to Start Practice</h3>
              <p>{error}</p>
              <p className="text-sm mt-2 opacity-80">Check that the API server is running and reachable.</p>
            </div>
          )}
          <button
            onClick={() => setShowPreflight(true)}
            className="px-8 py-4 bg-indigo-600 hover:bg-indigo-700 text-white font-bold tracking-wider uppercase rounded shadow-lg transition"
          >
            Start Practice Interview
          </button>
        </div>
      )}
    </div>
  );
}
