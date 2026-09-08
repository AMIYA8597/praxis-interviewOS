import React from 'react';

export default function ApplicationTrackerPage() {
  return (
    <div className="p-8 max-w-6xl mx-auto space-y-8">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">Application Tracker</h1>
        <button className="bg-indigo-600 text-white px-4 py-2 rounded font-bold">+ New Application</button>
      </div>

      <div className="bg-white rounded shadow border overflow-hidden">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-gray-100 border-b">
              <th className="p-4 font-semibold text-gray-600 uppercase text-xs tracking-widest">Company & Role</th>
              <th className="p-4 font-semibold text-gray-600 uppercase text-xs tracking-widest">Status</th>
              <th className="p-4 font-semibold text-gray-600 uppercase text-xs tracking-widest">Sessions</th>
              <th className="p-4 font-semibold text-gray-600 uppercase text-xs tracking-widest">Next Action</th>
            </tr>
          </thead>
          <tbody>
            <tr className="border-b hover:bg-gray-50">
              <td className="p-4">
                <div className="font-bold">Anthropic</div>
                <div className="text-sm text-gray-500">Sr. Inference Engineer</div>
              </td>
              <td className="p-4">
                <span className="bg-blue-100 text-blue-800 px-3 py-1 rounded-full text-xs font-bold">Technical Interview</span>
              </td>
              <td className="p-4">
                <div className="flex items-center space-x-2">
                  <span className="font-mono bg-gray-200 px-2 py-1 rounded text-xs font-bold">3</span>
                  <span className="text-xs text-gray-500">Practice runs</span>
                </div>
              </td>
              <td className="p-4 text-sm text-gray-600">Review CUDA memory layouts</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div className="bg-indigo-50 border border-indigo-200 rounded p-6">
        <h2 className="text-lg font-bold text-indigo-900 mb-2">Cold Outreach Generator</h2>
        <div className="flex space-x-4">
          <input type="text" placeholder="Hiring Manager Name (Optional)" className="border p-2 rounded flex-1" />
          <input type="text" placeholder="Specific detail (e.g. recent funding)" className="border p-2 rounded flex-1" />
          <button className="bg-indigo-600 text-white px-6 py-2 rounded font-bold">Generate Draft</button>
        </div>
        <p className="text-xs text-indigo-500 mt-4 uppercase tracking-widest font-bold">
          ⚠ PRAXIS will never auto-send emails or fabricate recipient facts.
        </p>
      </div>
    </div>
  );
}
