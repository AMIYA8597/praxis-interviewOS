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

  const renderMetric = (label: string, value: number | null | undefined, unit: string, goodThreshold?: number, fairThreshold?: number, transform?: (v: number) => number | string) => {
    if (value == null) {
      return (
        <div className="flex justify-between items-center">
          <span className="text-gray-400">{label}</span>
          <span className="font-mono text-lg text-gray-600 italic">Unavailable</span>
        </div>
      );
    }
    
    const displayValue = transform ? transform(value) : value;
    const colorClass = (goodThreshold !== undefined && fairThreshold !== undefined) 
      ? getMetricColor(value, goodThreshold, fairThreshold) 
      : 'text-gray-300';
      
    return (
      <div className="flex justify-between items-center">
        <span className="text-gray-400">{label}</span>
        <span className={`font-mono text-lg ${colorClass}`}>
          {displayValue}{unit}
        </span>
      </div>
    );
  };

  return (
    <div className="space-y-3 text-sm">
      {renderMetric("WPM", metrics.wpm, "", 120, 80, v => v.toFixed(0))}
      {renderMetric("Fillers", metrics.filler_rate, "%", 0.05, 0.15, v => (v * 100).toFixed(0))}
      {renderMetric("Max Pause", metrics.longest_pause_ms, "s", 1500, 3000, v => (v / 1000).toFixed(1))}
      {renderMetric("Hedges", metrics.hedge_count, "", 1, 3)}
      {renderMetric("Avg Sentence", metrics.avg_sentence_length, " words", 20, 10, v => v.toFixed(1))}
      {renderMetric("Sentences", metrics.sentence_count, "")}
    </div>
  );
}
