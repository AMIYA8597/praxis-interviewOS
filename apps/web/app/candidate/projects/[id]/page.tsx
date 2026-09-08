import React from 'react';

export default function ProjectDeepDivePage() {
  return (
    <div className="p-8 max-w-4xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">Project Deep Dive</h1>
        <div className="text-sm bg-blue-100 text-blue-800 px-3 py-1 rounded-full">
          This project is 40% complete — richer project data means sharper follow-up questions
        </div>
      </div>

      <form className="space-y-6 bg-white p-8 border rounded shadow">
        <div>
          <label className="block text-sm font-medium mb-1">Project Name *</label>
          <input type="text" className="w-full border p-2 rounded" defaultValue="Distributed RAG Pipeline" />
        </div>
        
        <div>
          <label className="block text-sm font-medium mb-1">Summary *</label>
          <textarea className="w-full border p-2 rounded" rows={3}></textarea>
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Core Problem</label>
          <textarea className="w-full border p-2 rounded" rows={3} placeholder="What was the business or technical problem?"></textarea>
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Architecture & Tech Stack</label>
          <textarea className="w-full border p-2 rounded" rows={3}></textarea>
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Tradeoffs & Failures</label>
          <textarea className="w-full border p-2 rounded" rows={3} placeholder="What didn't work initially?"></textarea>
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Business Impact & Metrics</label>
          <textarea className="w-full border p-2 rounded" rows={3} placeholder="Did revenue increase? Latency drop?"></textarea>
        </div>

        <button className="bg-blue-600 text-white px-6 py-2 rounded font-semibold">Save Project</button>
      </form>
    </div>
  );
}
