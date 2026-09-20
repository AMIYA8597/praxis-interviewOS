import { useRef } from 'react';
import { float32ToPCM16 } from '../lib/audioConvert';

export function useAudioFrameStream(sessionId: string, ws: WebSocket | null) {
  const seqRef = useRef(0);
  
  return {
    sendAudioFrame: (float32Data: Float32Array) => {
      if (!ws || ws.readyState !== WebSocket.OPEN) return;
      
      const pcm16 = float32ToPCM16(float32Data);
      const timestamp = Date.now() / 1000;  // Client-side capture timestamp
      
      // Frame header: 4 bytes seq + 8 bytes timestamp + 4 bytes length
      const header = new ArrayBuffer(16);
      const headerView = new DataView(header);
      headerView.setUint32(0, seqRef.current++, false);
      headerView.setFloat64(4, timestamp, false);
      headerView.setUint32(12, pcm16.byteLength, false);
      
      // Send header + PCM as binary frames
      ws.send(header);
      ws.send(pcm16.buffer);
    }
  };
}
