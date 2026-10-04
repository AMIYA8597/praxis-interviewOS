"use client";

import { useState } from "react";
import { supabase } from "@/lib/supabase";
import { apiFetch, ApiError } from "@/lib/api/client";

export default function OnboardingPage() {
  const [name, setName] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatus("Uploading...");

    const { data } = await supabase.auth.getSession();
    if (!data.session?.access_token) {
      setStatus("Error: Not authenticated. Please sign in again.");
      return;
    }

    try {
      // 1. Update Profile
      await apiFetch("/candidates/me", {
        method: "PUT",
        body: JSON.stringify({ name, summary: "Initial upload" }),
      });

      // 2. Upload Resume if selected
      if (file) {
        const formData = new FormData();
        formData.append("file", file);
        await apiFetch("/resumes/upload", {
          method: "POST",
          body: formData,
        });
      }

      setStatus("Success! Resume processing started.");
      setTimeout(() => {
        window.location.href = "/";
      }, 1500);
    } catch (err: unknown) {
      const msg = err instanceof ApiError ? err.message : (err as Error).message;
      setStatus(`Error: ${msg}`);
    }
  };

  return (
    <div className="flex min-h-screen flex-col items-center justify-center p-24 bg-neutral-950 text-white">
      <div className="z-10 max-w-lg w-full font-mono text-sm border border-neutral-800 p-8 rounded shadow-lg bg-neutral-900">
        <h1 className="text-2xl font-bold mb-6">Complete Profile</h1>
        <form onSubmit={handleSubmit} className="flex flex-col gap-6">
          <div>
            <label className="block mb-2 text-neutral-400">Full Name</label>
            <input
              type="text"
              className="w-full p-2 bg-neutral-800 border border-neutral-700 rounded text-white"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
          </div>
          <div>
            <label className="block mb-2 text-neutral-400">Upload Resume (PDF)</label>
            <input
              type="file"
              accept=".pdf"
              className="w-full p-2 bg-neutral-800 border border-neutral-700 rounded text-neutral-300"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
            />
          </div>
          <button type="submit" className="p-3 bg-white text-black font-bold rounded mt-2">
            Save &amp; Continue
          </button>
        </form>
        {status && <p className="mt-4 text-center text-sm text-neutral-400">{status}</p>}
      </div>
    </div>
  );
}
