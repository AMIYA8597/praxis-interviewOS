import asyncio
import os
import sys
import json
import websockets

async def test_reconnect():
    session_id = os.environ.get("SESSION_ID")
    token = os.environ.get("TOKEN")
    
    if not session_id or not token:
        print("Please set SESSION_ID and TOKEN environment variables.")
        sys.exit(1)
        
    uri = f"ws://localhost:8001/ws/sessions/{session_id}?token={token}"
    
    try:
        # First connection
        print("--- FIRST CONNECTION ---")
        async with websockets.connect(uri) as ws:
            print(f"Connected to {uri}")
            while True:
                msg = await ws.recv()
                evt = json.loads(msg)
                if evt["type"] == "state.transitioned":
                    print(f"State transitioned to {evt['payload']['to']}")
                    if evt["payload"]["to"] == "READY":
                        break
                        
            # Simulate a drop by exiting context manager abruptly
            print("Simulating network drop... closing connection abruptly.")
            
        await asyncio.sleep(2) # Wait a bit to simulate real-world drop time
        
        # Second connection
        print("\n--- RECONNECTION ---")
        async with websockets.connect(uri) as ws:
            print(f"Reconnected to {uri}")
            msg = await ws.recv()
            evt = json.loads(msg)
            if evt["type"] == "state.transitioned":
                print(f"State resumed to {evt['payload']['to']} (Reason: {evt['payload'].get('reason')})")
                assert evt['payload']['to'] == "READY"
            
            print("Reconnection test successful. State resumed correctly.")
            
    except Exception as e:
        print(f"Test failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(test_reconnect())
