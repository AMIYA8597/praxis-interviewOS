"use client";

import { useState } from "react";
import { supabase } from "@/lib/supabase";

export default function AuthPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLogin, setIsLogin] = useState(true);
  const [message, setMessage] = useState("");

  const handleAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    setMessage("Processing...");

    // Fast-path mock for local dev if Supabase is unconfigured
    if (!process.env.NEXT_PUBLIC_SUPABASE_URL) {
      setMessage("Running in Mock Mode. Please configure Supabase for real auth.");
      setTimeout(() => {
        window.location.href = "/onboarding";
      }, 1000);
      return;
    }

    try {
      if (isLogin) {
        const { error } = await supabase.auth.signInWithPassword({ email, password });
        if (error) throw error;
        window.location.href = "/onboarding";
      } else {
        const { error } = await supabase.auth.signUp({ email, password });
        if (error) throw error;
        setMessage("Check your email for confirmation!");
      }
    } catch (err: any) {
      setMessage(err.message || "An error occurred");
    }
  };

  return (
    <div className="flex min-h-screen flex-col items-center justify-center p-24 bg-neutral-950 text-white">
      <div className="z-10 max-w-md w-full font-mono text-sm border border-neutral-800 p-8 rounded shadow-lg bg-neutral-900">
        <h1 className="text-2xl font-bold mb-6 text-center">{isLogin ? "Sign In" : "Sign Up"}</h1>
        <form onSubmit={handleAuth} className="flex flex-col gap-4">
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
          <button type="submit" className="p-2 bg-white text-black font-bold rounded mt-2">
            {isLogin ? "Sign In" : "Sign Up"}
          </button>
        </form>
        {message && <p className="mt-4 text-center text-sm text-neutral-400">{message}</p>}
        <button
          className="mt-6 text-xs text-neutral-500 w-full text-center hover:text-white"
          onClick={() => setIsLogin(!isLogin)}
        >
          {isLogin ? "Need an account? Sign up" : "Already have an account? Sign in"}
        </button>
      </div>
    </div>
  );
}
