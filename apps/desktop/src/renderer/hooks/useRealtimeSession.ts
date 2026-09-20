import { useEffect, useRef, useState, useCallback } from 'react';
import { useAudioFrameStream } from './useAudioFrameStream';
import type { MainToRendererChannels } from '../../shared/ipc-types';

export function useRealtimeSession(sessionId: string) {
  const wsRef = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const [events, setEvents] = useState<any[]>([]);
  
  // Create audio frame stream once connected
  const { sendAudioFrame } = useAudioFrameStream(sessionId, wsRef.current);

  useEffect(() => {
    if (!sessionId) return;
    
    const token = localStorage.getItem('auth-token') || ''; 
    const envUrl = typeof process !== 'undefined' ? process.env.VITE_WS_URL : undefined;
    const wsUrl = `${envUrl || 'ws://localhost:8001'}/ws/sessions/${sessionId}`;
    
    wsRef.current = new WebSocket(wsUrl);
    
    wsRef.current.onopen = () => {
      // Send auth header
      wsRef.current?.send(JSON.stringify({
        type: 'auth',
        token
      }));
      setConnected(true);
    };
    
    // ONE-CHANGE DISCIPLINE: any new server event type must add both a dispatch line here and a corresponding listener wherever it's consumed, in the same change
    wsRef.current.onmessage = (event) => {
      try {
        if (typeof event.data !== 'string') return;
        const data = JSON.parse(event.data);
        setEvents(prev => [...prev, data]);
        
        // Dispatch identical DOM event names to Envelope.type
        window.dispatchEvent(new CustomEvent(data.type, { detail: data }));
      } catch (err) {
        console.error('Failed to parse WebSocket message', err);
      }
    };
    
    wsRef.current.onerror = (err) => {
      console.error('WebSocket error', err);
      setConnected(false);
    };
    
    wsRef.current.onclose = () => {
      setConnected(false);
    };
    
    return () => {
      wsRef.current?.close();
    };
  }, [sessionId]);
  
  return { connected, events, sendAudioFrame, ws: wsRef.current };
}
