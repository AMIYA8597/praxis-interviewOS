import asyncio
import os
import sys
import json
import websockets

async def test_echo():
    session_id = os.environ.get("SESSION_ID")
    token = os.environ.get("TOKEN")
    
    if not session_id or not token:
        print("Please set SESSION_ID and TOKEN environment variables.")
        sys.exit(1)
        
    uri = f"ws://localhost:8001/ws/sessions/{session_id}?token={token}"
    
    try:
        async with websockets.connect(uri) as ws:
            print(f"Connected to {uri}")
            
            # 1. Receive state transitions until READY
            while True:
                msg = await ws.recv()
                evt = json.loads(msg)
                if evt["type"] == "state.transitioned":
                    to_state = evt["payload"]["to"]
                    print(f"State transitioned to {to_state}")
                    if to_state == "READY":
                        break
                else:
                    print(f"Unexpected event during startup: {evt['type']}")
            
            # 2. Send 10 binary frames and wait for acks
            for i in range(1, 11):
                payload = os.urandom(1024) # Fake 1KB audio frame
                await ws.send(payload)
                print(f"Sent binary frame {i} of 1024 bytes")
                
                # Receive ack
                ack_msg = await ws.recv()
                ack_evt = json.loads(ack_msg)
                
                if ack_evt["type"] != "audio.frame_ack":
                    print(f"Expected audio.frame_ack, got {ack_evt['type']}")
                    sys.exit(1)
                    
                print(f"Received ack for frame {i}: server_seq={ack_evt['payload']['server_seq']}, length={ack_evt['payload']['length']}")
                
            print("Smoke test completed successfully. 10 frames acknowledged.")
            
    except Exception as e:
        print(f"Test failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(test_echo())
