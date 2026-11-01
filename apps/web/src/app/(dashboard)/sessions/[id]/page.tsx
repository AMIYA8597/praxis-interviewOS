"use client";

import React, { useEffect, useState, useRef, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { getSession, endSession } from '@/lib/api/sessions';
import type { SessionResponse } from '@/lib/api/types';
import { supabase } from '@/lib/supabase';
import { AudioControl, type AudioDeviceOption } from '@praxis/ui';
import type { SessionMetrics, RealtimeServerEventType } from '@praxis/types';

export default function LiveSessionRoomPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const sessionId = params.id;

  // Session state
  const [session, setSession] = useState<SessionResponse | null>(null);
  const [sessionState, setSessionState] = useState<string>('CONNECTING');
  const [currentQuestion, setCurrentQuestion] = useState<string>(
    'Connecting to PRAXIS intelligence engine...'
  );
  const [partialTranscript, setPartialTranscript] = useState<string>('');
  const [transcriptHistory, setTranscriptHistory] = useState<
    Array<{ speaker: 'interviewer' | 'candidate'; text: string; time: string }>
  >([]);
  const [metrics, setMetrics] = useState<SessionMetrics>({
    wpm: 0,
    filler_rate: 0,
    duration_s: 0,
    measurement_status: 'MEASURED',
  });
  const [textAnswer, setTextAnswer] = useState<string>('');
  const [isSubmittingText, setIsSubmittingText] = useState(false);
  const [ending, setEnding] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Audio state
  const [devices, setDevices] = useState<AudioDeviceOption[]>([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState<string>('');
  const [isStreamingAudio, setIsStreamingAudio] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [audioLevel, setAudioLevel] = useState<number>(0);
  const [audioError, setAudioError] = useState<string | null>(null);

  // Refs for Web Audio & WebSocket
  const wsRef = useRef<WebSocket | null>(null);
  const seqRef = useRef<number>(0);
  const audioContextRef = useRef<AudioContext | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const animFrameRef = useRef<number | null>(null);

  // 1. Fetch Session Metadata
  useEffect(() => {
    if (!sessionId) return;
    getSession(sessionId)
      .then((s) => {
        setSession(s);
        if (s.status === 'completed') {
          router.replace(`/sessions/${sessionId}/debrief`);
        }
      })
      .catch((err) => {
        setError(`Failed to load session details: ${err.message || String(err)}`);
      });
  }, [sessionId, router]);

  // 2. Enumerate Audio Devices
  const enumerateAudioDevices = useCallback(async () => {
    if (typeof navigator === 'undefined' || !navigator.mediaDevices?.enumerateDevices) return;
    try {
      const devList = await navigator.mediaDevices.enumerateDevices();
      const audioInputs = devList
        .filter((d) => d.kind === 'audioinput')
        .map((d, index) => ({
          deviceId: d.deviceId,
          label: d.label || `Microphone ${index + 1}`,
        }));
      setDevices(audioInputs);
      if (audioInputs.length > 0 && !selectedDeviceId) {
        setSelectedDeviceId(audioInputs[0].deviceId);
      }
    } catch (err: any) {
      console.warn('Microphone enumeration notice:', err);
    }
  }, [selectedDeviceId]);

  // 3. Float32 to PCM16 converter
  const float32ToPCM16 = useCallback((float32Array: Float32Array): Int16Array => {
    const pcm16 = new Int16Array(float32Array.length);
    for (let i = 0; i < float32Array.length; i++) {
      const sample = Math.max(-1, Math.min(1, float32Array[i]));
      pcm16[i] = sample < 0 ? sample * 0x8000 : sample * 0x7fff;
    }
    return pcm16;
  }, []);

  // 4. Send Binary Audio Frame (>BBIdI header + PCM16)
  const sendBinaryAudioFrame = useCallback(
    (pcm16: Int16Array) => {
      const ws = wsRef.current;
      if (!ws || ws.readyState !== WebSocket.OPEN || isMuted) return;

      const headerLen = 18;
      const totalLen = headerLen + pcm16.byteLength;
      const buffer = new ArrayBuffer(totalLen);
      const view = new DataView(buffer);

      // proto_ver=1, frame_type=1 (AUDIO_FRAME)
      view.setUint8(0, 1);
      view.setUint8(1, 1);
      // client_seq (uint32 big-endian)
      view.setUint32(2, seqRef.current++, false);
      // capture_ts (float64 big-endian)
      view.setFloat64(6, Date.now() / 1000, false);
      // payload_len (uint32 big-endian)
      view.setUint32(14, pcm16.byteLength, false);

      // Copy PCM16 bytes
      new Uint8Array(buffer, 18).set(new Uint8Array(pcm16.buffer));

      ws.send(buffer);
    },
    [isMuted]
  );

  // 5. Start Audio Capture Pipeline
  const startAudioCapture = useCallback(async () => {
    try {
      setAudioError(null);
      const constraints: MediaStreamConstraints = {
        audio: selectedDeviceId
          ? { deviceId: { exact: selectedDeviceId }, sampleRate: 16000, channelCount: 1, echoCancellation: true }
          : { sampleRate: 16000, channelCount: 1, echoCancellation: true },
        video: false,
      };

      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      mediaStreamRef.current = stream;

      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      const ctx = new AudioCtx({ sampleRate: 16000 });
      audioContextRef.current = ctx;

      const source = ctx.createMediaStreamSource(stream);
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 256;
      analyserRef.current = analyser;
      source.connect(analyser);

      // ScriptProcessorNode for 16kHz PCM streaming
      const processor = ctx.createScriptProcessor(4096, 1, 1);
      processorRef.current = processor;
      source.connect(processor);
      processor.connect(ctx.destination);

      processor.onaudioprocess = (e) => {
        const inputData = e.inputBuffer.getChannelData(0);
        const pcm16 = float32ToPCM16(inputData);
        sendBinaryAudioFrame(pcm16);
      };

      // Animate level meter
      const dataArray = new Uint8Array(analyser.frequencyBinCount);
      const updateLevel = () => {
        if (!analyserRef.current) return;
        analyserRef.current.getByteFrequencyData(dataArray);
        let sum = 0;
        for (let i = 0; i < dataArray.length; i++) {
          sum += dataArray[i];
        }
        const avg = sum / dataArray.length;
        setAudioLevel(avg / 128); // 0.0 to 1.0 approx
        animFrameRef.current = requestAnimationFrame(updateLevel);
      };
      updateLevel();

      setIsStreamingAudio(true);
      await enumerateAudioDevices();
    } catch (err: any) {
      console.error('Audio capture error:', err);
      setAudioError(err.message || 'Microphone access denied or audio device error.');
      setIsStreamingAudio(false);
    }
  }, [selectedDeviceId, float32ToPCM16, sendBinaryAudioFrame, enumerateAudioDevices]);

  // Stop Audio Capture
  const stopAudioCapture = useCallback(() => {
    if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    if (processorRef.current) processorRef.current.disconnect();
    if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
      audioContextRef.current.close().catch(() => {});
    }
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((t) => t.stop());
    }
    setIsStreamingAudio(false);
    setAudioLevel(0);
  }, []);

  // 6. Realtime WebSocket Lifecycle
  useEffect(() => {
    if (!sessionId) return;
    let cancelled = false;

    const connectWS = async () => {
      try {
        const {
          data: { session: authSession },
        } = await supabase.auth.getSession();
        if (cancelled) return;

        const token = authSession?.access_token || '';
        const wsUrl =
          process.env.NEXT_PUBLIC_REALTIME_URL ||
          (typeof window !== 'undefined'
            ? `ws://${window.location.hostname}:8001`
            : 'ws://localhost:8001');

        const ws = new WebSocket(`${wsUrl}/ws/sessions/${sessionId}?token=${token}`);
        ws.binaryType = 'arraybuffer';
        wsRef.current = ws;

        ws.onopen = () => {
          if (cancelled) return;
          setSessionState('READY');
          // Start microphone capture once WebSocket is established
          startAudioCapture();
        };

        ws.onmessage = (event) => {
          if (cancelled) return;
          try {
            if (typeof event.data !== 'string') return;
            const msg = JSON.parse(event.data);
            const type = msg.type as RealtimeServerEventType;
            const payload = msg.payload || {};

            switch (type) {
              case 'interviewer.text':
                if (payload.text) {
                  setCurrentQuestion(payload.text);
                  setTranscriptHistory((prev) => [
                    ...prev,
                    {
                      speaker: 'interviewer',
                      text: payload.text,
                      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
                    },
                  ]);
                }
                break;

              case 'transcript.partial':
                if (payload.text) {
                  setPartialTranscript(payload.text);
                }
                break;

              case 'transcript.final':
                if (payload.text) {
                  setPartialTranscript('');
                  setTranscriptHistory((prev) => [
                    ...prev,
                    {
                      speaker: 'candidate',
                      text: payload.text,
                      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
                    },
                  ]);
                }
                break;

              case 'coaching.metrics':
                setMetrics({
                  wpm: payload.wpm ?? 0,
                  filler_rate: payload.filler_rate ?? 0,
                  duration_s: payload.duration_s ?? 0,
                  measurement_status: payload.measurement_status ?? 'MEASURED',
                });
                break;

              case 'state.transitioned':
                if (payload.to) {
                  setSessionState(payload.to);
                }
                break;

              default:
                break;
            }
          } catch (e) {
            console.warn('Realtime parse notice:', e);
          }
        };

        ws.onerror = (e) => {
          if (cancelled) return;
          console.error('WebSocket connection error:', e);
          setSessionState('DEGRADED');
        };

        ws.onclose = () => {
          if (cancelled) return;
          setSessionState('DISCONNECTED');
        };
      } catch (err: any) {
        if (!cancelled) setError(err.message || 'Failed to initialize real-time connection');
      }
    };

    connectWS();

    return () => {
      cancelled = true;
      stopAudioCapture();
      if (wsRef.current) {
        wsRef.current.close(1000, 'session_navigation');
      }
    };
  }, [sessionId, startAudioCapture, stopAudioCapture]);

  // Send Text Answer (Degraded/Text mode fallback)
  const handleSendTextAnswer = () => {
    if (!textAnswer.trim() || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    setIsSubmittingText(true);
    const msg = {
      type: 'candidate.text_answer',
      session_id: sessionId,
      sequence: seqRef.current++,
      payload: { text: textAnswer.trim() },
    };
    wsRef.current.send(JSON.stringify(msg));
    setTranscriptHistory((prev) => [
      ...prev,
      {
        speaker: 'candidate',
        text: textAnswer.trim(),
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      },
    ]);
    setTextAnswer('');
    setIsSubmittingText(false);
  };

  // Finalize / End Session
  const handleEndSession = async () => {
    if (!sessionId || ending) return;
    setEnding(true);
    try {
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(
          JSON.stringify({
            type: 'session.complete',
            session_id: sessionId,
            sequence: seqRef.current++,
            payload: {},
          })
        );
      }
      stopAudioCapture();
      await endSession(sessionId);
      router.push(`/sessions/${sessionId}/debrief`);
    } catch (err: any) {
      setError(`Failed to conclude session: ${err.message || String(err)}`);
      setEnding(false);
    }
  };

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 p-4 sm:p-6 lg:p-8 flex flex-col gap-6 max-w-7xl mx-auto">
      {/* Header bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-zinc-800 gap-4">
        <div>
          <div className="flex items-center gap-3">
            <Link
              href="/sessions"
              className="text-xs text-zinc-400 hover:text-zinc-200 transition-colors"
            >
              ← Back to Sessions
            </Link>
            <span className="text-zinc-700">|</span>
            <span className="text-xs uppercase font-mono tracking-widest text-zinc-400">
              ID: {sessionId.slice(0, 8)}...
            </span>
          </div>
          <h1 className="text-2xl font-bold mt-1 text-white">
            Live Practice Interview Arena
          </h1>
          {session?.interview_type && (
            <p className="text-xs text-zinc-400 capitalize">
              Role Focus: {session.interview_type.replace('_', ' ')} • Difficulty:{' '}
              {session.difficulty || 'standard'}
            </p>
          )}
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 bg-zinc-900 border border-zinc-800 px-3 py-1.5 rounded-full text-xs">
            <span
              className={`w-2 h-2 rounded-full ${
                sessionState === 'READY' || sessionState === 'CANDIDATE_TURN'
                  ? 'bg-emerald-500 animate-pulse'
                  : sessionState === 'CONNECTING'
                  ? 'bg-amber-400'
                  : 'bg-zinc-600'
              }`}
            />
            <span className="font-mono text-zinc-300">{sessionState}</span>
          </div>

          <button
            type="button"
            onClick={handleEndSession}
            disabled={ending}
            className="px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white rounded-md text-xs font-semibold shadow-sm transition-colors disabled:opacity-50"
          >
            {ending ? 'Finalizing...' : 'Conclude Session →'}
          </button>
        </div>
      </div>

      {error && (
        <div className="p-3 bg-rose-950/40 border border-rose-800 text-rose-300 text-xs rounded">
          {error}
        </div>
      )}

      {/* Main Grid: Left Interviewer & Speech Area, Right Coaching HUD & Audio Controls */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 flex-1">
        {/* Left Column: 2/3 width */}
        <div className="lg:col-span-2 flex flex-col gap-5">
          {/* Active Interviewer Question Card */}
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6 shadow-sm">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-bold uppercase tracking-wider text-blue-400 flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-blue-500 inline-block" />
                Interviewer Question
              </span>
              <span className="text-[11px] text-zinc-500 font-mono">Real-Time Synthesis</span>
            </div>
            <p className="text-lg sm:text-xl font-medium text-zinc-100 leading-relaxed">
              "{currentQuestion}"
            </p>
          </div>

          {/* Live Transcript / Candidate Turn Card */}
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5 flex-1 flex flex-col min-h-[300px]">
            <div className="flex items-center justify-between pb-3 border-b border-zinc-800/80 mb-3">
              <span className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
                Conversation Transcript
              </span>
              {partialTranscript && (
                <span className="text-xs font-mono text-amber-400 animate-pulse">
                  ● Capturing speech...
                </span>
              )}
            </div>

            {/* Scrollable Dialogue List */}
            <div className="flex-1 overflow-y-auto space-y-3.5 pr-2 max-h-[360px]">
              {transcriptHistory.length === 0 && !partialTranscript && (
                <p className="text-xs text-zinc-500 italic py-8 text-center">
                  Start speaking into your microphone. Faster-whisper will stream speech hypotheses live.
                </p>
              )}

              {transcriptHistory.map((item, idx) => (
                <div
                  key={idx}
                  className={`p-3 rounded-lg text-xs leading-relaxed ${
                    item.speaker === 'interviewer'
                      ? 'bg-blue-950/20 border border-blue-900/40 text-blue-200'
                      : 'bg-zinc-800/60 border border-zinc-700/50 text-zinc-200 ml-4'
                  }`}
                >
                  <div className="flex justify-between items-center mb-1 text-[10px] text-zinc-500 uppercase font-semibold">
                    <span>{item.speaker === 'interviewer' ? 'Interviewer' : 'You (Candidate)'}</span>
                    <span className="font-mono">{item.time}</span>
                  </div>
                  <p>{item.text}</p>
                </div>
              ))}

              {/* Streaming Partial Hypothesis */}
              {partialTranscript && (
                <div className="p-3 rounded-lg text-xs leading-relaxed bg-zinc-800/40 border border-amber-500/40 text-amber-200 ml-4 animate-pulse">
                  <div className="text-[10px] text-amber-400/80 uppercase font-semibold mb-1">
                    Live Speech (Interim)
                  </div>
                  <p className="italic">"{partialTranscript}"</p>
                </div>
              )}
            </div>

            {/* Degraded Text Mode Fallback */}
            <div className="mt-4 pt-3 border-t border-zinc-800/80">
              <label
                htmlFor="text-answer-input"
                className="block text-xs font-medium text-zinc-400 mb-1"
              >
                Text Answer (Degraded / Fallback Mode):
              </label>
              <div className="flex gap-2">
                <input
                  id="text-answer-input"
                  type="text"
                  value={textAnswer}
                  onChange={(e) => setTextAnswer(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') handleSendTextAnswer();
                  }}
                  placeholder="Type your response if microphone is unavailable..."
                  className="flex-1 bg-zinc-950 border border-zinc-700 rounded-md px-3 py-1.5 text-xs text-zinc-200 placeholder-zinc-600 focus:outline-none focus:border-blue-500"
                />
                <button
                  type="button"
                  onClick={handleSendTextAnswer}
                  disabled={isSubmittingText || !textAnswer.trim()}
                  className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-40 text-white rounded-md text-xs font-semibold"
                >
                  Submit
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: 1/3 width (Audio Controls & Real-Time Coaching Metrics) */}
        <div className="flex flex-col gap-5">
          {/* Audio Setup Component */}
          <AudioControl
            devices={devices}
            selectedDeviceId={selectedDeviceId}
            onDeviceChange={(devId) => {
              setSelectedDeviceId(devId);
              stopAudioCapture();
              setTimeout(() => startAudioCapture(), 200);
            }}
            isStreaming={isStreamingAudio}
            isMuted={isMuted}
            onToggleMute={() => setIsMuted(!isMuted)}
            audioLevel={audioLevel}
            error={audioError}
            onRetryPermission={startAudioCapture}
          />

          {/* Fast-Path Coaching HUD (~1Hz feedback) */}
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5 shadow-sm space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-zinc-800">
              <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-300">
                Live Speech Intelligence
              </h3>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-zinc-800 text-zinc-400">
                1Hz Fast Path
              </span>
            </div>

            {/* Speaking Pace (WPM) */}
            <div>
              <div className="flex justify-between items-baseline mb-1">
                <span className="text-xs text-zinc-400">Speaking Pace:</span>
                <span className="text-lg font-mono font-bold text-white">
                  {metrics.wpm != null ? Math.round(metrics.wpm) : 0}{' '}
                  <span className="text-xs font-normal text-zinc-500">WPM</span>
                </span>
              </div>
              <div className="text-[11px] text-zinc-500 flex justify-between">
                <span>Target: 130–160 WPM</span>
                <span
                  className={
                    (metrics.wpm ?? 0) >= 120 && (metrics.wpm ?? 0) <= 170
                      ? 'text-emerald-400 font-medium'
                      : 'text-amber-400'
                  }
                >
                  {(metrics.wpm ?? 0) >= 120 && (metrics.wpm ?? 0) <= 170
                    ? 'Optimal'
                    : (metrics.wpm ?? 0) < 120
                    ? 'Slow'
                    : 'Fast'}
                </span>
              </div>
            </div>

            {/* Filler Word Rate */}
            <div className="pt-2 border-t border-zinc-800/60">
              <div className="flex justify-between items-baseline mb-1">
                <span className="text-xs text-zinc-400">Filler Words:</span>
                <span className="text-lg font-mono font-bold text-white">
                  {metrics.filler_rate != null ? (metrics.filler_rate * 100).toFixed(1) : '0.0'}%
                </span>
              </div>
              <div className="w-full bg-zinc-800 h-1.5 rounded-full overflow-hidden">
                <div
                  className={`h-full ${
                    (metrics.filler_rate ?? 0) < 0.04 ? 'bg-emerald-500' : 'bg-amber-500'
                  }`}
                  style={{
                    width: `${Math.min(100, (metrics.filler_rate ?? 0) * 1000)}%`,
                  }}
                />
              </div>
            </div>

            {/* Turn Duration */}
            <div className="pt-2 border-t border-zinc-800/60 flex justify-between items-baseline">
              <span className="text-xs text-zinc-400">Active Turn Time:</span>
              <span className="text-sm font-mono text-zinc-300">
                {metrics.duration_s != null ? `${Math.round(metrics.duration_s)}s` : '0s'}
              </span>
            </div>

            {/* Measurement Status */}
            <div className="pt-2 border-t border-zinc-800/60 flex justify-between items-center">
              <span className="text-[11px] text-zinc-500">Signal Status:</span>
              <span className="text-[10px] font-semibold uppercase px-2 py-0.5 rounded bg-zinc-800 text-zinc-400 border border-zinc-700">
                {metrics.measurement_status || 'MEASURED'}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
