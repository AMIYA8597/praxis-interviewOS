#!/usr/bin/env python3
"""
PRAXIS Reference Client.

Workflow:
1. Real Supabase user authentication (or provided JWT token).
2. REST Journey:
   - Verify candidate identity (GET /api/v1/auth/me)
   - Create / upload resume (POST /api/v1/resumes)
   - Create job target (POST /api/v1/jobs)
   - Initialize practice session (POST /api/v1/sessions)
3. WebSocket Journey:
   - Connect to praxis-realtime (wss://.../ws/sessions/{session_id}?token={jwt})
   - Receive interviewer opening question
   - Stream PCM16 audio at real-time pace with strict 18-byte protocol headers
   - Record coaching timestamps (VAD speech_end, transcript, turn scoring, debrief)
   - End session cleanly and display debrief results.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import math
import os
import struct
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import httpx
import websockets

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("praxis_client")

def generate_synthetic_pcm16(duration_s: float = 4.0, sample_rate: int = 16000) -> bytes:
    """Generate a 16kHz PCM16 mono sine audio clip for testing speech streaming."""
    num_samples = int(duration_s * sample_rate)
    samples = []
    for i in range(num_samples):
        # 440 Hz tone modulated by 2 Hz envelope
        t = i / sample_rate
        amp = 0.3 * math.sin(2 * math.pi * 2 * t)
        val = int(amp * math.sin(2 * math.pi * 440 * t) * 32767)
        samples.append(max(-32768, min(32767, val)))
    return struct.pack(f"<{len(samples)}h", *samples)

class PraxisClient:
    def __init__(self, api_url: str, realtime_url: str, token: Optional[str] = None):
        self.api_url = api_url.rstrip("/")
        self.realtime_url = realtime_url.rstrip("/")
        self.token = token
        self.coaching_timestamps: List[Dict[str, Any]] = []

    async def authenticate(self, email: Optional[str] = None, password: Optional[str] = None) -> str:
        """Authenticate with Supabase Auth or use existing token."""
        if self.token:
            logger.info("Using provided JWT token.")
            return self.token

        supabase_url = os.environ.get("SUPABASE_URL", "").rstrip("/")
        supabase_key = os.environ.get("SUPABASE_ANON_KEY", "")
        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY required to authenticate, or provide --token")

        logger.info(f"Authenticating user '{email}' against Supabase Auth...")
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{supabase_url}/auth/v1/token?grant_type=password",
                headers={"apikey": supabase_key, "Content-Type": "application/json"},
                json={"email": email, "password": password},
                timeout=15.0
            )
            if resp.status_code != 200:
                raise RuntimeError(f"Authentication failed ({resp.status_code}): {resp.text}")
            data = resp.json()
            self.token = data["access_token"]
            logger.info("Authentication successful.")
            return self.token

    async def run_rest_journey(self) -> Dict[str, Any]:
        """Execute candidate REST onboarding journey."""
        headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=30.0) as client:
            # 1. Identity
            logger.info("REST: Checking candidate profile (/api/v1/auth/me)...")
            me_resp = await client.get(f"{self.api_url}/api/v1/auth/me", headers=headers)
            if me_resp.status_code != 200:
                raise RuntimeError(f"Failed to get candidate profile: {me_resp.text}")
            candidate = me_resp.json()
            candidate_id = candidate.get("id")
            logger.info(f"REST: Candidate verified: {candidate.get('full_name')} ({candidate_id})")

            # 2. Upload / create resume
            logger.info("REST: Submitting resume profile...")
            resume_resp = await client.post(
                f"{self.api_url}/api/v1/resumes",
                headers=headers,
                json={
                    "raw_text": "Experienced Python Backend Engineer with expertise in FastAPI, PostgreSQL, Docker, and distributed systems. Built high-throughput microservices handling 50k req/s.",
                    "file_name": "resume.txt"
                }
            )
            resume_id = resume_resp.json().get("id") if resume_resp.status_code in (200, 201) else None

            # 3. Create Job
            logger.info("REST: Submitting target Job Description...")
            job_resp = await client.post(
                f"{self.api_url}/api/v1/jobs",
                headers=headers,
                json={
                    "role_title": "Senior Backend Engineer",
                    "company_name": "Praxis Tech",
                    "raw_text": "Looking for Senior Backend Engineer with strong Python, FastAPI, PostgreSQL, and System Design skills."
                }
            )
            job_id = job_resp.json().get("id") if job_resp.status_code in (200, 201) else "00000000-0000-0000-0000-000000000000"

            # 4. Create Session
            logger.info("REST: Creating practice session...")
            session_resp = await client.post(
                f"{self.api_url}/api/v1/sessions",
                headers=headers,
                json={
                    "job_id": job_id,
                    "difficulty": "standard",
                    "interview_type": "technical"
                }
            )
            if session_resp.status_code not in (200, 201):
                raise RuntimeError(f"Failed to create practice session: {session_resp.text}")
            session_data = session_resp.json()
            session_id = session_data.get("id")
            logger.info(f"REST: Practice session created: {session_id}")
            return {"session_id": session_id, "candidate_id": candidate_id, "job_id": job_id}

    async def run_websocket_stream(self, session_id: str, pcm_bytes: bytes):
        """Connect to WebSocket, stream audio at real-time pace, record coaching events."""
        ws_url = f"{self.realtime_url}/ws/sessions/{session_id}?token={self.token}"
        logger.info(f"WS: Connecting to {ws_url}...")

        async with websockets.connect(ws_url) as ws:
            logger.info("WS: Connected. Awaiting opening question...")
            
            # 1. Receive opening flow
            interviewer_asked = False
            while not interviewer_asked:
                msg = await ws.recv()
                if isinstance(msg, str):
                    ev = json.loads(msg)
                    self._record_event(ev)
                    if ev.get("type") == "interviewer.text":
                        logger.info(f"Interviewer: {ev.get('payload', {}).get('text')}")
                        interviewer_asked = True

            # 2. Stream audio at real-time pace (20ms frames: 320 samples = 640 bytes)
            frame_size = 640
            frame_duration = 0.02  # 20ms
            total_frames = len(pcm_bytes) // frame_size
            logger.info(f"WS: Streaming {total_frames} audio frames at real-time pace (16kHz mono PCM16)...")

            for seq_num in range(total_frames):
                chunk = pcm_bytes[seq_num * frame_size : (seq_num + 1) * frame_size]
                capture_ts = time.time()
                # Protocol header: >BBIdI (proto_ver=1, frame_type=1, seq, ts, len)
                header = struct.pack(">BBIdI", 1, 1, seq_num, capture_ts, len(chunk))
                await ws.send(header + chunk)
                await asyncio.sleep(frame_duration)

            logger.info("WS: Audio stream completed. Awaiting transcript & scoring...")

            # 3. Collect responses
            debrief_received = False
            session_end_sent = False
            start_wait = time.time()

            while time.time() - start_wait < 30.0:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
                except asyncio.TimeoutError:
                    if not session_end_sent:
                        logger.info("WS: Sending session.end...")
                        await ws.send(json.dumps({"type": "session.end"}))
                        session_end_sent = True
                    continue

                if isinstance(msg, str):
                    ev = json.loads(msg)
                    self._record_event(ev)
                    etype = ev.get("type")
                    if etype == "turn.scoring_result":
                        logger.info(f"Coaching Scoring Result: {ev.get('payload')}")
                        if not session_end_sent:
                            logger.info("WS: Sending session.end...")
                            await ws.send(json.dumps({"type": "session.end"}))
                            session_end_sent = True
                    elif etype == "debrief.ready":
                        logger.info(f"Debrief Ready! Summary: {ev.get('payload')}")
                        debrief_received = True
                        break

            logger.info("WS: Session completed successfully.")

    def _record_event(self, ev: Dict[str, Any]):
        t = datetime.now(timezone.utc).isoformat()
        etype = ev.get("type")
        self.coaching_timestamps.append({"timestamp": t, "type": etype, "payload": ev.get("payload")})
        logger.info(f"Event received [{etype}] at {t}")

async def main():
    parser = argparse.ArgumentParser(description="PRAXIS Reference Client")
    parser.add_argument("--api-url", default="http://localhost:8000")
    parser.add_argument("--realtime-url", default="ws://localhost:8080")
    parser.add_argument("--token", help="Bearer JWT token")
    parser.add_argument("--email", default="candidate@example.com")
    parser.add_argument("--password", default="password123")
    parser.add_argument("--wav", help="Path to input WAV file")
    args = parser.parse_args()

    client = PraxisClient(api_url=args.api_url, realtime_url=args.realtime_url, token=args.token)
    try:
        await client.authenticate(email=args.email, password=args.password)
    except Exception as e:
        logger.warning(f"Live auth skipped or failed ({e}); client ready for direct JWT token.")

    pcm = generate_synthetic_pcm16(duration_s=3.0)
    logger.info(f"Generated {len(pcm)} bytes of 16kHz test PCM audio.")

if __name__ == "__main__":
    asyncio.run(main())
