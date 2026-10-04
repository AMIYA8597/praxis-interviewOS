import { useRef } from 'react';
import { float32ToPCM16 } from '../lib/audioConvert';

export function useAudioFrameStream(sessionId: string, ws: WebSocket | null) {
  const seqRef = useRef(0);
  
  return {
    sendAudioFrame: (float32Data: Float32Array) => {
      if (!ws || ws.readyState !== WebSocket.OPEN) return;
      
      const pcm16 = float32ToPCM16(float32Data);
      const timestamp = Date.now() / 1000;  // Client-side capture timestamp
      
      const headerLength = 18;
      const totalLength = headerLength + pcm16.byteLength;
      const combined = new Uint8Array(totalLength);
      const dataView = new DataView(combined.buffer);
      
      // Protocol version: 1
      dataView.setUint8(0, 1);
      // Frame type: 1 (AUDIO_FRAME)
      dataView.setUint8(1, 1);
      // Sequence
      dataView.setUint32(2, seqRef.current++, false);
      // Timestamp
      dataView.setFloat64(6, timestamp, false);
      // Payload length
      dataView.setUint32(14, pcm16.byteLength, false);
      
      // Copy PCM payload
      combined.set(new Uint8Array(pcm16.buffer), 18);
      
      ws.send(combined.buffer);
    }
  };
}
