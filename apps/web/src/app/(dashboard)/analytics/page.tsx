import React from 'react';

export default function AnalyticsPage() {
  return (
    <div className="p-8 max-w-6xl mx-auto space-y-8">
      
      <div>
        <h1 className="text-3xl font-bold">Candidate Analytics</h1>
        <p className="text-gray-300 mt-2">Aggregate trends across 14 practice sessions.</p>
      </div>

      <div className="grid grid-cols-3 gap-6">
        <div className="bg-gray-900 p-6 rounded shadow-lg shadow-black/50 border border-gray-800">
          <h3 className="text-gray-400 font-semibold mb-2">Average Pace</h3>
          <div className="text-4xl font-mono">142 <span className="text-lg">WPM</span></div>
          <div className="text-green-500 text-sm mt-2 font-bold">↑ 5% this week</div>
        </div>

        <div className="bg-gray-900 p-6 rounded shadow-lg shadow-black/50 border border-gray-800">
          <h3 className="text-gray-400 font-semibold mb-2">Filler Word Density</h3>
          <div className="text-4xl font-mono">3.2%</div>
          <div className="text-red-500 text-sm mt-2 font-bold">↑ 1.2% in System Design</div>
        </div>

        <div className="bg-gray-900 p-6 rounded shadow-lg shadow-black/50 border border-gray-800">
          <h3 className="text-gray-400 font-semibold mb-2">STAR Consistency</h3>
          <div className="text-4xl font-mono">68%</div>
          <div className="text-gray-400 text-sm mt-2 font-semibold">Missing 'Action' most frequently</div>
        </div>
      </div>

      <div className="bg-gray-900 p-8 rounded shadow-lg shadow-black/50 border border-gray-800 h-64 flex items-center justify-center">
        <p className="text-gray-400 italic">[ Recharts Placeholder: Line graph showing WPM vs Filler Density over time ]</p>
      </div>

    </div>
  );
}
