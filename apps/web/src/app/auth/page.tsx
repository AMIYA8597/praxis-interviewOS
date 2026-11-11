"use client";

import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabase";

export default function AuthPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLogin, setIsLogin] = useState(true);
  const [message, setMessage] = useState("");
  const [messageType, setMessageType] = useState<"info" | "error" | "success">("info");
  const [signedUp, setSignedUp] = useState(false);

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      if (data.session) {
        window.location.href = "/onboarding";
      }
    });
  }, []);

  const handleAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    setMessage("Processing...");
    setMessageType("info");

    if (!process.env.NEXT_PUBLIC_SUPABASE_URL) {
      setMessage("Error: Supabase is not configured.");
      setMessageType("error");
      return;
    }

    try {
      if (isLogin) {
        const { error } = await supabase.auth.signInWithPassword({ email, password });
        if (error) throw error;
        window.location.href = "/onboarding";
      } else {
        const { data, error } = await supabase.auth.signUp({
          email,
          password,
          options: {
            emailRedirectTo: `${window.location.origin}/auth`,
          },
        });
        if (error) throw error;
        if (data.user?.identities?.length === 0) {
          setMessage("An account with this email already exists. Please sign in.");
          setMessageType("error");
          setIsLogin(true);
        } else {
          setSignedUp(true);
          setMessage(`Confirmation email sent to ${email}. Click the link in your email, then come back and sign in.`);
          setMessageType("success");
        }
      }
    } catch (err: any) {
      setMessage(err.message || "An error occurred");
      setMessageType("error");
    }
  };

  const messageColor =
    messageType === "error"
      ? "text-red-400"
      : messageType === "success"
        ? "text-green-400"
        : "text-neutral-400";

  return (
    <div className="flex min-h-screen flex-col items-center justify-center p-24 bg-neutral-950 text-white">
      <div className="z-10 max-w-md w-full font-mono text-sm border border-neutral-800 p-8 rounded shadow-lg bg-neutral-900">
        <h1 className="text-2xl font-bold mb-6 text-center">
          {signedUp ? "Check Your Email" : isLogin ? "Sign In" : "Sign Up"}
        </h1>
        {signedUp ? (
          <div className="flex flex-col gap-4">
            <p className="text-center text-green-400">{message}</p>
            <button
              onClick={() => {
                setSignedUp(false);
                setIsLogin(true);
                setMessage("");
              }}
              className="p-2 bg-white text-black font-bold rounded mt-2"
            >
              I confirmed my email — Sign In
            </button>
          </div>
        ) : (
          <>
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
                placeholder="Password (min 6 characters)"
                className="p-2 bg-neutral-800 border border-neutral-700 rounded text-white"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                minLength={6}
                required
              />
              <button type="submit" className="p-2 bg-white text-black font-bold rounded mt-2">
                {isLogin ? "Sign In" : "Sign Up"}
              </button>
            </form>
            {message && <p className={`mt-4 text-center text-sm ${messageColor}`}>{message}</p>}
            <button
              className="mt-6 text-xs text-neutral-500 w-full text-center hover:text-white"
              onClick={() => {
                setIsLogin(!isLogin);
                setMessage("");
              }}
            >
              {isLogin ? "Need an account? Sign up" : "Already have an account? Sign in"}
            </button>
          </>
        )}
      </div>
    </div>
  );
}
