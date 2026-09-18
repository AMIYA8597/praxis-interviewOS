import React, { useEffect, useState } from 'react';

interface CoachingFeedbackProps {
  message: string;
  autoFadeAfterMs?: number;
}

export function CoachingFeedback({ message, autoFadeAfterMs = 5000 }: CoachingFeedbackProps) {
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    if (autoFadeAfterMs <= 0) return;
    
    const timer = setTimeout(() => setVisible(false), autoFadeAfterMs);
    return () => clearTimeout(timer);
  }, [message, autoFadeAfterMs]);

  if (!visible) return null;

  return (
    <div className="p-2 bg-blue-900 border-l-4 border-blue-400 rounded-r text-sm text-blue-100 animate-fade-in">
      <div className="flex gap-2">
        <span className="text-blue-400">→</span>
        <span>{message}</span>
      </div>
    </div>
  );
}
