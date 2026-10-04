import { useState, useCallback } from 'react';
import { supabase } from '../lib/supabase';

export type CaptureState = 'SCREEN_CAPTURE_OFF' | 'SCREEN_CAPTURE_READY' | 'CAPTURING' | 'UPLOAD_PENDING' | 'UPLOADED' | 'FAILED';

export function useScreenshotUpload() {
  const [captureState, setCaptureState] = useState<CaptureState>('SCREEN_CAPTURE_OFF');
  const [result, setResult] = useState<any>(null);
  
  const uploadScreenshot = useCallback(async (screenshotBase64: string) => {
    setCaptureState('UPLOAD_PENDING');
    try {
      const { data: { session } } = await supabase.auth.getSession();
      const token = session?.access_token || '';
      
      const response = await fetch(
        `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/v1/study/screenshots/solve`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({
            image_base64: screenshotBase64,
            screenshot_task_id: "manual-capture-" + Date.now()
          })
        }
      );
      
      const data = await response.json();
      if (!response.ok) throw new Error(data.message || 'Error from server');
      
      setResult(data);
      setCaptureState('UPLOADED');
    } catch (err) {
      console.error('Screenshot upload failed', err);
      setCaptureState('FAILED');
    }
  }, []);
  
  return { captureState, setCaptureState, result, uploadScreenshot };
}
