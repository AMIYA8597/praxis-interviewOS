import { renderHook, act } from '@testing-library/react';
import { useScreenCapture } from '../../src/renderer/hooks/useScreenCapture';

const mockGetDisplayMedia = jest.fn().mockResolvedValue({
  getTracks: () => [{ stop: jest.fn() }]
});

Object.defineProperty(global.navigator, 'mediaDevices', {
  value: { 
    ...global.navigator.mediaDevices,
    getDisplayMedia: mockGetDisplayMedia 
  },
  writable: true
});

describe('useScreenCapture', () => {
  it('starts screen capture', async () => {
    const { result } = renderHook(() => useScreenCapture());
    
    await act(async () => {
      await result.current.startCapture();
    });
    
    expect(result.current.captureStarted).toBe(true);
    expect(mockGetDisplayMedia).toHaveBeenCalledWith({
      video: { cursor: 'always' },
      audio: false
    });
  });
});
