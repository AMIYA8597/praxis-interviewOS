import { useEffect, useRef, useState, useCallback } from 'react';
import type { MainToRendererChannels } from '../../shared/ipc-types';

export function useRealtimeSession(sessionId: string) {
  const wsRef = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const [events, setEvents] = useState<any[]>([]);
  
  useEffect(() => {
    if (!sessionId) return;
    
    const token = localStorage.getItem('auth-token') || ''; 
    const wsUrl = `${typeof import.meta !== 'undefined' && import.meta.env ? import.meta.env.VITE_WS_URL || 'ws://localhost:8001' : 'ws://localhost:8001'}/ws/sessions/${sessionId}`;
    
    wsRef.current = new WebSocket(wsUrl);
    
    wsRef.current.onopen = () => {
      // Send auth header
      wsRef.current?.send(JSON.stringify({
        type: 'auth',
        token
      }));
      setConnected(true);
    };
    
    wsRef.current.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setEvents(prev => [...prev, data]);
        
        // Dispatch to listeners (coaching HUD, transcript, etc.)
        if (data.type === 'session.ready') {
          console.log('Session ready');
        } else if (data.type === 'session.metrics') {
          // MetricsDisplay will listen to this
          window.dispatchEvent(new CustomEvent('metrics-update', { detail: data }));
        }
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
  
  const sendAudioFrame = useCallback((pcmData: Float32Array) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(pcmData.buffer);  // Binary WebSocket frame
    }
  }, []);
  
  return { connected, events, sendAudioFrame, ws: wsRef.current };
}
