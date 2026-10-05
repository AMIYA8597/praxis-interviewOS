import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { PracticeArenaPage } from '../../src/renderer/pages/PracticeArenaPage';
import '@testing-library/jest-dom';

// Mock supabase to return a valid session
jest.mock('../../src/renderer/lib/supabase', () => ({
  supabase: {
    auth: {
      getSession: jest.fn().mockResolvedValue({ data: { session: { access_token: 'test-token' } } }),
    },
  },
}));

global.fetch = jest.fn(() =>
  Promise.resolve({
    ok: true,
    json: () => Promise.resolve({ session_id: 'real-session-123' })
  })
) as jest.Mock;

jest.mock('../../src/renderer/components/CoachingHUD', () => ({
  CoachingHUD: ({ sessionId }: { sessionId: string }) => <div data-testid="hud">HUD for {sessionId}</div>
}));

// PreflightCheck gates session creation; stub it to immediately call onReady
jest.mock('../../src/renderer/components/PreflightCheck', () => ({
  PreflightCheck: ({ onReady }: { onReady: (payload: string) => void }) => (
    <button data-testid="preflight-ready" onClick={() => onReady('{}')}>
      Ready
    </button>
  ),
}));

describe('PracticeArenaPage Integration', () => {
  it('creates a session and renders CoachingHUD', async () => {
    render(<PracticeArenaPage />);

    // First click opens PreflightCheck
    fireEvent.click(screen.getByText('Start Practice Interview'));

    // PreflightCheck stub is now visible; click its Ready button to call onReady
    await waitFor(() => expect(screen.getByTestId('preflight-ready')).toBeInTheDocument());
    fireEvent.click(screen.getByTestId('preflight-ready'));

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/sessions'),
        expect.any(Object)
      );
      expect(screen.getByTestId('hud')).toHaveTextContent('HUD for real-session-123');
    });
  });
});
