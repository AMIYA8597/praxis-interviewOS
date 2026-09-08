import React from 'react';

export default function CandidateReviewPage() {
  return (
    <div className="p-8 max-w-4xl mx-auto">
      <h1 className="text-3xl font-bold mb-4">Resume Extraction Review</h1>
      
      <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4 mb-8">
        <p className="text-yellow-800 font-semibold">
          The AI has read your resume. Confirm what's accurate so PRAXIS never puts words in your mouth during practice.
        </p>
      </div>

      <div className="space-y-8">
        {/* Stub for fact iteration */}
        <div className="bg-white p-6 rounded shadow border">
          <h2 className="text-xl font-bold mb-4">Extracted Fact: Skills</h2>
          <div className="grid grid-cols-2 gap-4">
            <div className="border p-4 bg-gray-50 text-gray-600">
              <p className="text-sm uppercase tracking-wider mb-2">Source Document</p>
              <p>...proficient in <mark className="bg-yellow-200">Python, React, and AWS</mark>...</p>
            </div>
            <div className="border p-4">
              <p className="text-sm uppercase tracking-wider mb-2">AI Extraction</p>
              <ul className="list-disc pl-4 mb-4">
                <li>Python</li>
                <li>React</li>
                <li>AWS</li>
              </ul>
              <div className="flex space-x-2">
                <button className="bg-green-600 text-white px-4 py-2 rounded">Confirm</button>
                <button className="bg-gray-200 text-gray-800 px-4 py-2 rounded">Edit</button>
                <button className="bg-red-100 text-red-800 px-4 py-2 rounded">Reject</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
