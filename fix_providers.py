import os

with open('apps/web/src/app/(dashboard)/settings/providers/page.tsx', 'w', encoding='utf-8') as f:
    f.write('''"use client";

import React, { useState } from 'react';

export default function ProvidersSettingsPage() {
  const [costMode, setCostMode] = useState('FREE-FIRST');

  return (
    <div className="p-8 max-w-4xl mx-auto space-y-8">
      <div className="flex justify-between items-end border-b border-gray-800 pb-4">
        <div>
          <h1 className="text-3xl font-bold">AI Providers</h1>
          <p className="text-gray-300">Manage keys, routing logic, and cost guardrails.</p>
        </div>
        <div className="flex flex-col text-right">
          <span className="text-sm font-bold text-gray-400 uppercase tracking-widest">Total Spend (Today)</span>
          <span className="text-2xl font-mono text-green-600">.00</span>
        </div>
      </div>

      <div className="bg-gray-800 p-6 rounded border border-gray-800">
        <h2 className="font-bold text-gray-200 mb-4">Cost Mode</h2>
        <div className="flex space-x-4">
          <button 
            onClick={() => setCostMode('FREE-FIRST')}
            className={lex-1 p-4 rounded border-2 font-bold }
          >
            FREE-FIRST (ZERO SPEND)
            <div className="text-xs font-normal mt-1">Force local Ollama. Fail if unavailable.</div>
          </button>
          <button 
            onClick={() => setCostMode('BALANCED')}
            className={lex-1 p-4 rounded border-2 font-bold }
          >
            BALANCED
            <div className="text-xs font-normal mt-1">Local first. Fallback to free Groq tier.</div>
          </button>
          <button 
            onClick={() => setCostMode('UNRESTRICTED')}
            className={lex-1 p-4 rounded border-2 font-bold }
          >
            BYO UNRESTRICTED
            <div className="text-xs font-normal mt-1 text-red-600">Use paid APIs (OpenAI/Anthropic).</div>
          </button>
        </div>
      </div>

      <div className="space-y-4">
        {/* Groq Provider Card */}
        <div className="bg-gray-900 p-6 rounded shadow-lg shadow-black/50 border border-gray-800 flex justify-between items-center">
          <div>
            <div className="flex items-center space-x-2 mb-1">
              <h3 className="font-bold text-lg">Groq</h3>
              <span className="bg-green-900/30 text-green-300 text-xs px-2 py-1 rounded font-bold">HEALTHY</span>
            </div>
            <div className="flex items-center space-x-2">
              <span className="font-mono text-sm bg-gray-800 px-2 py-1 rounded border border-gray-800">gsk_...9a2f</span>
              <span className="text-xs text-gray-400 italic">Key masked for security</span>
            </div>
          </div>
          <div className="flex space-x-4">
            <div className="text-right mr-4">
              <div className="text-xs font-bold text-gray-400 uppercase">Est. Cost</div>
              <div className="font-mono">.00</div>
            </div>
            <button className="bg-gray-800 hover:bg-gray-700 text-gray-200 font-bold py-2 px-4 rounded border border-gray-800 transition">Test Connection</button>
            <button className="bg-red-900/20 hover:bg-red-900/30 text-red-600 font-bold py-2 px-4 rounded border border-gray-800 transition">Remove Key</button>
          </div>
        </div>
      </div>

    </div>
  );
}
''')
