import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { PracticeArenaPage } from '../../src/renderer/pages/PracticeArenaPage';
import '@testing-library/jest-dom';

global.fetch = jest.fn(() =>
  Promise.resolve({
    ok: true,
    json: () => Promise.resolve({ session_id: 'real-session-123' })
  })
) as jest.Mock;

jest.mock('../../src/renderer/components/CoachingHUD', () => ({
  CoachingHUD: ({ sessionId }: { sessionId: string }) => <div data-testid="hud">HUD for {sessionId}</div>
}));

describe('PracticeArenaPage Integration', () => {
  it('creates a session and renders CoachingHUD', async () => {
    render(<PracticeArenaPage />);
    
    fireEvent.click(screen.getByText('Start Practice Interview'));
    
    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(expect.stringContaining('/api/v1/sessions'), expect.any(Object));
      expect(screen.getByTestId('hud')).toHaveTextContent('HUD for real-session-123');
    });
  });
});
