import React from 'react';

export default function JobMatchPage() {
  return (
    <div className="p-8 max-w-5xl mx-auto space-y-8">
      
      {/* Blueprint Header */}
      <div className="bg-white p-6 rounded shadow border border-gray-200">
        <h1 className="text-3xl font-bold mb-2">Senior Staff Engineer — Distributed Systems</h1>
        <div className="flex space-x-2 mb-4">
          <span className="bg-indigo-100 text-indigo-800 px-3 py-1 rounded-full text-sm font-semibold">System Design</span>
          <span className="bg-indigo-100 text-indigo-800 px-3 py-1 rounded-full text-sm font-semibold">Technical</span>
        </div>
        
        {/* Streamed Summary */}
        <div className="text-gray-700 bg-gray-50 p-4 rounded border">
          <p>This is a streamed summary of the Job Blueprint. It generates token-by-token so the user never sees a blocking spinner.</p>
        </div>
      </div>

      {/* Explainable Match Score */}
      <div className="bg-white p-6 rounded shadow border border-gray-200">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-2xl font-bold">Candidate Match: <span className="text-green-600">74%</span></h2>
          <span className="text-sm text-gray-500 italic">See how this is calculated</span>
        </div>

        <div className="space-y-4">
          
          <div className="border-l-4 border-green-500 bg-green-50 p-4">
            <h3 className="font-semibold text-green-800">✅ Matched: Kafka / Event Streaming</h3>
            <p className="text-sm text-green-700 mt-2">
              <strong>Evidence from your Resume:</strong> "...architected the high-throughput event bus using Kafka, reducing message latency by 40%."
            </p>
          </div>

          <div className="border-l-4 border-yellow-500 bg-yellow-50 p-4">
            <h3 className="font-semibold text-yellow-800">⚠️ Partial: Kubernetes Administration</h3>
            <p className="text-sm text-yellow-700 mt-2">
              <strong>Evidence from your Resume:</strong> "...deployed services to Kubernetes clusters."
            </p>
          </div>

          <div className="border-l-4 border-red-500 bg-red-50 p-4">
            <h3 className="font-semibold text-red-800">❌ Missing: Rust / Low-Level Optimization</h3>
            <p className="text-sm text-red-700 mt-2">
              No verified evidence found in your profile. 
              <strong> The Prep Pack will heavily probe this gap.</strong>
            </p>
          </div>

        </div>
      </div>

    </div>
  );
}
