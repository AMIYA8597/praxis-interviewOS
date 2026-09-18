import asyncio
import websockets
import json
import time
import base64
import jwt
import os

from test_stt_accuracy import synthesize_audio

async def run_live_test():
    secret = os.environ.get("JWT_SECRET", "supersecret")
    token = jwt.encode({"sub": "test_user"}, secret, algorithm="HS256")
    
    # Needs the backend server to be running.
    # Start it temporarily if not? 
    uri = f"ws://localhost:8001/ws/test_session_id?token={token}"
    
    print("Generating audio payload...")
    # Generate 3 seconds of audio
    pcm_data = synthesize_audio("Hello, this is a real-time speech test over the websocket.")
    
    print(f"Connecting to {uri}")
    try:
        async with websockets.connect(uri) as ws:
            print("Connected.")
            
            # Send audio in 32ms chunks
            chunk_size = 512 * 2 # 1024 bytes = 32ms
            
            print("Sending audio...")
            for i in range(0, len(pcm_data), chunk_size):
                chunk = pcm_data[i:i+chunk_size]
                # Send binary frame
                await ws.send(chunk)
                await asyncio.sleep(0.032) # real-time simulation
                
            print("Finished sending audio. Waiting for transcript...")
            
            speech_end_time = time.perf_counter()
            final_received = False
            
            while not final_received:
                msg = await ws.recv()
                try:
                    data = json.loads(msg)
                    if data["type"] == "audio.frame_ack":
                        continue
                    if data["type"] == "speech_start":
                        print(f"Server detected speech start! Confidence: {data['payload']['confidence']}")
                    if data["type"] == "speech_end":
                        print(f"Server detected speech end!")
                        speech_end_time = time.perf_counter()
                    if data["type"] == "transcript.final":
                        recv_time = time.perf_counter()
                        latency = (recv_time - speech_end_time) * 1000
                        print(f"--- REALTIME E2E RESULT ---")
                        print(f"Text    : {data['payload']['text']}")
                        print(f"Latency : {latency:.2f} ms")
                        print(f"Source  : {data['payload']['source']}")
                        final_received = True
                except json.JSONDecodeError:
                    pass
                    
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(run_live_test())
