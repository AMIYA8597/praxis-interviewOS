import React, { useState } from 'react';

export default function StudyWorkbench() {
  const [hintLevel, setHintLevel] = useState(1);
  
  const hints = {
    level1: "The problem asks to reverse a singly linked list in-place. The core challenge is maintaining reference pointers without breaking the chain.",
    level2: "Use three pointers: `prev`, `curr`, and `next`. Iterate through the list, temporarily storing `next`, reversing `curr.next` to point to `prev`, and advancing the pointers.",
    level3: "```python\nwhile curr:\n  nxt = curr.next\n  curr.next = prev\n  prev = curr\n  curr = nxt\nreturn prev\n```\nExplanation: Time complexity is O(N). Space is O(1)."
  };

  return (
    <div className="p-8 max-w-6xl mx-auto flex gap-8">
      
      {/* Visual Capture Preview */}
      <div className="w-1/2 space-y-4">
        <h1 className="text-2xl font-bold">Captured Problem</h1>
        <div className="bg-gray-100 p-4 rounded border h-96 flex items-center justify-center">
          <p className="text-gray-400 font-mono italic">[ Image / Screenshot Preview ]</p>
        </div>
        <div className="flex justify-between items-center">
          <span className="bg-indigo-100 text-indigo-800 px-3 py-1 rounded text-sm font-bold tracking-widest uppercase">Coding</span>
          <button className="text-sm text-gray-500 hover:text-indigo-600 transition font-semibold">Rescan (Ctrl+Shift+S)</button>
        </div>
      </div>

      {/* Graduated Hint Ladder */}
      <div className="w-1/2 flex flex-col space-y-6">
        <div className="flex justify-between items-end border-b pb-4">
          <h2 className="text-2xl font-bold">Hint Ladder</h2>
          <span className="text-sm font-mono text-gray-500">Level {hintLevel} of 3</span>
        </div>

        {/* Level 1 */}
        <div className="bg-white p-6 rounded shadow border-l-4 border-indigo-500">
          <h3 className="text-xs uppercase tracking-widest font-bold text-indigo-500 mb-2">Level 1: Clarify</h3>
          <p className="text-gray-800">{hints.level1}</p>
        </div>

        {/* Level 2 */}
        {hintLevel >= 2 ? (
          <div className="bg-white p-6 rounded shadow border-l-4 border-blue-500">
            <h3 className="text-xs uppercase tracking-widest font-bold text-blue-500 mb-2">Level 2: Approach</h3>
            <p className="text-gray-800">{hints.level2}</p>
          </div>
        ) : (
          <button 
            onClick={() => setHintLevel(2)}
            className="p-4 border-2 border-dashed border-gray-300 rounded text-gray-400 hover:text-blue-500 hover:border-blue-500 font-semibold transition"
          >
            Reveal Algorithm Approach
          </button>
        )}

        {/* Level 3 */}
        {hintLevel >= 3 ? (
          <div className="bg-white p-6 rounded shadow border-l-4 border-green-500">
            <h3 className="text-xs uppercase tracking-widest font-bold text-green-500 mb-2">Level 3: Full Solution</h3>
            <pre className="text-sm text-gray-800 bg-gray-50 p-4 rounded">{hints.level3}</pre>
            
            <button className="mt-6 w-full bg-indigo-600 text-white font-bold py-3 rounded shadow hover:bg-indigo-700 transition">
              Send concept to Study Plan
            </button>
          </div>
        ) : (
          hintLevel === 2 && (
            <button 
              onClick={() => setHintLevel(3)}
              className="p-4 border-2 border-dashed border-gray-300 rounded text-gray-400 hover:text-green-500 hover:border-green-500 font-semibold transition"
            >
              Reveal Code Implementation
            </button>
          )
        )}
      </div>

    </div>
  );
}
