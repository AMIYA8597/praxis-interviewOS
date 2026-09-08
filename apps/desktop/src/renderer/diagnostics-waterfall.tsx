import React from 'react';

export default function DiagnosticsWaterfall() {
  return (
    <div className="p-8 max-w-5xl mx-auto space-y-6 font-sans bg-gray-950 text-gray-100 h-screen">
      
      <div className="border-b border-gray-800 pb-4">
        <h1 className="text-2xl font-bold tracking-widest text-gray-300">PRAXIS TELEMETRY</h1>
        <p className="text-gray-500 mt-1">Live OpenTelemetry Trace: Last Completed Turn</p>
      </div>

      <div className="bg-gray-900 border border-gray-800 rounded p-6 font-mono text-sm">
        
        {/* Total Latency Header */}
        <div className="flex justify-between items-center mb-8 border-b border-gray-800 pb-4">
          <span className="text-gray-400">Total End-to-End Latency (VAD to TTS)</span>
          <span className="text-3xl text-green-400 font-bold">214 ms</span>
        </div>

        {/* Waterfall Nodes */}
        <div className="space-y-4">
          
          <div className="flex items-center">
            <div className="w-48 text-gray-500">1. Audio Capture</div>
            <div className="flex-1 flex items-center">
              <div className="h-4 bg-blue-900 rounded" style={{ width: '5%' }}></div>
              <span className="ml-4 text-blue-400">12 ms</span>
            </div>
          </div>

          <div className="flex items-center">
            <div className="w-48 text-gray-500">2. VAD Envelope</div>
            <div className="flex-1 flex items-center">
              <div className="w-[5%]"></div>
              <div className="h-4 bg-indigo-900 rounded" style={{ width: '2%' }}></div>
              <span className="ml-4 text-indigo-400">4 ms</span>
            </div>
          </div>

          <div className="flex items-center">
            <div className="w-48 text-gray-500">3. Partial STT</div>
            <div className="flex-1 flex items-center">
              <div className="w-[7%]"></div>
              <div className="h-4 bg-purple-900 rounded" style={{ width: '20%' }}></div>
              <span className="ml-4 text-purple-400">42 ms</span>
            </div>
          </div>

          <div className="flex items-center">
            <div className="w-48 text-gray-500">4. Gateway Reasoning</div>
            <div className="flex-1 flex items-center">
              <div className="w-[27%]"></div>
              <div className="h-4 bg-yellow-900 rounded" style={{ width: '45%' }}></div>
              <span className="ml-4 text-yellow-500">110 ms</span>
            </div>
          </div>

          <div className="flex items-center">
            <div className="w-48 text-gray-500">5. TTS First-Token</div>
            <div className="flex-1 flex items-center">
              <div className="w-[72%]"></div>
              <div className="h-4 bg-green-900 rounded" style={{ width: '20%' }}></div>
              <span className="ml-4 text-green-400">46 ms</span>
            </div>
          </div>

        </div>

      </div>

      <div className="text-right">
        <button className="text-sm bg-gray-800 hover:bg-gray-700 text-gray-300 px-4 py-2 rounded transition">
          Export Trace to Jaeger
        </button>
      </div>

    </div>
  );
}
