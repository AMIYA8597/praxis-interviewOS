import React from 'react';

export default function StoryBankPage() {
  return (
    <div className="p-8 max-w-3xl mx-auto">
      <h1 className="text-3xl font-bold mb-6">STAR Story Bank</h1>
      
      <form className="space-y-6 bg-white p-8 border rounded shadow">
        <div>
          <label className="block text-sm font-medium mb-1">Situation</label>
          <textarea className="w-full border p-2 rounded" rows={2} placeholder="Set the scene and context..."></textarea>
        </div>
        
        <div>
          <label className="block text-sm font-medium mb-1">Task</label>
          <textarea className="w-full border p-2 rounded" rows={2} placeholder="What was your specific responsibility?"></textarea>
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Action</label>
          <textarea className="w-full border p-2 rounded" rows={4} placeholder="What steps did you take? Focus on 'I' not 'We'." ></textarea>
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Result</label>
          <textarea className="w-full border p-2 rounded" rows={2} placeholder="What was the measurable outcome?"></textarea>
        </div>
        
        <div className="flex space-x-4">
          <div className="flex-1">
            <label className="block text-sm font-medium mb-1">Link to Project (Optional)</label>
            <select className="w-full border p-2 rounded">
              <option>Select a project...</option>
              <option>Distributed RAG Pipeline</option>
            </select>
          </div>
          <div className="flex-1">
            <label className="block text-sm font-medium mb-1">Tags</label>
            <input type="text" className="w-full border p-2 rounded" placeholder="Leadership, Conflict..." />
          </div>
        </div>

        <button className="bg-indigo-600 text-white px-6 py-2 rounded font-semibold">Save Story</button>
      </form>
    </div>
  );
}
