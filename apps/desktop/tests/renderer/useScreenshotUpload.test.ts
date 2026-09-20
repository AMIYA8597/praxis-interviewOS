import React from 'react';
import { renderHook, act } from '@testing-library/react';
import { useScreenshotUpload } from '../../src/renderer/hooks/useScreenshotUpload';

global.fetch = jest.fn(() =>
  Promise.resolve({
    ok: true,
    json: () => Promise.resolve({ level_1: 'Hint 1' })
  })
) as jest.Mock;

describe('useScreenshotUpload Integration', () => {
  it('uploads screenshot to the correct endpoint', async () => {
    const { result } = renderHook(() => useScreenshotUpload());
    
    await act(async () => {
      await result.current.uploadScreenshot('data:image/png;base64,mock');
    });
    
    expect(global.fetch).toHaveBeenCalledWith(expect.stringContaining('/api/v1/study/screenshots/solve'), expect.any(Object));
    expect(result.current.result.level_1).toBe('Hint 1');
  });
});
