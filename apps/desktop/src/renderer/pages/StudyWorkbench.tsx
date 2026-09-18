import React, { useState } from 'react';
import { useScreenCapture } from '../hooks/useScreenCapture';
import { useScreenshotUpload } from '../hooks/useScreenshotUpload';
import { DiagramCanvas } from '../components/DiagramCanvas';
import { HintCard, Button } from '@praxis/ui';

export function StudyWorkbench() {
  const { captureStarted, startCapture, stopCapture, captureFrame } = useScreenCapture();
  const { uploading, result, uploadScreenshot } = useScreenshotUpload();
  const [screenshot, setScreenshot] = useState<string | null>(null);
  const [showDiagramTool, setShowDiagramTool] = useState(false);
  
  const handleCapture = () => {
    const frame = captureFrame();
    if (frame) {
      setScreenshot(frame);
      uploadScreenshot(frame);
    }
  };
  
  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6 text-white">
      <h1 className="text-3xl font-bold">Study Workbench</h1>
      
      <div className="space-y-2">
        <h2 className="text-xl font-semibold">Problem Types</h2>
        <div className="flex gap-2">
          {!captureStarted ? (
            <Button onClick={startCapture}>Start Capture Stream</Button>
          ) : (
            <>
              <Button onClick={handleCapture} disabled={uploading}>
                {uploading ? 'Analyzing...' : 'Capture Frame & Analyze'}
              </Button>
              <Button onClick={stopCapture} variant="danger">Stop Stream</Button>
            </>
          )}
          <Button onClick={() => setShowDiagramTool(!showDiagramTool)}>
            {showDiagramTool ? 'Hide Diagram' : 'Sketch Diagram'}
          </Button>
        </div>
      </div>
      
      {showDiagramTool && <DiagramCanvas />}
      
      {screenshot && (
        <div className="space-y-2">
          <h3 className="text-lg font-semibold">Preview</h3>
          <img src={screenshot} alt="Captured" className="max-w-full border border-gray-700 rounded" />
        </div>
      )}
      
      {result && (
        <div className="space-y-4">
          <h3 className="text-lg font-semibold">Hint Ladder</h3>
          {result.level_1 && <HintCard hint={result.level_1} level={1} />}
          {result.level_2 && <HintCard hint={result.level_2} level={2} />}
          {result.level_3 && <HintCard hint={result.level_3} level={3} />}
        </div>
      )}
    </div>
  );
}
