import React, { useState, useEffect } from 'react';
import { PracticeArenaPage } from './pages/PracticeArenaPage';
import { StudyWorkbench } from './pages/StudyWorkbench';

type ScreenState = 
  | { screen: 'loading' }
  | { screen: 'auth' }
  | { screen: 'dashboard' }
  | { screen: 'practice'; sessionId: string }
  | { screen: 'study-workbench' };

export function App() {
  const [state, setState] = useState<ScreenState>({ screen: 'loading' });

  useEffect(() => {
    // Check auth token via IPC storage
    const initAuth = async () => {
      try {
        const token = await window.electronAPI.storageGet('auth-token');
        if (token) {
          setState({ screen: 'dashboard' });
        } else {
          // Default to dashboard for now if mock mode, or auth if strictly required. 
          // Let's assume we require auth, but we can bypass it in UI.
          setState({ screen: 'auth' });
        }
      } catch (e) {
        setState({ screen: 'auth' });
      }
    };
    initAuth();
  }, []);

  const handleLogin = async () => {
    // Mock login for desktop
    await window.electronAPI.storageSet('auth-token', 'mock-token');
    setState({ screen: 'dashboard' });
  };

  if (state.screen === 'loading') {
    return (
      <div className="flex h-screen items-center justify-center bg-gray-950 text-gray-400">
        <p className="tracking-widest uppercase text-sm font-bold">Loading...</p>
      </div>
    );
  }

  if (state.screen === 'auth') {
    return (
      <div className="flex h-screen items-center justify-center bg-gray-950 text-gray-100">
        <div className="bg-gray-900 p-8 rounded border border-gray-800 flex flex-col items-center">
          <h1 className="text-2xl font-bold mb-6 tracking-widest uppercase">PRAXIS DESKTOP</h1>
          <button 
            onClick={handleLogin}
            className="bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-2 px-6 rounded transition"
          >
            Sign In
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-gray-950 text-gray-100 font-sans selection:bg-indigo-500/30">
      <aside className="w-64 bg-gray-900/50 border-r border-gray-800 flex flex-col">
        <div 
          className="p-6 font-bold text-lg tracking-widest uppercase border-b border-gray-800 cursor-pointer" 
          onClick={() => setState({ screen: 'dashboard' })}
        >
          PRAXIS
        </div>
        <nav className="flex-1 p-4 space-y-2">
          <button 
            className={`w-full text-left px-3 py-2 rounded text-sm font-medium transition-colors ${state.screen === 'practice' ? 'bg-indigo-900/50 text-white' : 'text-gray-400 hover:bg-gray-800 hover:text-gray-200'}`}
            onClick={() => setState({ screen: 'practice', sessionId: 'mock-session-id' })}
          >
            Practice Arena
          </button>
          <button 
            className={`w-full text-left px-3 py-2 rounded text-sm font-medium transition-colors ${state.screen === 'study-workbench' ? 'bg-indigo-900/50 text-white' : 'text-gray-400 hover:bg-gray-800 hover:text-gray-200'}`}
            onClick={() => setState({ screen: 'study-workbench' })}
          >
            Study Workbench
          </button>
        </nav>
        <div className="p-4 border-t border-gray-800">
          <button
            onClick={async () => {
              await window.electronAPI.authLogout();
              setState({ screen: 'auth' });
            }}
            className="w-full text-left px-3 py-2 rounded text-sm font-medium text-gray-400 hover:bg-gray-800 hover:text-white transition-colors"
          >
            Sign Out
          </button>
        </div>
      </aside>
      
      <main className="flex-1 overflow-y-auto">
        {state.screen === 'dashboard' && (
          <div className="flex h-full items-center justify-center flex-col text-center p-8">
            <h1 className="text-3xl font-bold mb-4 tracking-widest uppercase text-gray-300">Desktop Dashboard</h1>
            <p className="text-gray-500 max-w-md">Select Practice Arena to start a live session or Study Workbench to review screenshots and materials.</p>
          </div>
        )}
        {state.screen === 'practice' && <PracticeArenaPage />}
        {state.screen === 'study-workbench' && <StudyWorkbench />}
      </main>
    </div>
  );
}
