import { useState, useCallback, useRef } from 'react';

export type CaptureDiagnostic = {
  os: string;
  hasLoopback: boolean;
  permissionGranted: boolean;
  message: string;
  fallbackToMic: boolean;
};

export function useAudioCapture(onAudioFrame?: (data: Float32Array) => void) {
  const [isCapturing, setIsCapturing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [diagnostic, setDiagnostic] = useState<CaptureDiagnostic | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const processorRef = useRef<AudioWorkletNode | null>(null);
  
  const startCapture = useCallback(async () => {
    try {
      let stream: MediaStream;
      let usedFallback = false;
      let diagMessage = 'System audio capture successful.';
      let hasLoopback = false;

      // Capability detection
      try {
        const sources = await window.electronAPI.audioGetSources();
        hasLoopback = sources.hasLoopback;
      } catch (e) {
        console.warn("Could not get audio sources from main", e);
      }

      try {
        if (!hasLoopback) {
          throw new Error("No loopback source detected by OS.");
        }
        
        stream = await navigator.mediaDevices.getUserMedia({
          audio: {
            mandatory: {
              chromeMediaSource: 'desktop'
            }
          } as any,
          video: {
            mandatory: {
              chromeMediaSource: 'desktop',
              maxWidth: 1,
              maxHeight: 1
            }
          } as any
        });
        stream.getVideoTracks().forEach(track => track.stop());
      } catch (systemErr: any) {
        usedFallback = true;
        diagMessage = `System audio capture unavailable: ${systemErr.message}. The OS restricts direct desktop audio capture. Falling back to microphone only. You may need to use speakers instead of headphones to capture the interviewer's voice.`;
        
        stream = await navigator.mediaDevices.getUserMedia({
          audio: {
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: false
          }
        });
      }

      const os = await window.electronAPI.systemGetStatus().then((res: any) => res.os).catch(() => 'unknown');
      setDiagnostic({
        os,
        hasLoopback,
        permissionGranted: true,
        message: diagMessage,
        fallbackToMic: usedFallback
      });
      
      mediaStreamRef.current = stream;
      const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
      audioContextRef.current = audioContext;
      
      const source = audioContext.createMediaStreamSource(stream);
      const workletCode = `
        class PCMProcessor extends AudioWorkletProcessor {
          process(inputs, outputs, parameters) {
            const input = inputs[0];
            if (input.length > 0) {
              const channelData = input[0];
              this.port.postMessage(channelData);
            }
            return true;
          }
        }
        registerProcessor('pcm-processor', PCMProcessor);
      `;
      const blob = new Blob([workletCode], { type: 'application/javascript' });
      const workletUrl = URL.createObjectURL(blob);
      
      await audioContext.audioWorklet.addModule(workletUrl);
      const processorNode = new AudioWorkletNode(audioContext, 'pcm-processor');
      processorNode.port.onmessage = (event) => {
        onAudioFrame?.(event.data);
      };
      
      source.connect(processorNode);
      processorNode.connect(audioContext.destination);
      
      processorRef.current = processorNode;
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
  
  return { isCapturing, error, diagnostic, startCapture, stopCapture };
}
