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

const mockCreateScriptProcessor = jest.fn().mockReturnValue({
  connect: jest.fn(),
  disconnect: jest.fn()
});

const mockCreateMediaStreamSource = jest.fn().mockReturnValue({
  connect: jest.fn()
});

Object.defineProperty(window, 'AudioContext', {
  value: jest.fn().mockImplementation(() => ({
    createScriptProcessor: mockCreateScriptProcessor,
    createMediaStreamSource: mockCreateMediaStreamSource,
    destination: {},
    close: jest.fn()
  })),
  writable: true
});

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
