import React from 'react';

export default function AnalyticsPage() {
  return (
    <div className="p-8 max-w-6xl mx-auto space-y-8">
      
      <div>
        <h1 className="text-3xl font-bold">Candidate Analytics</h1>
        <p className="text-gray-300 mt-2">Aggregate trends across your practice sessions.</p>
      </div>

      <div className="grid grid-cols-3 gap-6">
        <div className="bg-gray-900 p-6 rounded shadow-lg shadow-black/50 border border-gray-800">
          <h3 className="text-gray-400 font-semibold mb-2">Average Pace</h3>
          <div className="text-4xl font-mono text-gray-500 italic text-xl">Unavailable</div>
          <div className="text-gray-500 text-sm mt-2">Waiting for session data</div>
        </div>

        <div className="bg-gray-900 p-6 rounded shadow-lg shadow-black/50 border border-gray-800">
          <h3 className="text-gray-400 font-semibold mb-2">Filler Word Density</h3>
          <div className="text-4xl font-mono text-gray-500 italic text-xl">Unavailable</div>
          <div className="text-gray-500 text-sm mt-2">Waiting for session data</div>
        </div>

        <div className="bg-gray-900 p-6 rounded shadow-lg shadow-black/50 border border-gray-800">
          <h3 className="text-gray-400 font-semibold mb-2">STAR Consistency</h3>
          <div className="text-4xl font-mono text-gray-500 italic text-xl">Unavailable</div>
          <div className="text-gray-500 text-sm mt-2">Waiting for session data</div>
        </div>
      </div>

      <div className="bg-gray-900 p-8 rounded shadow-lg shadow-black/50 border border-gray-800 h-64 flex items-center justify-center">
        <p className="text-gray-500 italic">Complete more practice sessions to view trend graphs over time.</p>
      </div>

    </div>
  );
}
