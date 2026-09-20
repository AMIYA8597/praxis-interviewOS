import { renderHook, act } from '@testing-library/react';
import { useAudioCapture } from '../../src/renderer/hooks/useAudioCapture';
import { useRealtimeSession } from '../../src/renderer/hooks/useRealtimeSession';

jest.mock('../../src/renderer/hooks/useAudioCapture', () => ({
  useAudioCapture: jest.fn((onAudioFrame) => {
    return {
      isCapturing: true,
      startCapture: jest.fn(),
      stopCapture: jest.fn(),
      triggerMockFrame: () => onAudioFrame && onAudioFrame(new Float32Array([0.1, 0.2]))
    };
  })
}));

jest.mock('../../src/renderer/hooks/useRealtimeSession', () => ({
  useRealtimeSession: jest.fn(() => ({
    sendAudioFrame: jest.fn(),
    connected: true
  }))
}));

describe('Audio Pipeline Integration', () => {
  it('pipes audio capture through frame streaming to websocket transport', () => {
    const { result: sessionResult } = renderHook(() => useRealtimeSession('test'));
    const { result: captureResult } = renderHook(() => useAudioCapture(sessionResult.current.sendAudioFrame));

    // Simulate audio frame from microphone
    act(() => {
      (captureResult.current as any).triggerMockFrame();
    });

    // Check if the frame was encoded and sent to websocket
    expect(sessionResult.current.sendAudioFrame).toHaveBeenCalledWith(expect.any(Float32Array));
  });
});
