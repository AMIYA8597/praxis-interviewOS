import os
from unittest.mock import patch
from praxis_ai_gateway.transcription.router import select_transcriber
from praxis_ai_gateway.transcription.cloud_groq import GroqCloudTranscriber
from praxis_ai_gateway.transcription.local_faster_whisper import FasterWhisperTranscriber

def test_cloud_fallback_engages():
    # Set environment variables for the test
    os.environ["GROQ_API_KEY"] = "fake-test-key"
    
    settings = {
        "LOCAL_ONLY_MODE": "false"
    }
    
    # Mock compute_local_rtf to return a slow RTF (e.g., 1.5 > 0.7)
    with patch("praxis_ai_gateway.transcription.router.compute_local_rtf", return_value=1.5):
        transcriber = select_transcriber({}, settings)
        
        # Assert that the cloud transcriber is returned
        assert isinstance(transcriber, GroqCloudTranscriber)

def test_local_only_mode_forces_local_despite_slow_rtf():
    settings = {
        "LOCAL_ONLY_MODE": "true"
    }
    
    with patch("praxis_ai_gateway.transcription.router.compute_local_rtf", return_value=1.5):
        transcriber = select_transcriber({}, settings)
        
        # Assert that the local transcriber is returned even if RTF is bad
        assert isinstance(transcriber, FasterWhisperTranscriber)
