"use client";

import { useEffect, useState, useRef } from "react";
import { Mic, MicOff, Activity } from "lucide-react";

export default function PracticeArena() {
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState<string>("");
  const [status, setStatus] = useState<string>("Disconnected");
  
  const wsRef = useRef<WebSocket | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);

  useEffect(() => {
    return () => {
      // Cleanup
      wsRef.current?.close();
      mediaStreamRef.current?.getTracks().forEach(t => t.stop());
    };
  }, []);

  const toggleListen = async () => {
    if (isListening) {
      // Stop
      setIsListening(false);
      setStatus("Disconnected");
      wsRef.current?.close();
      mediaStreamRef.current?.getTracks().forEach(t => t.stop());
      return;
    }

    try {
      // 1. Get Microphone
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;
      
      // 2. Connect WebSocket
      const wsUrl = "ws://localhost:8000/ws/interviews/session-12345";
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setStatus("Connected");
        setIsListening(true);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === "transcript.partial" || data.type === "transcript.final") {
            setTranscript(prev => prev + "\n" + data.payload.text);
          }
        } catch (e) {
            console.error("Failed to parse WS message", e);
        }
      };

      ws.onclose = () => {
        setStatus("Disconnected");
        setIsListening(false);
      };

      // 3. Audio Processor (Very simple raw PCM extraction for MVP, in real app use AudioWorklet)
      audioContextRef.current = new AudioContext();
      const source = audioContextRef.current.createMediaStreamSource(stream);
      const processor = audioContextRef.current.createScriptProcessor(4096, 1, 1);
      
      source.connect(processor);
      processor.connect(audioContextRef.current.destination);

      processor.onaudioprocess = (e) => {
        if (ws.readyState === WebSocket.OPEN) {
          const inputData = e.inputBuffer.getChannelData(0);
          // Convert Float32Array to Int16Array for basic transmission
          const int16Array = new Int16Array(inputData.length);
          for (let i = 0; i < inputData.length; i++) {
            let s = Math.max(-1, Math.min(1, inputData[i]));
            int16Array[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
          }
          ws.send(int16Array.buffer);
        }
      };
      
    } catch (err: any) {
      setStatus(`Error: ${err.message}`);
    }
  };

  return (
    <div className="flex flex-col h-screen bg-neutral-950 text-white font-mono">
      {/* Header */}
      <header className="flex items-center justify-between p-4 border-b border-neutral-800 bg-neutral-900">
        <div className="flex items-center gap-4">
          <h1 className="text-xl font-bold">Practice Arena</h1>
          <div className="flex items-center gap-2 text-sm px-3 py-1 bg-neutral-800 rounded">
            <div className={`w-2 h-2 rounded-full ${isListening ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`}></div>
            <span>{status}</span>
          </div>
        </div>
        <button 
          onClick={toggleListen}
          className={`flex items-center gap-2 px-4 py-2 rounded font-bold ${isListening ? 'bg-red-600 hover:bg-red-700' : 'bg-white text-black hover:bg-neutral-200'}`}
        >
          {isListening ? <MicOff size={18} /> : <Mic size={18} />}
          {isListening ? "Stop Interview" : "Start Live Interview"}
        </button>
      </header>

      {/* Main Grid */}
      <div className="flex-1 grid grid-cols-3 gap-4 p-4 min-h-0">
        
        {/* Left Column: AI Interviewer */}
        <div className="col-span-2 flex flex-col border border-neutral-800 rounded bg-neutral-900 overflow-hidden">
          <div className="p-3 border-b border-neutral-800 bg-neutral-950 text-neutral-400 text-xs font-bold uppercase tracking-wider flex justify-between">
            <span>Interviewer AI</span>
            <span className="flex items-center gap-1"><Activity size={12}/> VAD ACTIVE</span>
          </div>
          <div className="flex-1 p-6 flex flex-col justify-center items-center text-center">
             {isListening ? (
                <div className="text-2xl text-neutral-300 max-w-2xl">
                    "Tell me about a time you had to deal with a difficult technical tradeoff."
                </div>
             ) : (
                <div className="text-neutral-500">Waiting to start...</div>
             )}
          </div>
        </div>

        {/* Right Column: Live Transcript & Coaching HUD */}
        <div className="flex flex-col gap-4">
          {/* Transcript */}
          <div className="flex-1 border border-neutral-800 rounded bg-neutral-900 flex flex-col overflow-hidden">
             <div className="p-3 border-b border-neutral-800 bg-neutral-950 text-neutral-400 text-xs font-bold uppercase tracking-wider">
               Live Transcript
             </div>
             <div className="flex-1 p-4 overflow-y-auto whitespace-pre-wrap text-sm text-neutral-300">
                {transcript || (
                   <span className="text-neutral-600 italic">No audio detected...</span>
                )}
             </div>
          </div>

          {/* Coaching HUD */}
          <div className="h-48 border border-neutral-800 rounded bg-neutral-900 flex flex-col overflow-hidden">
             <div className="p-3 border-b border-neutral-800 bg-neutral-950 text-neutral-400 text-xs font-bold uppercase tracking-wider">
               Coaching HUD
             </div>
             <div className="flex-1 p-4 grid grid-cols-2 gap-4 text-sm">
                <div className="bg-neutral-950 p-2 rounded flex flex-col justify-center items-center">
                    <span className="text-neutral-500 text-xs">Pace</span>
                    <span className="text-xl font-bold">140 <span className="text-xs text-neutral-500 font-normal">WPM</span></span>
                </div>
                <div className="bg-neutral-950 p-2 rounded flex flex-col justify-center items-center">
                    <span className="text-neutral-500 text-xs">Fillers</span>
                    <span className="text-xl font-bold text-green-500">Low</span>
                </div>
             </div>
          </div>
        </div>

      </div>
    </div>
  );
}
