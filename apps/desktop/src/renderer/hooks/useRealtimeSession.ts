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
    
    let isCancelled = false;
    
    const initWS = async () => {
      const { data: { session } } = await import('../lib/supabase').then(m => m.supabase.auth.getSession());
      if (isCancelled) return;
      const token = session?.access_token || ''; 
      
      // process.env is injected by Electron/Vite at build time and is available in
      // both the renderer and Jest test environments (import.meta is not used here
      // because Jest runs in CommonJS mode and cannot parse import.meta syntax).
      const envUrl = process.env.VITE_REALTIME_URL
        || (process.env.NODE_ENV === 'development' ? 'ws://localhost:8080' : '');
      if (!envUrl) throw new Error('VITE_REALTIME_URL is not configured for production');
      const wsUrl = `${envUrl}/ws/sessions/${sessionId}`;
      
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
          
          const detail = data && typeof data.payload === 'object' && data.payload !== null
            ? { ...data, ...data.payload }
            : data;
          window.dispatchEvent(new CustomEvent(data.type, { detail }));
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
    };
    
    initWS();
    
    return () => {
      isCancelled = true;
      wsRef.current?.close();
    };
  }, [sessionId]);
    
  return { connected, events, sendAudioFrame, ws: wsRef.current };
}
