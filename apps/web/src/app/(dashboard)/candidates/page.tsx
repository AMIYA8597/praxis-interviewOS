import React from 'react';
import { Tabs } from '@praxis/ui';

export default function CandidatesPage() {
  return (
    <div className="p-8 max-w-5xl mx-auto">
      <h1 className="text-3xl font-bold mb-6">Candidate Profile</h1>
      
      <div className="space-y-12">
        <section>
          <h2 className="text-2xl font-bold mb-4">Resume Extraction Review</h2>
          <div className="bg-yellow-900/20 border-l-4 border-yellow-600 p-4 mb-8">
            <p className="text-yellow-300 font-semibold">
              The AI has read your resume. Confirm what's accurate so PRAXIS never puts words in your mouth during practice.
            </p>
          </div>

          <div className="bg-gray-900 p-6 rounded shadow-lg shadow-black/50 border border-gray-800">
            <h3 className="text-lg font-bold mb-4">Extracted Fact: Skills</h3>
            <div className="grid grid-cols-2 gap-4">
              <div className="border border-gray-800 p-4 bg-gray-800 text-gray-300">
                <p className="text-sm uppercase tracking-wider mb-2">Source Document</p>
                <p>...proficient in <mark className="bg-yellow-800/50">Python, React, and AWS</mark>...</p>
              </div>
              <div className="border border-gray-800 p-4">
                <p className="text-sm uppercase tracking-wider mb-2">AI Extraction</p>
                <ul className="list-disc pl-4 mb-4">
                  <li>Python</li>
                  <li>React</li>
                  <li>AWS</li>
                </ul>
                <div className="flex space-x-2">
                  <button className="bg-green-600 text-white px-4 py-2 rounded">Confirm</button>
                  <button className="bg-gray-700 text-gray-200 px-4 py-2 rounded">Edit</button>
                  <button className="bg-red-900/30 text-red-300 px-4 py-2 rounded">Reject</button>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section>
          <h2 className="text-2xl font-bold mb-4">STAR Story Bank</h2>
          <form className="space-y-6 bg-gray-900 p-8 border border-gray-800 rounded shadow-lg shadow-black/50">
            <div>
              <label className="block text-sm font-medium mb-1">Situation</label>
              <textarea className="w-full border border-gray-800 p-2 rounded" rows={2} placeholder="Set the scene and context..."></textarea>
            </div>
            
            <div>
              <label className="block text-sm font-medium mb-1">Task</label>
              <textarea className="w-full border border-gray-800 p-2 rounded" rows={2} placeholder="What was your specific responsibility?"></textarea>
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">Action</label>
              <textarea className="w-full border border-gray-800 p-2 rounded" rows={4} placeholder="What steps did you take? Focus on 'I' not 'We'." ></textarea>
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">Result</label>
              <textarea className="w-full border border-gray-800 p-2 rounded" rows={2} placeholder="What was the measurable outcome?"></textarea>
            </div>
            
            <div className="flex space-x-4">
              <div className="flex-1">
                <label className="block text-sm font-medium mb-1">Link to Project (Optional)</label>
                <select className="w-full border border-gray-800 p-2 rounded">
                  <option>Select a project...</option>
                  <option>Distributed RAG Pipeline</option>
                </select>
              </div>
              <div className="flex-1">
                <label className="block text-sm font-medium mb-1">Tags</label>
                <input type="text" className="w-full border border-gray-800 p-2 rounded" placeholder="Leadership, Conflict..." />
              </div>
            </div>

            <button className="bg-indigo-600 text-white px-6 py-2 rounded font-semibold">Save Story</button>
          </form>
        </section>
      </div>
    </div>
  );
}
