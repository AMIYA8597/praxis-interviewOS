import pytest
import asyncio
from realtime_agent.audio.vad_engine import VADBuffer
from realtime_agent.audio.coaching_metrics import PauseAnalyzer

@pytest.mark.asyncio
async def test_pause_analyzer():
    vad_buffer = VADBuffer()
    analyzer = PauseAnalyzer(min_pause_ms=200)
    
    # Simulate speech
    await vad_buffer.push({"is_speech": True, "timestamp": 100.0})
    await vad_buffer.push({"is_speech": True, "timestamp": 100.1})
    
    # Simulate a pause of 300ms (from 100.1 to 100.4)
    await vad_buffer.push({"is_speech": False, "timestamp": 100.1})
    await vad_buffer.push({"is_speech": False, "timestamp": 100.2})
    await vad_buffer.push({"is_speech": False, "timestamp": 100.3})
    
    # Resume speech at 100.4
    await vad_buffer.push({"is_speech": True, "timestamp": 100.4})
    
    # Simulate a shorter pause of 100ms (from 100.5 to 100.6) - should not be counted
    await vad_buffer.push({"is_speech": False, "timestamp": 100.5})
    
    # Resume speech at 100.6
    await vad_buffer.push({"is_speech": True, "timestamp": 100.6})
    
    metrics = await analyzer.analyze_vad_stream(vad_buffer)
    
    # The pause was 100.4 - 100.1 = 0.3s = 300ms
    assert metrics["pause_count"] == 1
    assert 290 <= metrics["avg_pause_ms"] <= 310
    assert 290 <= metrics["max_pause_ms"] <= 310
