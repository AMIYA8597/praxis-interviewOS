import React, { useState, useEffect } from 'react';
import { useScreenshotUpload } from '../hooks/useScreenshotUpload';
import { DiagramCanvas } from '../components/DiagramCanvas';
import { HintCard, Button } from '@praxis/ui';

export function StudyWorkbench() {
  const { uploading, result, uploadScreenshot } = useScreenshotUpload();
  const [screenshot, setScreenshot] = useState<string | null>(null);
  const [showDiagramTool, setShowDiagramTool] = useState(false);
  
  useEffect(() => {
    if ((window as any).electronAPI) {
      (window as any).electronAPI.onScreenshotCaptureReady((dataUrl: string) => {
        setScreenshot(dataUrl);
        uploadScreenshot(dataUrl);
      });
    }
  }, [uploadScreenshot]);
  
  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6 text-white">
      <h1 className="text-3xl font-bold">Study Workbench</h1>
      
      <div className="space-y-2">
        <h2 className="text-xl font-semibold">Problem Types</h2>
        <div className="flex gap-2">
          <Button onClick={() => setShowDiagramTool(!showDiagramTool)}>
            {showDiagramTool ? 'Hide Diagram' : 'Sketch Diagram'}
          </Button>
          <div className="text-gray-400 self-center ml-4">
            Press Cmd/Ctrl + Shift + S to capture screen and analyze.
          </div>
        </div>
      </div>
      
      {showDiagramTool && <DiagramCanvas />}
      
      {screenshot && (
        <div className="space-y-2">
          <h3 className="text-lg font-semibold">Preview</h3>
          <img src={screenshot} alt="Captured" className="max-w-full border border-gray-700 rounded" />
          {uploading && <p className="text-blue-400">Analyzing...</p>}
        </div>
      )}
      
      {result && result.hints && !uploading && (
        <div className="space-y-4">
          <h3 className="text-lg font-semibold">Hint Ladder</h3>
          {result.hints.clarify && <HintCard hint={result.hints.clarify} level={1} />}
          {result.hints.approach && <HintCard hint={result.hints.approach} level={2} />}
          {result.hints.solution && <HintCard hint={result.hints.solution} level={3} />}
        </div>
      )}
    </div>
  );
}
