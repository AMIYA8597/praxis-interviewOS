import { useEffect, useState } from 'react';

export interface Screenshot {
  id: string;
  dataUrl: string;
  timestamp?: string;
  context?: string;
}

export function useScreenshotHistory() {
  const [history, setHistory] = useState<Screenshot[]>([]);
  
  const addScreenshot = (screenshot: Screenshot) => {
    const storedHistory = JSON.parse(
      localStorage.getItem('screenshot-history') || '[]'
    );
    storedHistory.push({
      ...screenshot,
      timestamp: new Date().toISOString()
    });
    localStorage.setItem('screenshot-history', JSON.stringify(storedHistory));
    setHistory(storedHistory);
  };
  
  const deleteScreenshot = (id: string) => {
    const updated = history.filter(s => s.id !== id);
    localStorage.setItem('screenshot-history', JSON.stringify(updated));
    setHistory(updated);
  };
  
  useEffect(() => {
    const stored = JSON.parse(
      localStorage.getItem('screenshot-history') || '[]'
    );
    setHistory(stored);
  }, []);
  
  return { history, addScreenshot, deleteScreenshot };
}
