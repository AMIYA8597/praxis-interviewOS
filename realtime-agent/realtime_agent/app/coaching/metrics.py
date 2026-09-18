import re
import yaml
import os
from typing import List, Set, Dict, Any

def load_coaching_config() -> Dict[str, Set[str]]:
    config_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "config", "coaching.yaml")
    try:
        with open(config_path, "r") as f:
            data = yaml.safe_load(f)
            return {
                "fillers": set(data.get("fillers", [])),
                "hedges": set(data.get("hedges", []))
            }
    except Exception:
        return {"fillers": {"um", "uh", "like", "you know"}, "hedges": {"i think", "maybe"}}

def compute_wpm(word_count: int, duration_ms: int) -> float:
    """Computes words per minute. Returns 0.0 if duration is 0."""
    if duration_ms <= 0:
        return 0.0
    minutes = duration_ms / 60000.0
    return word_count / minutes

def tokenize_text(text: str) -> List[str]:
    """Simple whitespace and punctuation tokenizer."""
    text = text.lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    return text.split()

def compute_filler_rate(text: str, filler_list: Set[str]) -> Dict[str, Any]:
    text_lower = text.lower()
    breakdown = {filler: 0 for filler in filler_list}
    total = 0
    padded_text = f" {re.sub(r'[^\w\s]', ' ', text_lower)} "
    for filler in filler_list:
        count = padded_text.count(f" {filler} ")
        if count > 0:
            breakdown[filler] = count
            total += count
    return {"total": total, "breakdown": {k: v for k, v in breakdown.items() if v > 0}}

def compute_pause_stats(vad_silence_gaps: List[int], turn_duration_ms: int) -> Dict[str, Any]:
    count = len(vad_silence_gaps)
    longest = max(vad_silence_gaps) if count > 0 else 0
    total_silence = sum(vad_silence_gaps)
    ratio = (total_silence / turn_duration_ms) if turn_duration_ms > 0 else 0.0
    return {
        "count": count,
        "longest_pause_ms": longest,
        "pause_ratio": ratio
    }

def compute_hedge_count(text: str, hedge_list: Set[str]) -> int:
    text_lower = text.lower()
    padded_text = f" {re.sub(r'[^\w\s]', ' ', text_lower)} "
    count = 0
    for hedge in hedge_list:
        count += padded_text.count(f" {hedge} ")
    return count

def compute_time_to_first_word(question_end_ts: float, first_word_ts: float) -> float:
    if question_end_ts <= 0 or first_word_ts <= 0:
        return 0.0
    diff = first_word_ts - question_end_ts
    return max(0.0, diff * 1000.0)
