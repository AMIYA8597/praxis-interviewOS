import React, { useState } from 'react';
import { CoachingHUD } from '../components/CoachingHUD';

export function PracticeArenaPage() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sessionLive, setSessionLive] = useState(false);
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);

  const [error, setError] = useState<string | null>(null);

  // When "Start Practice" button clicked:
  const handleStartPractice = async () => {
    try {
      setError(null);
      // 1. Create a session on backend
      const apiUrl = (typeof process !== 'undefined' ? process.env.VITE_API_URL : undefined) || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/v1/sessions`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('auth-token')}` 
        },
        body: JSON.stringify({ target_job_id: selectedJobId })
      });
      if (!response.ok) {
        throw new Error(`Server returned ${response.status}`);
      }
      const data = await response.json();
      if (!data.session_id) {
         throw new Error("No session_id in response");
      }
      setSessionId(data.session_id);
      setSessionLive(true);
    } catch (e) {
      console.error('Failed to create session', e);
      setError((e as Error).message);
    }
  };

  return (
    <div className="h-screen bg-gray-900 p-4 flex flex-col">
      <h1 className="text-2xl font-bold text-gray-100 mb-4">Practice Arena</h1>
      
      {sessionLive && sessionId ? (
        <CoachingHUD sessionId={sessionId} isLive={true} />
      ) : (
        <div className="flex flex-col items-center justify-center h-full">
          {error && (
            <div className="mb-4 p-4 bg-red-900 text-red-100 rounded">
              <h3 className="font-bold">Failed to Start Practice</h3>
              <p>{error}</p>
              <p className="text-sm mt-2 opacity-80">Check that the API server is running and reachable.</p>
            </div>
          )}
          <button
            onClick={handleStartPractice}
            className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded"
          >
            Start Practice Interview
          </button>
        </div>
      )}
    </div>
  );
}
