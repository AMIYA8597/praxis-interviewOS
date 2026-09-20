import { renderHook, act } from '@testing-library/react';
import { useAudioCapture } from '../../src/renderer/hooks/useAudioCapture';

// Mock Web Audio API and mediaDevices
const mockGetUserMedia = jest.fn().mockResolvedValue({
  getTracks: () => [{ stop: jest.fn() }]
});

Object.defineProperty(global.navigator, 'mediaDevices', {
  value: { getUserMedia: mockGetUserMedia },
  writable: true
});

const mockCreateMediaStreamSource = jest.fn().mockReturnValue({
  connect: jest.fn()
});

class MockAudioWorkletNode {
  port = { onmessage: null };
  connect = jest.fn();
  disconnect = jest.fn();
}

Object.defineProperty(window, 'AudioWorkletNode', {
  value: MockAudioWorkletNode,
  writable: true
});

Object.defineProperty(window, 'URL', {
  value: {
    createObjectURL: jest.fn().mockReturnValue('blob:mock-url')
  }
});

Object.defineProperty(window, 'AudioContext', {
  value: jest.fn().mockImplementation(() => ({
    createMediaStreamSource: mockCreateMediaStreamSource,
    audioWorklet: {
      addModule: jest.fn().mockResolvedValue(undefined)
    },
    destination: {},
    close: jest.fn()
  })),
  writable: true
});

(window as any).electronAPI = {
  audioGetSources: jest.fn().mockResolvedValue({ hasLoopback: true, sources: [] }),
  systemGetStatus: jest.fn().mockResolvedValue({ os: 'win32' })
};

describe('useAudioCapture', () => {
  it('starts audio capture and sets isCapturing=true', async () => {
    const { result } = renderHook(() => useAudioCapture());
    
    await act(async () => {
      await result.current.startCapture();
    });
    
    expect(result.current.isCapturing).toBe(true);
    expect(mockGetUserMedia).toHaveBeenCalled();
  });
});
