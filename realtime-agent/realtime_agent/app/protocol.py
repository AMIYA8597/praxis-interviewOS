from typing import Any, Dict, Literal
from pydantic import BaseModel, Field
from datetime import datetime, timezone

class Envelope(BaseModel):
    version: Literal["1"] = "1"
    type: Literal[
        "session.ready",
        "session.error",
        "audio.frame_ack",
        "state.transitioned",
        "provider.changed",
        "session.degraded",
        "session.stopped",
        "audio.stop_playback",
        "coaching.metrics",
        "transcript.partial",
        "transcript.final",
        "speech_start",
        "speech_end"
    ]
    session_id: str
    sequence: int
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    payload: Dict[str, Any]
