import React from 'react';

export default function DebriefPage() {
  return (
    <div className="p-8 max-w-4xl mx-auto space-y-8">
      
      <div className="flex justify-between items-end border-b pb-6">
        <div>
          <h1 className="text-3xl font-bold">Session Debrief</h1>
          <p className="text-zinc-400 mt-2">Senior Staff Engineer — Distributed Systems</p>
        </div>
        <div className="text-right">
          <div className="text-sm font-semibold text-zinc-500 uppercase tracking-widest">Pace</div>
          <div className="text-2xl font-mono">138 WPM</div>
        </div>
      </div>

      <div className="bg-zinc-900 p-6 rounded border border-zinc-700">
        <h2 className="text-xl font-bold mb-4">AI Summary</h2>
        <p className="text-zinc-300 leading-relaxed">
          You demonstrated strong architectural knowledge, particularly around event-streaming. 
          However, your STAR structuring was inconsistent in behavioral answers. 
          Your filler word rate spiked from 2% to 6% during the Kubernetes deep-dive, suggesting a drop in confidence.
        </p>
      </div>

      <div className="space-y-4">
        <h2 className="text-xl font-bold">Turn Breakdown</h2>
        
        <div className="border border-zinc-700 rounded p-4 bg-zinc-900">
          <div className="flex justify-between items-center mb-2">
            <span className="font-semibold text-indigo-700">Q: Can you elaborate on your specific contribution to the Kafka architecture?</span>
            <div className="flex space-x-2">
              <span className="bg-red-100 text-red-800 text-xs px-2 py-1 rounded font-bold">Action Missing (STAR)</span>
              <span className="bg-green-100 text-green-800 text-xs px-2 py-1 rounded font-bold">Relevant</span>
            </div>
          </div>
          <p className="text-zinc-400 italic mb-4">"I think we used... uh, Kafka for the event bus. It dropped latency by 40%."</p>
          
          <div className="bg-yellow-50 border-l-4 border-yellow-400 p-3 mb-4 text-sm text-yellow-800">
            <strong>Ungrounded Claim:</strong> You claimed a 40% latency drop, but your resume says 20%. Ensure metric consistency.
          </div>

          <button className="text-sm bg-indigo-600 text-white px-4 py-2 rounded shadow hover:bg-indigo-700 transition">
            Add to Study Plan
          </button>
        </div>
      </div>

    </div>
  );
}
