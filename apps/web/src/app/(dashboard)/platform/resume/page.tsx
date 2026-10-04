import React from 'react';

export default function ResumeBuilderPage() {
  return (
    <div className="p-8 max-w-5xl mx-auto space-y-8">
      <h1 className="text-3xl font-bold">Tailored Resume Builder</h1>
      <p className="text-zinc-400">Generated against: Senior Staff Engineer — Distributed Systems</p>

      <div className="bg-zinc-900 p-6 rounded border border-zinc-700">
        <h2 className="text-xl font-bold mb-4">Professional Experience</h2>

        <div className="border border-zinc-700 rounded p-4 bg-zinc-800 mb-4">
          <div className="flex space-x-8">
            <div className="w-1/2">
              <h3 className="text-xs uppercase font-bold text-zinc-500 mb-2">Original</h3>
              <p className="text-sm text-zinc-300 italic">"Built an event bus with Kafka."</p>
            </div>
            
            <div className="w-1/2 border-l pl-8 border-indigo-200">
              <h3 className="text-xs uppercase font-bold text-indigo-600 mb-2">Tailored for JD</h3>
              <p className="text-sm text-zinc-100 font-semibold mb-2">
                "Architected a high-throughput event bus using Kafka, reducing message latency by 40% to meet hard realtime constraints."
              </p>
              
              <div className="mt-4 flex flex-col space-y-2">
                <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded inline-block w-max font-mono">
                  Targets JD: Streaming Architectures
                </span>
                <span className="text-xs bg-zinc-700 text-zinc-300 px-2 py-1 rounded inline-block w-max font-mono flex items-center cursor-pointer hover:bg-zinc-600">
                  <span className="mr-1">🔗</span> Provenance: chunk_9872
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="flex space-x-4">
        <button className="bg-indigo-600 text-white px-6 py-2 rounded font-bold hover:bg-indigo-700">Export to PDF</button>
        <button className="bg-zinc-700 text-zinc-200 px-6 py-2 rounded font-bold hover:bg-zinc-600">Export to Markdown</button>
      </div>
    </div>
  );
}
