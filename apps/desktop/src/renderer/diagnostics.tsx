import React, { useState, useEffect } from 'react';

export default function DiagnosticsScreen() {
  const [rms, setRms] = useState(0);
  const [micStatus, setMicStatus] = useState('UNTESTED');
  const [loopbackStatus, setLoopbackStatus] = useState('UNTESTED');

  // Stub simulating IPC meter events
  useEffect(() => {
    const interval = setInterval(() => {
      setRms(Math.random() * 100);
    }, 100);
    return () => clearInterval(interval);
  }, []);

  const testAudio = () => {
    setMicStatus('TESTING...');
    setTimeout(() => {
      setMicStatus('PASS');
      setLoopbackStatus('UNAVAILABLE (Windows restricted)');
    }, 3000);
  };

  return (
    <div className="p-8 max-w-2xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold">Hardware Diagnostics</h1>
      <p className="text-gray-600">You must pass the microphone test before entering the Practice Arena.</p>

      <div className="border p-6 rounded shadow space-y-4">
        <div className="flex justify-between items-center">
          <span className="font-semibold">Microphone Status</span>
          <span className={`font-bold ${micStatus === 'PASS' ? 'text-green-600' : 'text-gray-500'}`}>
            {micStatus}
          </span>
        </div>
        
        <div className="flex justify-between items-center">
          <span className="font-semibold">System Audio (Loopback)</span>
          <span className={`font-bold ${loopbackStatus.includes('UNAVAILABLE') ? 'text-yellow-600' : 'text-gray-500'}`}>
            {loopbackStatus}
          </span>
        </div>

        <div className="mt-4">
          <label className="block text-sm font-medium mb-1">Live Audio Level</label>
          <div className="w-full bg-gray-200 h-4 rounded overflow-hidden">
            <div className="bg-green-500 h-full transition-all" style={{ width: `${rms}%` }}></div>
          </div>
        </div>

        <button 
          onClick={testAudio}
          className="mt-4 bg-indigo-600 text-white px-4 py-2 rounded font-semibold w-full"
        >
          Test Capture (3 Seconds)
        </button>
      </div>

      <button 
        disabled={micStatus !== 'PASS'}
        className={`w-full py-3 rounded font-bold text-white ${micStatus === 'PASS' ? 'bg-green-600' : 'bg-gray-400 cursor-not-allowed'}`}
      >
        Enter Practice Arena
      </button>
    </div>
  );
}
