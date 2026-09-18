import React, { useEffect, useRef } from 'react';
import type { TranscriptSegment } from '@praxis/types';

interface TranscriptDisplayProps {
  segments: TranscriptSegment[];
}

export function TranscriptDisplay({ segments }: TranscriptDisplayProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new segments arrive
  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [segments]);

  return (
    <div
      ref={containerRef}
      className="h-32 overflow-y-auto bg-gray-950 border border-gray-700 rounded p-2 space-y-2 text-xs font-mono"
    >
      {segments.length === 0 ? (
        <div className="text-gray-600">Waiting for speech...</div>
      ) : (
        segments.map((segment, i) => (
          <div
            key={segment.segment_id || i}
            className={`pb-1 border-b border-gray-800 last:border-0 ${
              segment.is_interim ? 'opacity-50 italic' : 'opacity-100'
            }`}
          >
            {/* Speaker label */}
            <div className={`text-[10px] font-semibold uppercase tracking-wider ${
              segment.speaker === 'interviewer' ? 'text-blue-400' : 'text-green-400'
            }`}>
              {segment.speaker}
            </div>
            
            {/* Segment text */}
            <div className="text-gray-200 leading-tight">
              {segment.text}
            </div>
            
            {/* Confidence indicator (interim segments have lower confidence) */}
            {segment.is_interim && (
              <div className="text-[10px] text-gray-600 mt-0.5">
                Confidence: {((segment.confidence || 0) * 100).toFixed(0)}%
              </div>
            )}
          </div>
        ))
      )}
    </div>
  );
}
