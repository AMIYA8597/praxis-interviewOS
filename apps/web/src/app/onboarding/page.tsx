"use client";

import { useState } from "react";
import { supabase } from "@/lib/supabase";

export default function OnboardingPage() {
  const [name, setName] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatus("Uploading...");

    let token = "mock-token";
    if (process.env.NEXT_PUBLIC_SUPABASE_URL) {
      const { data } = await supabase.auth.getSession();
      token = data.session?.access_token || "";
    }

    try {
      // 1. Update Profile
      await fetch("http://localhost:8000/api/v1/candidates/me", {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ name, summary: "Initial upload" }),
      });

      // 2. Upload Resume if selected
      if (file) {
        const formData = new FormData();
        formData.append("file", file);

        const res = await fetch("http://localhost:8000/api/v1/resumes/upload", {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
          },
          body: formData,
        });
        
        if (!res.ok) {
            const errorData = await res.json();
            throw new Error(errorData.detail || "Failed to upload resume");
        }
      }

      setStatus("Success! Resume processing started.");
      setTimeout(() => {
        window.location.href = "/";
      }, 1500);
    } catch (err: any) {
      setStatus(`Error: ${err.message}`);
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
            Save & Continue
          </button>
        </form>
        {status && <p className="mt-4 text-center text-sm text-neutral-400">{status}</p>}
      </div>
    </div>
  );
}
