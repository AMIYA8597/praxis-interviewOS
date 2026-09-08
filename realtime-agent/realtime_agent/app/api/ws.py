from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import logging
import asyncio

from .audio.vad import SileroVAD
from .audio.turn_detection import TurnDetector

router = APIRouter()
logger = logging.getLogger(__name__)

@router.websocket("/{session_id}/audio")
async def audio_websocket(websocket: WebSocket, session_id: str):
    """
    Ingests binary PCM frames from the Electron client.
    Handles Out-Of-Sequence reordering and monotonic sequence tracking.
    """
    await websocket.accept()
    logger.info(f"WebSocket opened for session {session_id}")
    
    vad = SileroVAD()
    detector = TurnDetector()
    expected_sequence = 0
    buffer = {}

    try:
        while True:
            # Receive binary frame (4 bytes sequence, 8 bytes timestamp, N bytes PCM)
            data = await websocket.receive_bytes()
            
            # STUB parsing
            seq = int.from_bytes(data[0:4], "little")
            timestamp_ms = int.from_bytes(data[4:12], "little")
            pcm_payload = data[12:]
            
            # Reorder buffer logic
            if seq < expected_sequence:
                logger.warning(f"Dropping stale frame {seq} (expected {expected_sequence})")
                continue
                
            buffer[seq] = pcm_payload
            
            while expected_sequence in buffer:
                frame = buffer.pop(expected_sequence)
                expected_sequence += 1
                
                # 1. Process VAD
                confidence = vad.process_frame(frame)
                
                # 2. Turn Detection & Barge-In Check
                barge_in_triggered = detector.process_vad_confidence(confidence, timestamp_ms)
                
                if barge_in_triggered:
                    logger.warning(f"BARGE-IN DETECTED at {timestamp_ms}ms. Canceling in-flight TTS.")
                    await websocket.send_json({"event": "barge-in", "timestamp": timestamp_ms})
                
                # 3. Push to STT buffer (faster-whisper)
                # stt.append(frame)

    except WebSocketDisconnect:
        logger.info(f"WebSocket closed for session {session_id}")
