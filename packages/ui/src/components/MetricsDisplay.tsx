import React from 'react';
import type { SessionMetrics } from '@praxis/types';

interface MetricsDisplayProps {
  metrics: SessionMetrics;
}

export function MetricsDisplay({ metrics }: MetricsDisplayProps) {
  // Helper to color-code metrics (green = good, yellow = fair, red = needs work)
  const getMetricColor = (value: number, goodThreshold: number, fairThreshold: number) => {
    if (goodThreshold > fairThreshold) {
        // Higher is better
        if (value >= goodThreshold) return 'text-green-400';
        if (value >= fairThreshold) return 'text-yellow-400';
        return 'text-red-400';
    } else {
        // Lower is better
        if (value <= goodThreshold) return 'text-green-400';
        if (value <= fairThreshold) return 'text-yellow-400';
        return 'text-red-400';
    }
  };

  return (
    <div className="space-y-3 text-sm">
      
      {/* WPM (Words Per Minute) */}
      <div className="flex justify-between items-center">
        <span className="text-gray-400">WPM</span>
        <span className={`font-mono text-lg ${getMetricColor(metrics.wpm || 0, 120, 80)}`}>
          {metrics.wpm?.toFixed(0) || '—'}
        </span>
        <div className="w-24 h-2 bg-gray-700 rounded-full overflow-hidden">
          <div
            className="h-full bg-blue-500 transition-all"
            style={{ width: `${Math.min((metrics.wpm || 0) / 200 * 100, 100)}%` }}
          />
        </div>
      </div>

      {/* FILLER RATE (% of words that are fillers) */}
      <div className="flex justify-between items-center">
        <span className="text-gray-400">Fillers</span>
        <span className={`font-mono text-lg ${getMetricColor(100 - (metrics.filler_rate || 0) * 100, 95, 85)}`}>
          {(((1 - (metrics.filler_rate || 0)) * 100).toFixed(0))}%
        </span>
        <div className="w-24 h-2 bg-gray-700 rounded-full overflow-hidden">
          <div
            className="h-full bg-purple-500 transition-all"
            style={{ width: `${(1 - (metrics.filler_rate || 0)) * 100}%` }}
          />
        </div>
      </div>

      {/* LONGEST PAUSE */}
      <div className="flex justify-between items-center">
        <span className="text-gray-400">Max Pause</span>
        <span className={`font-mono text-lg ${getMetricColor(3000 - (metrics.longest_pause_ms || 0), 1500, 500)}`}>
          {((metrics.longest_pause_ms || 0) / 1000).toFixed(1)}s
        </span>
        <div className="w-24 h-2 bg-gray-700 rounded-full overflow-hidden">
          <div
            className="h-full bg-orange-500 transition-all"
            style={{ width: `${Math.min((metrics.longest_pause_ms || 0) / 3000 * 100, 100)}%` }}
          />
        </div>
      </div>

      {/* HEDGE COUNT */}
      <div className="flex justify-between items-center">
        <span className="text-gray-400">Hedges</span>
        <span className={`font-mono text-lg ${getMetricColor(metrics.hedge_count || 0, 1, 3)}`}>
          {metrics.hedge_count || 0}
          <span className="text-xs text-gray-500 ml-1">(lower is better)</span>
        </span>
      </div>

      {/* AVERAGE SENTENCE LENGTH */}
      <div className="flex justify-between items-center">
        <span className="text-gray-400">Avg Sentence</span>
        <span className={`font-mono text-lg ${getMetricColor(metrics.avg_sentence_length || 0, 20, 10)}`}>
          {metrics.avg_sentence_length?.toFixed(1) || '—'} words
        </span>
      </div>

      {/* SENTENCE COUNT */}
      <div className="flex justify-between items-center">
        <span className="text-gray-400">Sentences</span>
        <span className="font-mono text-lg text-gray-300">
          {metrics.sentence_count || 0}
        </span>
      </div>

    </div>
  );
}
