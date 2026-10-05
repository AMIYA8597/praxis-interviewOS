import React, { useState, useEffect } from 'react';
import { PracticeArenaPage } from './pages/PracticeArenaPage';
import { StudyWorkbench } from './pages/StudyWorkbench';
import { supabase } from './lib/supabase';

type ScreenState = 
  | { screen: 'loading' }
  | { screen: 'auth' }
  | { screen: 'dashboard' }
  | { screen: 'practice' }
  | { screen: 'study-workbench' };

export function App() {
  const [state, setState] = useState<ScreenState>({ screen: 'loading' });

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [authError, setAuthError] = useState('');

  useEffect(() => {
    // Check auth token via Supabase client
    const initAuth = async () => {
      try {
        const { data: { session } } = await supabase.auth.getSession();
        if (session) {
          setState({ screen: 'dashboard' });
        } else {
          setState({ screen: 'auth' });
        }
      } catch (e) {
        setState({ screen: 'auth' });
      }
    };
    initAuth();
  }, []);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthError('');
    const supabaseUrl = typeof process !== 'undefined' && process.env.VITE_SUPABASE_URL ? process.env.VITE_SUPABASE_URL : undefined;
    if (!supabaseUrl || supabaseUrl === 'missing') {
      setAuthError('Supabase is not configured. Authentication unavailable.');
      return;
    }
    const { data, error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) {
      setAuthError(error.message);
    } else if (data.session) {
      setState({ screen: 'dashboard' });
    }
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
          <form onSubmit={handleLogin} className="flex flex-col gap-4 w-full">
            <input 
              type="email" 
              placeholder="Email" 
              className="p-2 bg-neutral-800 border border-neutral-700 rounded text-white" 
              value={email} 
              onChange={(e) => setEmail(e.target.value)} 
              required 
            />
            <input 
              type="password" 
              placeholder="Password" 
              className="p-2 bg-neutral-800 border border-neutral-700 rounded text-white" 
              value={password} 
              onChange={(e) => setPassword(e.target.value)} 
              required 
            />
            <button 
              type="submit"
              className="bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-2 px-6 rounded transition"
            >
              Sign In
            </button>
          </form>
          {authError && <p className="mt-4 text-sm text-red-500">{authError}</p>}
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
            onClick={() => setState({ screen: 'practice' })}
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
              await supabase.auth.signOut();
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
