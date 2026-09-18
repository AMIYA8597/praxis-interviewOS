import React, { useState } from 'react';
import { CoachingHUD } from '../components/CoachingHUD';

export function PracticeArenaPage() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sessionLive, setSessionLive] = useState(false);
  const selectedJobId = 'dummy-job'; // Replace with actual job selection state

  // When "Start Practice" button clicked:
  const handleStartPractice = async () => {
    try {
      // 1. Create a session on backend
      const apiUrl = typeof import.meta !== 'undefined' && import.meta.env ? import.meta.env.VITE_API_URL || 'http://localhost:8000' : 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/sessions`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('auth-token')}` 
        },
        body: JSON.stringify({ target_job_id: selectedJobId })
      });
      const data = await response.json();
      setSessionId(data.session_id || 'test-session-id');
      setSessionLive(true);
    } catch (e) {
      console.error('Failed to create session, falling back to test session', e);
      setSessionId('test-session-id');
      setSessionLive(true);
    }
  };

  return (
    <div className="h-screen bg-gray-900 p-4 flex flex-col">
      <h1 className="text-2xl font-bold text-gray-100 mb-4">Practice Arena</h1>
      
      {sessionLive && sessionId ? (
        <CoachingHUD sessionId={sessionId} isLive={true} />
      ) : (
        <div className="flex items-center justify-center h-full">
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
