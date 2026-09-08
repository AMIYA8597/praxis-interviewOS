from enum import Enum
from typing import Dict, Set

class SessionState(str, Enum):
    IDLE = "IDLE"
    PREFLIGHT = "PREFLIGHT"
    WARMING = "WARMING"
    READY = "READY"
    INTERVIEWER_TURN = "INTERVIEWER_TURN"
    AWAITING_ANSWER = "AWAITING_ANSWER"
    CANDIDATE_TURN = "CANDIDATE_TURN"
    YIELDING = "YIELDING"
    TURN_END = "TURN_END"
    SCORING = "SCORING"
    PLANNING_NEXT = "PLANNING_NEXT"
    DEBRIEF = "DEBRIEF"
    
    # Error lattice and terminal
    DEGRADED_STT = "DEGRADED_STT"
    DEGRADED_LLM = "DEGRADED_LLM"
    DEGRADED_TTS = "DEGRADED_TTS"
    RECONNECTING = "RECONNECTING"
    PAUSED = "PAUSED"
    FAILED = "FAILED"
    STOPPED = "STOPPED"

class InvalidTransitionError(Exception):
    def __init__(self, from_state: SessionState, to_state: SessionState):
        self.from_state = from_state
        self.to_state = to_state
        super().__init__(f"Invalid transition from {from_state.value} to {to_state.value}")

TRANSITIONS: Dict[SessionState, Set[SessionState]] = {
    SessionState.IDLE: {SessionState.PREFLIGHT, SessionState.FAILED, SessionState.STOPPED},
    SessionState.PREFLIGHT: {SessionState.WARMING, SessionState.FAILED, SessionState.STOPPED, SessionState.RECONNECTING},
    SessionState.WARMING: {SessionState.READY, SessionState.FAILED, SessionState.STOPPED, SessionState.RECONNECTING},
    SessionState.READY: {SessionState.INTERVIEWER_TURN, SessionState.DEBRIEF, SessionState.PAUSED, SessionState.FAILED, SessionState.STOPPED, SessionState.RECONNECTING},
    SessionState.INTERVIEWER_TURN: {SessionState.YIELDING, SessionState.AWAITING_ANSWER, SessionState.DEGRADED_TTS, SessionState.FAILED, SessionState.STOPPED, SessionState.RECONNECTING},
    SessionState.AWAITING_ANSWER: {SessionState.CANDIDATE_TURN, SessionState.FAILED, SessionState.STOPPED, SessionState.RECONNECTING},
    SessionState.CANDIDATE_TURN: {SessionState.YIELDING, SessionState.TURN_END, SessionState.DEGRADED_STT, SessionState.FAILED, SessionState.STOPPED, SessionState.RECONNECTING},
    SessionState.YIELDING: {SessionState.INTERVIEWER_TURN, SessionState.AWAITING_ANSWER, SessionState.TURN_END, SessionState.FAILED, SessionState.STOPPED, SessionState.RECONNECTING},
    SessionState.TURN_END: {SessionState.SCORING, SessionState.FAILED, SessionState.STOPPED, SessionState.RECONNECTING},
    SessionState.SCORING: {SessionState.PLANNING_NEXT, SessionState.DEGRADED_LLM, SessionState.FAILED, SessionState.STOPPED, SessionState.RECONNECTING},
    SessionState.PLANNING_NEXT: {SessionState.READY, SessionState.DEGRADED_LLM, SessionState.FAILED, SessionState.STOPPED, SessionState.RECONNECTING},
    
    SessionState.DEGRADED_STT: {SessionState.TURN_END, SessionState.FAILED, SessionState.STOPPED, SessionState.RECONNECTING},
    SessionState.DEGRADED_LLM: {SessionState.READY, SessionState.FAILED, SessionState.STOPPED, SessionState.RECONNECTING},
    SessionState.DEGRADED_TTS: {SessionState.AWAITING_ANSWER, SessionState.FAILED, SessionState.STOPPED, SessionState.RECONNECTING},
    
    SessionState.RECONNECTING: {
        SessionState.PREFLIGHT, SessionState.WARMING, SessionState.READY, SessionState.INTERVIEWER_TURN,
        SessionState.AWAITING_ANSWER, SessionState.CANDIDATE_TURN, SessionState.YIELDING, SessionState.TURN_END,
        SessionState.SCORING, SessionState.PLANNING_NEXT, SessionState.DEBRIEF,
        SessionState.FAILED, SessionState.STOPPED
    },
    
    SessionState.PAUSED: {SessionState.READY, SessionState.STOPPED, SessionState.FAILED, SessionState.RECONNECTING},
    
    SessionState.DEBRIEF: {SessionState.STOPPED, SessionState.FAILED, SessionState.RECONNECTING},
    
    # Terminals
    SessionState.FAILED: set(),
    SessionState.STOPPED: set()
}

class StateMachine:
    def __init__(self, initial_state: SessionState = SessionState.IDLE):
        self.state = initial_state

    def transition(self, to_state: SessionState):
        if to_state not in TRANSITIONS.get(self.state, set()):
            raise InvalidTransitionError(self.state, to_state)
            
        from opentelemetry import trace
        tracer = trace.get_tracer(__name__)
        span = trace.get_current_span()
        if span.is_recording():
            span.add_event("state_transition", {"from_state": self.state.value, "to_state": to_state.value})
            
        self.state = to_state
