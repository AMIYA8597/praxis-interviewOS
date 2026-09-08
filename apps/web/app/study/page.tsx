import React from 'react';

export default function StudyPage() {
  return (
    <div className="p-8 max-w-2xl mx-auto h-screen flex flex-col justify-center">
      
      <div className="text-center mb-8">
        <h1 className="text-2xl font-bold">Daily Review</h1>
        <p className="text-gray-500">2 items due for review today.</p>
      </div>

      <div className="bg-white p-8 rounded shadow-lg border text-center space-y-8">
        <h2 className="text-sm font-bold text-indigo-600 uppercase tracking-widest">Topic: Distributed Systems</h2>
        
        <p className="text-xl">"What was your specific contribution to the event bus architecture?"</p>
        
        <div className="bg-gray-50 p-4 rounded text-left border">
          <p className="text-sm text-gray-500 mb-2">Your previous weak answer:</p>
          <p className="italic text-gray-700">"I think we used... uh, Kafka for the event bus. It dropped latency by 40%."</p>
          <p className="text-xs text-red-500 mt-2 font-semibold">Missing: Action (STAR), Contradicts verified 20% metric.</p>
        </div>

        <div>
          <p className="text-sm font-semibold mb-4 text-gray-500">How would you rate your mental rewrite?</p>
          <div className="flex justify-center space-x-2">
            {[0, 1, 2, 3, 4, 5].map(rating => (
              <button key={rating} className="w-12 h-12 rounded-full bg-gray-100 hover:bg-indigo-100 border transition font-bold text-gray-700">
                {rating}
              </button>
            ))}
          </div>
          <p className="text-xs text-gray-400 mt-4">0 = Blank, 5 = Perfect execution</p>
        </div>
      </div>

    </div>
  );
}
