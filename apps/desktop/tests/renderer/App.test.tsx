import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { App } from '../../src/renderer/App';
import '@testing-library/jest-dom';

// Mock supabase so auth.getSession returns a valid session without a real network call
jest.mock('../../src/renderer/lib/supabase', () => ({
  supabase: {
    auth: {
      getSession: jest.fn().mockResolvedValue({ data: { session: { access_token: 'test-token' } } }),
      onAuthStateChange: jest.fn().mockReturnValue({ data: { subscription: { unsubscribe: jest.fn() } } }),
      signInWithPassword: jest.fn(),
      signOut: jest.fn().mockResolvedValue({}),
    },
  },
}));

// Mock child components
jest.mock('../../src/renderer/pages/PracticeArenaPage', () => ({
  PracticeArenaPage: () => <div data-testid="practice-page">Practice Arena</div>
}));
jest.mock('../../src/renderer/pages/StudyWorkbench', () => ({
  StudyWorkbench: () => <div data-testid="study-page">Study Workbench</div>
}));

describe('App Routing', () => {
  beforeAll(() => {
    (window as any).electronAPI = {
      storageGet: jest.fn().mockResolvedValue('mock-token'),
      storageSet: jest.fn().mockResolvedValue(true),
      authLogout: jest.fn().mockResolvedValue(true)
    };
  });

  it('navigates through screen states', async () => {
    render(<App />);
    
    // Default is loading, then dashboard
    await waitFor(() => {
      expect(screen.getByText('Desktop Dashboard')).toBeInTheDocument();
    });
    
    // Click Practice
    fireEvent.click(screen.getByText('Practice Arena'));
    expect(screen.getByTestId('practice-page')).toBeInTheDocument();
    
    // Click Study
    fireEvent.click(screen.getByText('Study Workbench'));
    expect(screen.getByTestId('study-page')).toBeInTheDocument();
  });
});
