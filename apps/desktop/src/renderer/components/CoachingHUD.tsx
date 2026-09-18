import React, { useEffect, useState, useRef } from 'react';
import { useRealtimeSession } from '../hooks/useRealtimeSession';
import { MetricsDisplay, TranscriptDisplay, CoachingFeedback } from '@praxis/ui';
import type { SessionMetrics, TranscriptSegment } from '@praxis/types';

interface CoachingHUDProps {
  sessionId: string;
  isLive: boolean;
}

export function CoachingHUD({ sessionId, isLive }: CoachingHUDProps) {
  const { connected, events, sendAudioFrame } = useRealtimeSession(sessionId);
  
  // State for each visual component
  const [metrics, setMetrics] = useState<SessionMetrics | null>(null);
  const [transcript, setTranscript] = useState<TranscriptSegment[]>([]);
  const [coachingTips, setCoachingTips] = useState<string[]>([]);
  const [sessionState, setSessionState] = useState<string>('idle');
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  
  // Refs for performance (don't re-render on every update)
  const metricsUpdateTimeRef = useRef<number>(0);
  const transcriptBufferRef = useRef<TranscriptSegment[]>([]);
  
  // EVENT LISTENER 1: Metrics Updates (every ~250ms)
  // This is the PROOF of the dual-path architecture
  useEffect(() => {
    const handleMetricsUpdate = (event: CustomEvent<SessionMetrics>) => {
      const now = performance.now();
      metricsUpdateTimeRef.current = now;
      
      setMetrics({
        ...event.detail,
        // @ts-ignore
        receivedAtMs: now  // Log when metrics arrived
      });
    };
    
    window.addEventListener('metrics-update', handleMetricsUpdate as EventListener);
    return () => window.removeEventListener('metrics-update', handleMetricsUpdate as EventListener);
  }, []);
  
  // EVENT LISTENER 2: Transcript Updates (as they arrive from STT)
  useEffect(() => {
    const handleTranscriptPartial = (event: CustomEvent<TranscriptSegment>) => {
      const segment = event.detail;
      
      // For partial transcripts, update the last segment in place
      if (segment.is_interim) {
        transcriptBufferRef.current = transcriptBufferRef.current.map((s, i) =>
          i === transcriptBufferRef.current.length - 1 ? segment : s
        );
      } else {
        // Final segment: add to buffer
        transcriptBufferRef.current.push(segment);
      }
      
      setTranscript([...transcriptBufferRef.current]);
    };
    
    const handleTranscriptFinal = (event: CustomEvent<TranscriptSegment>) => {
      const segment = event.detail;
      transcriptBufferRef.current.push(segment);
      setTranscript([...transcriptBufferRef.current]);
    };
    
    window.addEventListener('transcript.partial', handleTranscriptPartial as EventListener);
    window.addEventListener('transcript.final', handleTranscriptFinal as EventListener);
    
    return () => {
      window.removeEventListener('transcript.partial', handleTranscriptPartial as EventListener);
      window.removeEventListener('transcript.final', handleTranscriptFinal as EventListener);
    };
  }, []);
  
  // EVENT LISTENER 3: Coaching Feedback (as the backend generates it)
  useEffect(() => {
    const handleCoachingFeedback = (event: CustomEvent<{ tip: string }>) => {
      setCoachingTips(prev => [
        ...prev.slice(-4),  // Keep last 5 tips
        event.detail.tip
      ]);
    };
    
    window.addEventListener('coaching.feedback', handleCoachingFeedback as EventListener);
    return () => window.removeEventListener('coaching.feedback', handleCoachingFeedback as EventListener);
  }, []);
  
  // EVENT LISTENER 4: Session State Changes
  useEffect(() => {
    const handleStateChange = (event: CustomEvent<{ state: string }>) => {
      setSessionState(event.detail.state);
    };
    
    window.addEventListener('session.state-changed', handleStateChange as EventListener);
    return () => window.removeEventListener('session.state-changed', handleStateChange as EventListener);
  }, []);
  
  // TIMER: Update elapsed time every second
  useEffect(() => {
    if (!isLive) return;
    
    const interval = setInterval(() => {
      setElapsedSeconds(prev => prev + 1);
    }, 1000);
    
    return () => clearInterval(interval);
  }, [isLive]);
  
  // MANUAL TIMING VERIFICATION (Logging)
  useEffect(() => {
    if (metrics) {
      const timestamp = performance.now();
      console.log(`[Metrics] ${timestamp} WPM: ${metrics.wpm}`, {
        timestamp,
        wpm: metrics.wpm,
        fillerRate: metrics.filler_rate,
        duration: timestamp - metricsUpdateTimeRef.current
      });
    }
  }, [metrics]);
  
  // RENDER: Four-column layout
  return (
    <div className="flex gap-4 h-full bg-gray-900 p-4 rounded-lg border border-gray-700">
      
      {/* COLUMN 1: METRICS (Left) */}
      <div className="flex-1 space-y-2">
        <h3 className="text-sm font-semibold text-gray-300">Coaching Metrics</h3>
        {metrics ? (
          <MetricsDisplay metrics={metrics} />
        ) : (
          <div className="text-xs text-gray-500">Waiting for metrics...</div>
        )}
      </div>
      
      {/* COLUMN 2: TRANSCRIPT (Center-Left) */}
      <div className="flex-1 space-y-2">
        <h3 className="text-sm font-semibold text-gray-300">Live Transcript</h3>
        <TranscriptDisplay segments={transcript} />
      </div>
      
      {/* COLUMN 3: COACHING TIPS (Center-Right) */}
      <div className="flex-1 space-y-2">
        <h3 className="text-sm font-semibold text-gray-300">Real-Time Coaching</h3>
        <div className="space-y-2 h-32 overflow-y-auto">
          {coachingTips.length === 0 ? (
            <div className="text-xs text-gray-500">Listening...</div>
          ) : (
            coachingTips.map((tip, i) => (
              <CoachingFeedback key={i} message={tip} />
            ))
          )}
        </div>
      </div>
      
      {/* COLUMN 4: SESSION STATE & TIMER (Right) */}
      <div className="flex flex-col justify-between items-end">
        <div className="text-center">
          <div className="text-2xl font-bold text-gray-100">
            {Math.floor(elapsedSeconds / 60)}:{String(elapsedSeconds % 60).padStart(2, '0')}
          </div>
          <div className="text-xs text-gray-400 uppercase tracking-wide">Elapsed</div>
        </div>
        
        <div className="text-center">
          <div className={`text-sm font-medium px-3 py-1 rounded ${
            sessionState === 'READY' ? 'bg-green-900 text-green-100' :
            sessionState === 'SCORING' ? 'bg-yellow-900 text-yellow-100' :
            sessionState === 'INTERVIEWER_TURN' ? 'bg-blue-900 text-blue-100' :
            'bg-gray-700 text-gray-100'
          }`}>
            {sessionState.replace(/_/g, ' ')}
          </div>
          {connected ? (
            <div className="text-xs text-green-400 mt-1">● Connected</div>
          ) : (
            <div className="text-xs text-red-400 mt-1">● Disconnected</div>
          )}
        </div>
      </div>
      
    </div>
  );
}
