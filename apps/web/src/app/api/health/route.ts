import { NextResponse } from "next/server";

export const runtime = "edge";

export async function GET() {
  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL;
  let backendOk = false;

  if (apiBase) {
    try {
      const res = await fetch(`${apiBase}/health/live`, {
        signal: AbortSignal.timeout(5000),
      });
      backendOk = res.ok;
    } catch {
      backendOk = false;
    }
  }

  return NextResponse.json({
    status: "ok",
    env: process.env.NEXT_PUBLIC_APP_ENV ?? "unknown",
    backend: backendOk ? "reachable" : "unreachable",
    timestamp: new Date().toISOString(),
  });
}
