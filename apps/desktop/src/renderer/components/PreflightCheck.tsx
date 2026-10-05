import React, { useState, useEffect } from 'react';
import { supabase } from '../lib/supabase';
import { useAudioCapture } from '../hooks/useAudioCapture';

export interface PreflightStatus {
  microphone: boolean | null;
  audioCapability: boolean | null;
  screenCapture: boolean | null;
  backend: boolean | null;
  auth: boolean | null;
  ready: boolean;
}

export function PreflightCheck({ onReady, onCancel }: { onReady: (mode: string) => void, onCancel: () => void }) {
  const [status, setStatus] = useState<PreflightStatus>({
    microphone: null,
    audioCapability: null,
    screenCapture: null,
    backend: null,
    auth: null,
    ready: false
  });
  
  const [mode, setMode] = useState('mock_interview');
  const [interviewType, setInterviewType] = useState('technical');
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    let isMounted = true;
    
    async function runChecks() {
      const newStatus = { ...status };
      
      // Check auth
      const { data: { session } } = await supabase.auth.getSession();
      newStatus.auth = !!session?.access_token;
      
      // Check backend
      try {
        const apiUrl = (typeof process !== 'undefined' ? process.env.VITE_API_URL : undefined) || 'http://localhost:8000';
        const res = await fetch(`${apiUrl}/api/v1/health`);
        newStatus.backend = res.ok;
      } catch (e) {
        newStatus.backend = false;
      }
      
      // Check mic / audio capability
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        stream.getTracks().forEach(t => t.stop());
        newStatus.microphone = true;
      } catch (e) {
        newStatus.microphone = false;
      }
      
      // We assume OS capability is true if we are in Electron (from window.electronAPI)
      newStatus.audioCapability = !!(window as any).electronAPI;
      newStatus.screenCapture = !!(window as any).electronAPI;

      newStatus.ready = newStatus.auth && newStatus.backend && newStatus.microphone;
      
      if (isMounted) {
        setStatus(newStatus as PreflightStatus);
        setChecking(false);
      }
    }
    
    runChecks();
    
    return () => { isMounted = false; };
  }, []);

  return (
    <div className="bg-gray-900 border border-gray-800 rounded p-6 max-w-lg w-full mx-auto shadow-xl text-gray-200">
      <h2 className="text-2xl font-bold mb-4 tracking-widest uppercase">System Preflight</h2>
      
      <div className="space-y-3 mb-6">
        <div className="flex justify-between items-center p-3 bg-gray-800 rounded border border-gray-700">
          <span className="font-medium">Authentication</span>
          <span className={status.auth === true ? 'text-green-400 font-bold' : status.auth === false ? 'text-red-400 font-bold' : 'text-gray-500'}>
            {status.auth === true ? 'READY' : status.auth === false ? 'FAILED' : 'CHECKING...'}
          </span>
        </div>
        
        <div className="flex justify-between items-center p-3 bg-gray-800 rounded border border-gray-700">
          <span className="font-medium">API Server</span>
          <span className={status.backend === true ? 'text-green-400 font-bold' : status.backend === false ? 'text-red-400 font-bold' : 'text-gray-500'}>
            {status.backend === true ? 'READY' : status.backend === false ? 'FAILED' : 'CHECKING...'}
          </span>
        </div>
        
        <div className="flex justify-between items-center p-3 bg-gray-800 rounded border border-gray-700">
          <span className="font-medium">Microphone</span>
          <span className={status.microphone === true ? 'text-green-400 font-bold' : status.microphone === false ? 'text-red-400 font-bold' : 'text-gray-500'}>
            {status.microphone === true ? 'READY' : status.microphone === false ? 'DENIED' : 'CHECKING...'}
          </span>
        </div>
      </div>
      
      <div className="grid grid-cols-2 gap-4 mb-6">
        <div>
          <label className="block text-sm text-gray-400 mb-2 font-bold uppercase tracking-wider">Mode</label>
          <select 
            value={mode} 
            onChange={e => setMode(e.target.value)}
            className="w-full p-3 bg-gray-800 border border-gray-700 rounded text-white focus:outline-none focus:border-indigo-500"
            disabled={checking}
          >
            <option value="mock_interview">Full Mock Interview</option>
            <option value="drill">Technical Drill</option>
            <option value="freeform">Freeform Practice</option>
          </select>
        </div>
        <div>
          <label className="block text-sm text-gray-400 mb-2 font-bold uppercase tracking-wider">Interview Type</label>
          <select 
            value={interviewType} 
            onChange={e => setInterviewType(e.target.value)}
            className="w-full p-3 bg-gray-800 border border-gray-700 rounded text-white focus:outline-none focus:border-indigo-500"
            disabled={checking}
          >
            <option value="technical">Technical</option>
            <option value="system_design">System Design</option>
            <option value="behavioral">Behavioral / STAR</option>
            <option value="mixed">Mixed</option>
            <option value="screening">Screening</option>
          </select>
        </div>
      </div>
      
      <div className="flex justify-end space-x-4">
        <button 
          onClick={onCancel}
          className="px-6 py-2 bg-gray-800 hover:bg-gray-700 text-white font-medium rounded transition"
        >
          Cancel
        </button>
        <button 
          onClick={() => onReady(JSON.stringify({ mode, interview_type: interviewType }))}
          disabled={checking || !status.ready}
          className="px-6 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded transition disabled:opacity-50"
        >
          {checking ? 'Checking...' : status.ready ? 'START SESSION' : 'NOT READY'}
        </button>
      </div>
    </div>
  );
}
