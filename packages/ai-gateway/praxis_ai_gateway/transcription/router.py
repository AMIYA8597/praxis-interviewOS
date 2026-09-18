import os
import time
import numpy as np
import logging
from typing import Dict, Any

from .protocol import RealtimeTranscriber
from .local_faster_whisper import FasterWhisperTranscriber
from .cloud_groq import GroqCloudTranscriber

logger = logging.getLogger(__name__)

def compute_local_rtf() -> float:
    """
    Measures the Real-Time Factor (RTF) of the local faster-whisper model.
    A 2-second dummy audio chunk is transcribed to measure wall-clock latency.
    """
    logger.info("Measuring local STT Real-Time Factor (RTF)...")
    
    # 2 seconds of 16kHz audio
    duration_sec = 2.0
    num_samples = int(16000 * duration_sec)
    fake_audio = np.random.randint(-32768, 32767, num_samples, dtype=np.int16).tobytes()
    
    transcriber = FasterWhisperTranscriber()
    
    start_t = time.perf_counter()
    # Synchronously run the private method for benchmarking purposes
    _ = transcriber._run_faster_whisper(fake_audio)
    end_t = time.perf_counter()
    
    processing_time = end_t - start_t
    rtf = processing_time / duration_sec
    logger.info(f"Local STT RTF: {rtf:.3f} (Processed {duration_sec}s of audio in {processing_time:.3f}s)")
    
    return rtf

def select_transcriber(hardware_profile: Dict[str, Any], settings: Dict[str, Any], enqueue_event_cb=None) -> RealtimeTranscriber:
    local_only = settings.get("LOCAL_ONLY_MODE", "true").lower() == "true"
    groq_key = os.environ.get("GROQ_API_KEY")
    
    # Check if Groq is preferred/configured
    # In an actual deployment, this preference might come from user settings.
    # We always benchmark local RTF to make the safety check.
    try:
        local_rtf = compute_local_rtf()
    except Exception as e:
        logger.error(f"Failed to measure local RTF: {e}")
        local_rtf = 999.0  # assume unacceptably slow if failing
        
    rtf_safety_threshold = 0.7
    
    if local_rtf > rtf_safety_threshold:
        msg = f"Local transcription is running slower than real-time on this hardware (RTF {local_rtf:.2f} > {rtf_safety_threshold}). Configure a cloud STT provider in Settings for better performance."
        logger.warning(msg)
        if enqueue_event_cb:
            from realtime_agent.app.protocol import Envelope
            evt = Envelope(
                type="system.alert",
                session_id="",
                sequence=0,
                payload={"message": msg, "severity": "warning"}
            )
            enqueue_event_cb(evt)
            
        if not local_only and groq_key:
            logger.info("Routing to cloud_groq STT due to high local RTF.")
            return GroqCloudTranscriber()
        else:
            logger.warning("Forced to use local STT despite high RTF due to LOCAL_ONLY_MODE or missing API key.")
            return FasterWhisperTranscriber()
    else:
        logger.info(f"Local STT is sufficiently fast (RTF {local_rtf:.2f}). Using local_faster_whisper.")
        return FasterWhisperTranscriber()
