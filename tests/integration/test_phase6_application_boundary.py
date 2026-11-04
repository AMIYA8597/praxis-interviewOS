import os
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock
from faster_whisper import WhisperModel

from praxis_ai_gateway.errors import AIProviderNotConfiguredError
from praxis_ai_gateway.registry import ModelRegistry
from praxis_ai_gateway.router import GatewayRouter, RoutingContext, AllProvidersUnavailableError
from realtime_agent.app.audio.vad import VoiceActivityDetector
from realtime_agent.app.session.state_machine import StateMachine, SessionState
from realtime_agent.app.scoring.service import score_answer_async
from backend.app.services.debrief import generate_session_debrief


@pytest.fixture
def empty_router():
    config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "config", "models.yaml"))
    registry = ModelRegistry(config_path)
    mock_redis = AsyncMock()
    return GatewayRouter(registry=registry, providers={}, redis=mock_redis)


@pytest.mark.asyncio
async def test_gateway_unconfigured_raises_typed_error(empty_router):
    """Verify that when no LLM providers are configured/available, the gateway raises AI_PROVIDER_NOT_CONFIGURED."""
    ctx = RoutingContext(user_id="test_candidate_123", session_id="test_session_1")

    with pytest.raises(AllProvidersUnavailableError) as exc_info:
        await empty_router.route(
            task="interviewer_next_question",
            context=ctx,
            method_name="generate",
            prompt="Generate the next interview question.",
        )

    err = exc_info.value
    assert isinstance(err, AIProviderNotConfiguredError)
    assert err.error_code == "AI_PROVIDER_NOT_CONFIGURED"


@pytest.mark.asyncio
async def test_audio_pipeline_real_transcription_and_vad():
    """Verify real local STT and VAD inference on test audio fixture."""
    audio_path = "ai-evaluation/datasets/audio/clean_technical.wav"
    if not os.path.exists(audio_path):
        pytest.skip(f"Audio fixture missing: {audio_path}")

    # 1. Real Faster-Whisper transcription (CPU, int8) using locally cached tiny.en
    model = WhisperModel("tiny.en", device="cpu", compute_type="int8")
    segments, info = model.transcribe(audio_path)
    text = " ".join(s.text for s in segments)
    assert text.strip()
    transcript_lower = text.lower()
    assert "distributed systems" in transcript_lower
    assert "eventual consistency" in transcript_lower

    # 2. Real Silero VAD
    vad = VoiceActivityDetector()
    with open(audio_path, "rb") as f:
        # Read wav header (44 bytes) then PCM16 frames
        raw_wav = f.read()
    pcm_bytes = raw_wav[44:] if raw_wav.startswith(b"RIFF") else raw_wav

    # 512 samples = 1024 bytes (16kHz 16-bit mono)
    frame_size = 1024
    speech_frames = 0
    total_frames = 0
    for offset in range(0, len(pcm_bytes) - frame_size, frame_size):
        frame = pcm_bytes[offset : offset + frame_size]
        is_speech = vad.process_frame(frame)
        if is_speech:
            speech_frames += 1
        total_frames += 1

    assert total_frames > 0
    assert speech_frames > 0, "Silero VAD should detect speech in clean_technical.wav"


@pytest.mark.asyncio
async def test_interview_orchestration_state_machine():
    """Verify interview state machine lifecycle and turn transitions."""
    sm = StateMachine()
    assert sm.state == SessionState.IDLE

    sm.transition(SessionState.PREFLIGHT)
    assert sm.state == SessionState.PREFLIGHT

    sm.transition(SessionState.WARMING)
    assert sm.state == SessionState.WARMING

    sm.transition(SessionState.READY)
    assert sm.state == SessionState.READY

    sm.transition(SessionState.INTERVIEWER_TURN)
    assert sm.state == SessionState.INTERVIEWER_TURN

    sm.transition(SessionState.AWAITING_ANSWER)
    assert sm.state == SessionState.AWAITING_ANSWER

    sm.transition(SessionState.CANDIDATE_TURN)
    assert sm.state == SessionState.CANDIDATE_TURN

    sm.transition(SessionState.TURN_END)
    assert sm.state == SessionState.TURN_END

    sm.transition(SessionState.SCORING)
    assert sm.state == SessionState.SCORING

    sm.transition(SessionState.PLANNING_NEXT)
    assert sm.state == SessionState.PLANNING_NEXT


@pytest.mark.asyncio
async def test_scoring_service_degradation_when_unconfigured(empty_router):
    """Verify scoring service does not fabricate scores when LLM is unavailable."""
    ctx = RoutingContext(user_id="user-123", session_id="session-test-uuid")

    res = await score_answer_async(
        question="What is eventual consistency?",
        candidate_answer="Replicas converge eventually.",
        is_behavioral=False,
        verified_context="",
        gateway_router=empty_router,
        routing_ctx=ctx,
    )

    assert res.overall is None
    assert res.measurement_status == "UNAVAILABLE"


@pytest.mark.asyncio
async def test_debrief_aggregation_and_unconfigured_error(empty_router):
    """Verify debrief generation queries real database records and records AI failure when unconfigured."""
    session_id = str(uuid.uuid4())
    mock_db = AsyncMock()

    class MockMetric:
        def __init__(self, wpm, filler):
            self.wpm = wpm
            self.filler_count = filler

    class MockScore:
        def __init__(self, relevance, id_str):
            self.relevance = relevance
            self.id = uuid.UUID(id_str)

    res1 = MagicMock()
    res1.scalars.return_value.all.return_value = [MockMetric(140.0, 2), MockMetric(150.0, 4)]
    res2 = MagicMock()
    res2.scalars.return_value.all.return_value = [MockScore(0.85, str(uuid.uuid4()))]

    mock_db.execute.side_effect = [res1, res2]

    debrief_result = await generate_session_debrief(session_id, mock_db, empty_router)

    assert debrief_result["session_id"] == session_id
    assert debrief_result["headline_metrics"]["average_wpm"] == 145
    assert debrief_result["headline_metrics"]["average_filler_rate"] == 6
    assert debrief_result["headline_metrics"]["average_score"] == 0.8
    assert "Failed to generate AI debrief summary." in debrief_result["weaknesses"]
