import { useState } from 'react';

export function useScreenshotUpload() {
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<any>(null);
  
  const uploadScreenshot = async (screenshotBase64: string) => {
    setUploading(true);
    try {
      const response = await fetch(
        `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/study-workbench/screenshots`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('auth-token')}`
          },
          body: JSON.stringify({
            image_base64: screenshotBase64,
            context: 'study'  // or 'session'
          })
        }
      );
      
      const data = await response.json();
      if (!response.ok) throw new Error(data.message);
      
      setResult(data);
    } catch (err) {
      console.error('Screenshot upload failed', err);
    } finally {
      setUploading(false);
    }
  };
  
  return { uploading, result, uploadScreenshot };
}
