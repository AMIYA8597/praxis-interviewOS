import logging
import time

logger = logging.getLogger(__name__)

class TurnDetector:
    def __init__(self, silence_threshold_ms: int = 550):
        self.silence_threshold_ms = silence_threshold_ms
        self.is_speaking = False
        self.last_speech_time = 0
        self.interviewer_speaking = False
        self.cancellation_token = None

    def process_vad_confidence(self, confidence: float, timestamp_ms: int) -> bool:
        """
        Evaluates speech energy to detect End-of-Turn or Barge-In events.
        Returns True if a barge-in is triggered.
        """
        barge_in_triggered = False
        
        if confidence > 0.5:
            if not self.is_speaking:
                self.is_speaking = True
                logger.info(f"Speech STARTED at {timestamp_ms}")
                
                # BARGE-IN LOGIC
                if self.interviewer_speaking:
                    barge_in_triggered = True
                    self.interviewer_speaking = False
                    if self.cancellation_token:
                        logger.warning(f"Aborting generation token: {self.cancellation_token}")
                        self.cancellation_token = None
                        
            self.last_speech_time = timestamp_ms
        else:
            if self.is_speaking and (timestamp_ms - self.last_speech_time > self.silence_threshold_ms):
                self.is_speaking = False
                logger.info(f"Speech ENDED at {timestamp_ms}. Verifying semantic completeness...")
                # Here we would invoke the fast_classify gateway alias (timeout 150ms)
                
        return barge_in_triggered

    def set_interviewer_speaking(self, token: str):
        self.interviewer_speaking = True
        self.cancellation_token = token
