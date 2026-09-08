import time
from enum import Enum
from collections import deque
import logging

logger = logging.getLogger(__name__)

class SessionState(Enum):
    IDLE = "IDLE"
    PREFLIGHT = "PREFLIGHT"
    WARMING = "WARMING"
    READY = "READY"
    INTERVIEWER_TURN = "INTERVIEWER_TURN"
    AWAITING_ANSWER = "AWAITING_ANSWER"
    CANDIDATE_TURN = "CANDIDATE_TURN"
    TURN_END = "TURN_END"
    SCORING = "SCORING"
    PLANNING_NEXT = "PLANNING_NEXT"
    DEBRIEF = "DEBRIEF"
    YIELDING = "YIELDING"
    
    # Error Lattice
    DEGRADED_STT = "DEGRADED_STT"
    DEGRADED_LLM = "DEGRADED_LLM"
    DEGRADED_TTS = "DEGRADED_TTS"
    RECONNECTING = "RECONNECTING"
    PAUSED = "PAUSED"
    FAILED = "FAILED"
    STOPPED = "STOPPED"

class StateMachine:
    # Valid transitions
    VALID_TRANSITIONS = {
        SessionState.IDLE: [SessionState.PREFLIGHT],
        SessionState.PREFLIGHT: [SessionState.WARMING, SessionState.FAILED],
        SessionState.WARMING: [SessionState.READY, SessionState.FAILED],
        SessionState.READY: [SessionState.INTERVIEWER_TURN, SessionState.STOPPED],
        SessionState.INTERVIEWER_TURN: [SessionState.AWAITING_ANSWER, SessionState.YIELDING],
        SessionState.AWAITING_ANSWER: [SessionState.CANDIDATE_TURN],
        SessionState.YIELDING: [SessionState.AWAITING_ANSWER],
        SessionState.CANDIDATE_TURN: [SessionState.TURN_END],
        SessionState.TURN_END: [SessionState.SCORING],
        SessionState.SCORING: [SessionState.PLANNING_NEXT],
        SessionState.PLANNING_NEXT: [SessionState.INTERVIEWER_TURN, SessionState.DEBRIEF],
    }

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.state = SessionState.IDLE
        # In-memory ring buffer (max 1000 events)
        self.audit_log = deque(maxlen=1000)

    def transition_to(self, new_state: SessionState, reason: str = ""):
        # Error states can be entered from anywhere
        is_error_state = new_state in [
            SessionState.DEGRADED_STT, SessionState.DEGRADED_LLM, 
            SessionState.DEGRADED_TTS, SessionState.RECONNECTING, 
            SessionState.PAUSED, SessionState.FAILED, SessionState.STOPPED
        ]
        
        valid = is_error_state or (new_state in self.VALID_TRANSITIONS.get(self.state, []))
        
        if not valid:
            logger.warning(f"Invalid transition attempted: {self.state.name} -> {new_state.name}")
            return False
            
        record = {
            "from": self.state.name,
            "to": new_state.name,
            "reason": reason,
            "timestamp": time.time(),
            "session_id": self.session_id
        }
        self.audit_log.append(record)
        
        logger.info(f"State transition: {self.state.name} -> {new_state.name} ({reason})")
        self.state = new_state
        return True

    def dump_log(self):
        return list(self.audit_log)
