import { renderHook, act, waitFor } from '@testing-library/react';
import { useRealtimeSession } from '../../src/renderer/hooks/useRealtimeSession';

// Mock supabase so auth.getSession resolves immediately without a network call
jest.mock('../../src/renderer/lib/supabase', () => ({
  supabase: {
    auth: {
      getSession: jest.fn().mockResolvedValue({ data: { session: { access_token: 'test-token' } } }),
    },
  },
}));

let mockWsInstance: any = null;

class MockWebSocket {
  onmessage: any;
  onopen: any;
  onerror: any;
  onclose: any;
  send = jest.fn();
  close = jest.fn();
  readyState = WebSocket.OPEN;

  constructor() {
    mockWsInstance = this;
  }
}

global.WebSocket = MockWebSocket as any;

describe('useRealtimeSession', () => {
  let addEventListenerSpy: jest.SpyInstance;

  beforeEach(() => {
    addEventListenerSpy = jest.spyOn(window, 'dispatchEvent');
    mockWsInstance = null;
  });

  afterEach(() => {
    addEventListenerSpy.mockRestore();
  });

  it('dispatches identical event names for coaching.metrics', async () => {
    renderHook(() => useRealtimeSession('test-session'));

    // initWS is async (awaits supabase.auth.getSession), so wait for WS creation
    await waitFor(() => expect(mockWsInstance).not.toBeNull());

    // Simulate incoming message
    act(() => {
      mockWsInstance.onmessage({
        data: JSON.stringify({ type: 'coaching.metrics', wpm: 150 })
      });
    });

    expect(addEventListenerSpy).toHaveBeenCalled();
    const event = addEventListenerSpy.mock.calls[0][0] as CustomEvent;
    expect(event.type).toBe('coaching.metrics');
    expect(event.detail.wpm).toBe(150);
  });

  it('dispatches identical event names for state.transitioned', async () => {
    renderHook(() => useRealtimeSession('test-session'));

    await waitFor(() => expect(mockWsInstance).not.toBeNull());

    act(() => {
      mockWsInstance.onmessage({
        data: JSON.stringify({ type: 'state.transitioned', to_state: 'SCORING' })
      });
    });

    const event = addEventListenerSpy.mock.calls[0][0] as CustomEvent;
    expect(event.type).toBe('state.transitioned');
    expect(event.detail.to_state).toBe('SCORING');
  });
});
