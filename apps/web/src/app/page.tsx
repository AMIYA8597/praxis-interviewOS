import React from 'react';
import Link from 'next/link';

export default function Home() {
  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 selection:bg-indigo-500 selection:text-white">
      {/* Navigation Header */}
      <header className="border-b border-zinc-800/80 bg-zinc-950/80 backdrop-blur sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center font-bold text-white tracking-wider text-sm">
              PX
            </div>
            <span className="font-bold text-lg tracking-tight text-white">
              PRAXIS <span className="text-indigo-400 font-mono text-sm font-normal">InterviewOS</span>
            </span>
          </div>

          <div className="flex items-center gap-4">
            <Link
              href="/auth"
              className="text-xs font-semibold text-zinc-300 hover:text-white transition-colors"
            >
              Sign In
            </Link>
            <Link
              href="/auth"
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-md text-xs font-semibold transition-colors shadow-sm"
            >
              Get Started →
            </Link>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="py-20 px-6 max-w-5xl mx-auto text-center space-y-6">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-indigo-500/30 bg-indigo-950/40 text-indigo-300 text-xs font-mono">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          Production AI/ML Intelligence Engine Active
        </div>

        <h1 className="text-4xl sm:text-6xl font-extrabold tracking-tight text-white max-w-4xl mx-auto leading-tight">
          Master Technical Interviews Through Real-Time Speech Intelligence
        </h1>

        <p className="text-base sm:text-lg text-zinc-400 max-w-2xl mx-auto leading-relaxed">
          PRAXIS evaluates what you actually know, how you explain complex architectures, and whether your claims align with your genuine project experience.
        </p>

        <div className="flex flex-wrap justify-center gap-4 pt-4">
          <Link
            href="/sessions"
            className="px-6 py-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm font-semibold shadow-lg shadow-indigo-600/20 transition-all"
          >
            Enter Practice Arena
          </Link>
          <Link
            href="/readiness"
            className="px-6 py-3 bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-300 rounded-lg text-sm font-semibold transition-colors"
          >
            View Readiness Estimate
          </Link>
        </div>
      </section>

      {/* Core Capabilities Grid */}
      <section className="py-16 px-6 max-w-7xl mx-auto border-t border-zinc-900">
        <div className="text-center mb-12">
          <h2 className="text-2xl font-bold text-white">Engineered for Technical Depth</h2>
          <p className="text-xs text-zinc-500 mt-1 uppercase tracking-widest font-mono">
            Full-Stack Intelligence Architecture
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Card 1 */}
          <div className="p-6 rounded-xl bg-zinc-900/60 border border-zinc-800/80 space-y-3">
            <div className="w-10 h-10 rounded-lg bg-blue-950/60 border border-blue-800/60 flex items-center justify-center text-blue-400 font-bold text-sm">
              ASR
            </div>
            <h3 className="text-base font-bold text-white">Real-Time Speech Processing</h3>
            <p className="text-xs text-zinc-400 leading-relaxed">
              Faster-Whisper on-device speech-to-text with 1Hz dual-path coaching metrics: speaking pace (WPM), filler word rate, and turn timing.
            </p>
          </div>

          {/* Card 2 */}
          <div className="p-6 rounded-xl bg-zinc-900/60 border border-zinc-800/80 space-y-3">
            <div className="w-10 h-10 rounded-lg bg-emerald-950/60 border border-emerald-800/60 flex items-center justify-center text-emerald-400 font-bold text-sm">
              5T
            </div>
            <h3 className="text-base font-bold text-white">5-Tier Evidence Grounding</h3>
            <p className="text-xs text-zinc-400 leading-relaxed">
              Every verbal claim is cross-referenced against your uploaded resume and GitHub project chunks using hybrid vector and lexical retrieval.
            </p>
          </div>

          {/* Card 3 */}
          <div className="p-6 rounded-xl bg-zinc-900/60 border border-zinc-800/80 space-y-3">
            <div className="w-10 h-10 rounded-lg bg-indigo-950/60 border border-indigo-800/60 flex items-center justify-center text-indigo-400 font-bold text-sm">
              STAR
            </div>
            <h3 className="text-base font-bold text-white">STAR Rubric Evaluation</h3>
            <p className="text-xs text-zinc-400 leading-relaxed">
              Multi-dimensional scoring across relevance, technical correctness, structure, specificity, grounding, and conciseness with honest measurement transparency.
            </p>
          </div>
        </div>
      </section>

      {/* Ethical Compliance Banner */}
      <section className="py-12 px-6 max-w-4xl mx-auto mb-16">
        <div className="p-6 rounded-xl bg-zinc-900/40 border border-zinc-800 text-center space-y-2">
          <span className="text-[11px] font-mono font-bold uppercase tracking-widest text-indigo-400">
            Ethical AI & Authenticity Invariant (ADR-001)
          </span>
          <h4 className="text-sm font-semibold text-zinc-200">
            Dedicated Exclusively to Preparation & Genuine Competency
          </h4>
          <p className="text-xs text-zinc-400 max-w-xl mx-auto leading-relaxed">
            PRAXIS contains zero proctor evasion, window-hiding, or live assessment cheating mechanisms. It is designed solely for ethical practice, authentic feedback, and legitimate interview preparation.
          </p>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-zinc-900 py-8 px-6 text-center text-xs text-zinc-600 font-mono">
        PRAXIS InterviewOS • Production Architecture • All Rights Reserved
      </footer>
    </div>
  );
}
