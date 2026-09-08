from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from .transcription import MockTranscriber
from .vad import VADEngine
from .prosody import ProsodyExtractor
from .state import StateMachine, SessionState
from .telemetry import TelemetryTracker
from app.ai.classifier import DomainClassifier
from app.ai.scorer import Scorer, FollowUpPlanner
import logging
import asyncio
import time

logger = logging.getLogger(__name__)

router = APIRouter()

class SessionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket client connected. Active: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket client disconnected. Active: {len(self.active_connections)}")

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        await websocket.send_json(message)

manager = SessionManager()

@router.websocket("/ws/interviews/{session_id}")
async def interview_session(websocket: WebSocket, session_id: str):
    await manager.connect(websocket)
    
    vad = VADEngine()
    prosody = ProsodyExtractor()
    classifier = DomainClassifier()
    scorer = Scorer()
    planner = FollowUpPlanner()
    
    state_machine = StateMachine(session_id)
    telemetry = TelemetryTracker()
    
    state_machine.transition_to(SessionState.PREFLIGHT, "Initializing resources")
    state_machine.transition_to(SessionState.WARMING, "Warming up STT models")
    state_machine.transition_to(SessionState.READY, "System is ready")

    current_question = "Tell me about a time you had to deal with a difficult technical tradeoff."
    state_machine.transition_to(SessionState.INTERVIEWER_TURN, "Speaking initial question")
    
    # Initialize Transcriber
    async def stt_callback(event: dict):
        if event["type"] == "transcript.partial" or event["type"] == "transcript.final":
            text = event["payload"]["text"]
            prosody.process_transcript(text)
            
            # Send metrics update
            metrics = prosody.get_metrics()
            await manager.send_personal_message({
                "type": "coaching.metrics",
                "payload": metrics
            }, websocket)
            
            # If final transcript, run the answer pipeline
            if event["type"] == "transcript.final":
                telemetry.mark("stt_final_ts")
                state_machine.transition_to(SessionState.TURN_END, "Silence threshold reached")
                
                state_machine.transition_to(SessionState.SCORING, "Computing domain and scoring")
                telemetry.mark("classify_ts")
                domain = classifier.classify(text)
                score_data = scorer.score_answer(current_question, text, {})
                
                state_machine.transition_to(SessionState.PLANNING_NEXT, "Determining next question")
                telemetry.mark("retrieve_ts")
                next_q = planner.plan_next_question(current_question, text, domain)
                
                state_machine.transition_to(SessionState.INTERVIEWER_TURN, "Delivering next question")
                telemetry.mark("tts_first_audio_ts")
                
                await manager.send_personal_message({
                    "type": "interviewer.turn",
                    "payload": {
                        "domain": domain,
                        "score": score_data,
                        "next_question": next_q,
                        "telemetry": telemetry.compute_deltas()
                    }
                }, websocket)

        await manager.send_personal_message(event, websocket)

    transcriber = MockTranscriber(callback=stt_callback)
    await transcriber.connect()

    await manager.send_personal_message({
        "version": "1",
        "type": "session.ready",
        "session_id": session_id,
        "payload": {"status": "listening", "question": current_question}
    }, websocket)

    try:
        while True:
            data = await websocket.receive_bytes()
            vad_res = vad.process_frame(data)
            
            # Barge-in watch / VAD events
            for event in vad_res["events"]:
                await manager.send_personal_message({
                    "type": f"vad.{event}"
                }, websocket)
                
            await transcriber.send_audio(data)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await transcriber.close()
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)
        await transcriber.close()
