"use client";

import React, { useEffect, useState, useCallback } from 'react';
import { listStudyItems, reviewItem } from '@/lib/api/study';
import type { StudyItemResponse } from '@/lib/api/types';
import { ApiError } from '@/lib/api/client';

type ReviewState = 'question' | 'answer' | 'rated';

export default function StudyPage() {
  const [items, setItems] = useState<StudyItemResponse[]>([]);
  const [current, setCurrent] = useState(0);
  const [reviewState, setReviewState] = useState<ReviewState>('question');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [sessionDone, setSessionDone] = useState(false);

  useEffect(() => {
    listStudyItems(undefined, 20)
      .then(page => {
        // Items due first (next_review_at <= now or null means new)
        const now = new Date();
        const due = page.items.filter(
          i => !i.next_review_at || new Date(i.next_review_at) <= now
        );
        setItems(due);
      })
      .catch(err => {
        setError(err instanceof ApiError ? `${err.status}: ${err.message}` : String(err));
      })
      .finally(() => setLoading(false));
  }, []);

  const handleRate = useCallback(async (quality: number) => {
    const item = items[current];
    if (!item) return;
    setSubmitting(true);
    try {
      await reviewItem(item.id, quality);
      if (current + 1 >= items.length) {
        setSessionDone(true);
      } else {
        setCurrent(c => c + 1);
        setReviewState('question');
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  }, [items, current]);

  if (loading) return <div className="p-8 text-gray-400">Loading study items…</div>;
  if (error) return (
    <div className="p-8">
      <div className="bg-red-900/20 border border-red-800 text-red-300 p-4 rounded">
        Failed to load study items: {error}
      </div>
    </div>
  );
  if (items.length === 0) return (
    <div className="p-8 max-w-2xl mx-auto h-screen flex flex-col justify-center text-center">
      <h1 className="text-2xl font-bold mb-4">Study</h1>
      <div className="bg-gray-900 border border-gray-800 rounded p-10 text-gray-400">
        <p className="text-lg mb-2">Nothing due for review.</p>
        <p className="text-sm">Complete practice sessions and PRAXIS will automatically create study cards from your weak answers.</p>
      </div>
    </div>
  );
  if (sessionDone) return (
    <div className="p-8 max-w-2xl mx-auto h-screen flex flex-col justify-center text-center">
      <h1 className="text-2xl font-bold mb-4">Session Complete</h1>
      <div className="bg-gray-900 border border-gray-800 rounded p-10 text-gray-300">
        <p className="text-lg mb-2">All {items.length} item{items.length !== 1 ? 's' : ''} reviewed.</p>
        <p className="text-sm text-gray-500">Come back tomorrow for your next scheduled review.</p>
      </div>
    </div>
  );

  const item = items[current];

  return (
    <div className="p-8 max-w-2xl mx-auto h-screen flex flex-col justify-center">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Daily Review</h1>
        <span className="text-sm text-gray-500 font-mono">{current + 1} / {items.length}</span>
      </div>

      <div className="bg-gray-900 p-8 rounded shadow-xl shadow-black/50 border border-gray-800 space-y-6">
        <h2 className="text-sm font-bold text-indigo-400 uppercase tracking-widest">
          Topic: {item.topic}
        </h2>

        <p className="text-xl leading-relaxed">{item.prompt}</p>

        {reviewState === 'question' && (
          <button
            onClick={() => setReviewState('answer')}
            className="w-full py-3 bg-gray-800 hover:bg-gray-700 text-gray-200 font-semibold rounded transition border border-gray-700"
          >
            Show Reference Answer
          </button>
        )}

        {reviewState === 'answer' && (
          <>
            {item.reference_answer && (
              <div className="bg-gray-800 p-4 rounded border border-gray-700">
                <p className="text-sm text-gray-400 mb-2 font-semibold uppercase tracking-widest">Reference Answer</p>
                <p className="text-gray-300 leading-relaxed">{item.reference_answer}</p>
              </div>
            )}

            <div>
              <p className="text-sm font-semibold mb-4 text-gray-400 text-center">
                How well did you recall and apply this?
              </p>
              <div className="flex justify-center space-x-2">
                {[0, 1, 2, 3, 4, 5].map(q => (
                  <button
                    key={q}
                    onClick={() => handleRate(q)}
                    disabled={submitting}
                    className="w-12 h-12 rounded-full bg-gray-800 hover:bg-indigo-900/30 border border-gray-700 transition font-bold text-gray-300 disabled:opacity-50"
                  >
                    {q}
                  </button>
                ))}
              </div>
              <p className="text-xs text-gray-500 mt-3 text-center">0 = Complete blank · 3 = Recalled with effort · 5 = Perfect</p>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
