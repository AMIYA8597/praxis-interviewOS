import React, { useRef, useState } from 'react';
import { Button } from '@praxis/ui';

export function DiagramCanvas() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [isDrawing, setIsDrawing] = useState(false);
  
  const handleMouseDown = () => setIsDrawing(true);
  const handleMouseUp = () => setIsDrawing(false);
  
  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDrawing || !canvasRef.current) return;
    
    const ctx = canvasRef.current.getContext('2d')!;
    const rect = canvasRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    
    ctx.lineTo(x, y);
    ctx.stroke();
  };
  
  const handleClear = () => {
    const ctx = canvasRef.current?.getContext('2d');
    if (ctx && canvasRef.current) {
      ctx.clearRect(0, 0, canvasRef.current.width, canvasRef.current.height);
      ctx.beginPath(); // reset path
    }
  };
  
  const handleSave = () => {
    const dataUrl = canvasRef.current?.toDataURL('image/png');
    // Send to backend for OCR/analysis
    console.log('Saved data url', dataUrl?.substring(0, 50));
  };
  
  return (
    <div className="flex flex-col gap-2">
      <canvas
        ref={canvasRef}
        width={600}
        height={400}
        onMouseDown={handleMouseDown}
        onMouseUp={handleMouseUp}
        onMouseMove={handleMouseMove}
        className="border border-gray-600 bg-gray-900 cursor-crosshair"
      />
      <div className="flex gap-2">
        <Button onClick={handleClear}>Clear</Button>
        <Button onClick={handleSave} variant="primary">Save & Analyze</Button>
      </div>
    </div>
  );
}
