class ProsodyExtractor:
    """
    Extracts prosodic features locally without an LLM.
    """
    def __init__(self):
        self.word_count = 0
        self.filler_count = 0
        self.start_time = None
        self.pauses = []

    def process_transcript(self, transcript: str):
        words = transcript.lower().split()
        if not words:
            return
            
        self.word_count += len(words)
        
        # Simple filler token detection
        fillers = {"um", "uh", "like", "you know"}
        for word in words:
            if word in fillers:
                self.filler_count += 1
                
    def get_metrics(self) -> dict:
        # Calculate WPM assuming process_transcript is called roughly per turn
        # For this stub, we return placeholder values based on counters
        wpm = min(150, max(80, self.word_count * 10))  # Simulated calculation
        filler_rate = (self.filler_count / max(1, self.word_count)) * 100
        
        return {
            "wpm": wpm,
            "filler_rate_percent": round(filler_rate, 2),
            "pause_distribution": "normal"
        }
