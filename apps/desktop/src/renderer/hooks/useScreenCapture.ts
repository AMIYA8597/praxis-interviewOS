import { useState, useCallback } from 'react';

export function useScreenCapture() {
  const [captureStarted, setCaptureStarted] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [stream, setStream] = useState<MediaStream | null>(null);
  
  const startCapture = useCallback(async () => {
    try {
      const mediaStream = await navigator.mediaDevices.getDisplayMedia({
        video: { cursor: 'always' } as any,
        audio: false
      });
      setStream(mediaStream);
      setCaptureStarted(true);
    } catch (err) {
      setError((err as Error).message);
    }
  }, []);
  
  const stopCapture = useCallback(() => {
    stream?.getTracks().forEach(t => t.stop());
    setCaptureStarted(false);
  }, [stream]);
  
  const captureFrame = useCallback(() => {
    if (!stream) return null;
    
    const video = document.createElement('video');
    video.srcObject = stream;
    video.play();
    
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d')!;
    ctx.drawImage(video, 0, 0);
    
    return canvas.toDataURL('image/png');
  }, [stream]);
  
  return { captureStarted, error, startCapture, stopCapture, captureFrame };
}
