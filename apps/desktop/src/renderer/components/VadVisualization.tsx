import React, { useEffect, useState } from 'react';

export function VadVisualization() {
  const [confidence, setConfidence] = useState(0);
  
  useEffect(() => {
    const handleMetrics = (event: any) => {
      const data = event.detail;
      // Using a proxy for confidence, or extracting from data
      if (data && data.metrics && typeof data.metrics.speech_confidence === 'number') {
        setConfidence(data.metrics.speech_confidence);
      } else {
        // Fallback for VAD confidence proxy
        setConfidence(prev => (prev > 0.5 ? 0 : 1)); 
      }
    };
    
    window.addEventListener('metrics-update', handleMetrics);
    return () => window.removeEventListener('metrics-update', handleMetrics);
  }, []);
  
  return (
    <div className="flex items-center gap-2">
      <span className="text-sm text-gray-400">Listening...</span>
      <div className="w-24 h-2 bg-gray-700 rounded-full overflow-hidden">
        <div
          className={`h-full transition-all ${
            confidence > 0.5 ? 'bg-green-500' : 'bg-gray-500'
          }`}
          style={{ width: `${Math.max(10, confidence * 100)}%` }}
        />
      </div>
    </div>
  );
}
