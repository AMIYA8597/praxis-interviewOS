import React, { useState, useEffect } from 'react';

export default function LiveArena() {
  const [hudMetrics, setHudMetrics] = useState({ wpm: 0, filler_rate_pct: 0, last_pause_ms: 0 });
  const [transcript, setTranscript] = useState("I think we used... uh, Kafka for the event bus.");
  const [latency, setLatency] = useState(124);

  // Stub simulating 4Hz DSP WebSocket updates
  useEffect(() => {
    const interval = setInterval(() => {
      setHudMetrics({
        wpm: Math.floor(Math.random() * (150 - 110) + 110),
        filler_rate_pct: Math.floor(Math.random() * 5),
        last_pause_ms: Math.floor(Math.random() * 800)
      });
      setLatency(Math.floor(Math.random() * (140 - 110) + 110));
    }, 250);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex h-screen bg-gray-900 text-gray-100 font-sans">
      
      {/* Main Interview Pane */}
      <div className="flex-1 flex flex-col p-8 border-r border-gray-800">
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-xl font-bold tracking-widest text-gray-400">PRAXIS / LIVE</h1>
          <div className="flex items-center space-x-2 text-xs font-mono bg-gray-800 px-3 py-1 rounded">
            <div className={`w-2 h-2 rounded-full ${latency < 200 ? 'bg-green-500' : 'bg-red-500'}`}></div>
            <span>E2E Latency: {latency}ms</span>
          </div>
        </div>

        <div className="flex-1">
          <h2 className="text-sm uppercase tracking-widest text-indigo-400 mb-4">Interviewer</h2>
          <p className="text-2xl font-light mb-12">"Can you elaborate on exactly what your personal contribution was to the Kafka architecture?"</p>
          
          <h2 className="text-sm uppercase tracking-widest text-green-400 mb-4">You</h2>
          <p className="text-xl text-gray-300">{transcript}</p>
        </div>

        <div className="flex space-x-4">
          <button className="px-6 py-3 bg-red-900/50 hover:bg-red-900 text-red-200 rounded font-bold transition">End Session</button>
          <button className="px-6 py-3 bg-gray-800 hover:bg-gray-700 rounded font-bold transition">Pause</button>
        </div>
      </div>

      {/* Pure-DSP Coaching HUD */}
      <div className="w-80 bg-gray-950 p-6 flex flex-col">
        <h2 className="text-sm uppercase tracking-widest text-gray-500 mb-8 border-b border-gray-800 pb-2">Coaching HUD</h2>
        
        <div className="space-y-8">
          <div>
            <div className="flex justify-between mb-1">
              <span className="text-gray-400">Pace (WPM)</span>
              <span className="font-mono font-bold">{hudMetrics.wpm}</span>
            </div>
            <div className="h-2 bg-gray-800 rounded overflow-hidden">
              <div className={`h-full ${hudMetrics.wpm > 160 ? 'bg-yellow-500' : 'bg-green-500'}`} style={{ width: `${Math.min(hudMetrics.wpm / 2, 100)}%` }}></div>
            </div>
          </div>

          <div>
            <div className="flex justify-between mb-1">
              <span className="text-gray-400">Filler Words</span>
              <span className="font-mono font-bold text-yellow-500">{hudMetrics.filler_rate_pct}%</span>
            </div>
            <div className="h-2 bg-gray-800 rounded overflow-hidden">
              <div className="h-full bg-yellow-500 transition-all" style={{ width: `${hudMetrics.filler_rate_pct * 10}%` }}></div>
            </div>
          </div>

          <div>
            <div className="flex justify-between mb-1">
              <span className="text-gray-400">Longest Pause</span>
              <span className="font-mono font-bold">{hudMetrics.last_pause_ms}ms</span>
            </div>
          </div>
        </div>

        <div className="mt-auto pt-6 border-t border-gray-800">
          <p className="text-xs text-gray-600">HUD telemetry is computed via pure DSP. It will continue to update during LLM reasoning spikes.</p>
        </div>
      </div>

    </div>
  );
}
