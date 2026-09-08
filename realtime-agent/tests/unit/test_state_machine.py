import pytest
from realtime_agent.app.session.state_machine import StateMachine, SessionState, InvalidTransitionError

def test_happy_path_sequence():
    sm = StateMachine()
    
    sequence = [
        SessionState.PREFLIGHT,
        SessionState.WARMING,
        SessionState.READY,
        SessionState.INTERVIEWER_TURN,
        SessionState.AWAITING_ANSWER,
        SessionState.CANDIDATE_TURN,
        SessionState.TURN_END,
        SessionState.SCORING,
        SessionState.PLANNING_NEXT,
        SessionState.READY
    ]
    
    for state in sequence:
        sm.transition(state)
        assert sm.state == state

def test_invalid_transitions():
    sm = StateMachine(SessionState.IDLE)
    with pytest.raises(InvalidTransitionError) as exc:
        sm.transition(SessionState.SCORING)
    assert exc.value.from_state == SessionState.IDLE
    assert exc.value.to_state == SessionState.SCORING
    
    sm = StateMachine(SessionState.READY)
    with pytest.raises(InvalidTransitionError):
        sm.transition(SessionState.IDLE)

def test_terminal_states():
    sm = StateMachine(SessionState.STOPPED)
    with pytest.raises(InvalidTransitionError):
        sm.transition(SessionState.READY)
        
    sm = StateMachine(SessionState.FAILED)
    with pytest.raises(InvalidTransitionError):
        sm.transition(SessionState.IDLE)
