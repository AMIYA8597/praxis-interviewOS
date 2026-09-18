import { useState, useCallback, useRef } from 'react';

export function useAudioCapture(onAudioFrame?: (data: Float32Array) => void) {
  const [isCapturing, setIsCapturing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  
  const startCapture = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: false  // Don't auto-adjust gain; let VAD see natural levels
        }
      });
      
      mediaStreamRef.current = stream;
      const audioContext = new (window.AudioContext || 
                               (window as any).webkitAudioContext)();
      audioContextRef.current = audioContext;
      
      const source = audioContext.createMediaStreamSource(stream);
      
      // Create a script processor for frame-by-frame audio (Phase 2.11)
      const processor = audioContext.createScriptProcessor(
        4096,  // buffer size = ~85ms at 48kHz
        1,     // input channels (mono)
        1      // output channels
      );
      
      processor.onaudioprocess = (event) => {
        const audioData = event.inputBuffer.getChannelData(0);
        // Send to backend via WebSocket (Phase 4.7 will wire this)
        onAudioFrame?.(new Float32Array(audioData));
      };
      
      source.connect(processor);
      processor.connect(audioContext.destination);
      
      processorRef.current = processor;
      setIsCapturing(true);
    } catch (err) {
      setError((err as Error).message);
    }
  }, [onAudioFrame]);
  
  const stopCapture = useCallback(() => {
    processorRef.current?.disconnect();
    mediaStreamRef.current?.getTracks().forEach(t => t.stop());
    audioContextRef.current?.close();
    setIsCapturing(false);
  }, []);
  
  return { isCapturing, error, startCapture, stopCapture };
}
