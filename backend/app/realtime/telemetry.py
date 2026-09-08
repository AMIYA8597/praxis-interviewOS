import time

class TelemetryTracker:
    def __init__(self):
        self.events = {}
        
    def mark(self, event_name: str, ts: float = None):
        if ts is None:
            ts = time.time()
        self.events[event_name] = ts
        
    def compute_deltas(self) -> dict:
        deltas = {}
        if "capture_ts" in self.events and "ingest_ts" in self.events:
            deltas["mic_to_ingest"] = (self.events["ingest_ts"] - self.events["capture_ts"]) * 1000
            
        if "vad_start_ts" in self.events and "audio_stop_ts" in self.events:
            deltas["barge_in_to_silent"] = (self.events["audio_stop_ts"] - self.events["vad_start_ts"]) * 1000
            
        if "chunk_ts" in self.events and "stt_partial_ts" in self.events:
            deltas["chunk_to_partial"] = (self.events["stt_partial_ts"] - self.events["chunk_ts"]) * 1000
            
        if "stt_final_ts" in self.events and "classify_ts" in self.events:
            deltas["final_to_classify"] = (self.events["classify_ts"] - self.events["stt_final_ts"]) * 1000
            
        if "classify_ts" in self.events and "retrieve_ts" in self.events:
            deltas["classify_to_retrieve"] = (self.events["retrieve_ts"] - self.events["classify_ts"]) * 1000
            
        if "stt_final_ts" in self.events and "tts_first_audio_ts" in self.events:
            deltas["end_to_end_turnaround"] = (self.events["tts_first_audio_ts"] - self.events["stt_final_ts"]) * 1000
            
        return deltas
