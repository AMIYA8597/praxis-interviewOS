import pytest
import asyncio
from unittest.mock import MagicMock
from realtime_agent.app.coaching.accumulator import CoachingMetricsAccumulator

@pytest.mark.asyncio
async def test_accumulator_cadence():
    mock_enqueue = MagicMock()
    acc = CoachingMetricsAccumulator("test-session", mock_enqueue)
    
    # Start turn
    acc.start_turn()
    acc.update_text("This is a test um uh sentence.")
    
    # Wait for the 250ms cadence to fire at least once
    await asyncio.sleep(0.3)
    
    # It should have fired at least once
    assert mock_enqueue.call_count >= 1
    call_args = mock_enqueue.call_args[0]
    envelope = call_args[0]
    
    assert envelope.type == "coaching.metrics"
    assert envelope.payload["hedges"] == 0
    assert envelope.payload["wpm"] > 0
    
    # Record current call count
    calls_before_end = mock_enqueue.call_count
    
    # End turn
    acc.end_turn()
    
    # Wait another 300ms
    await asyncio.sleep(0.3)
    
    # Should not have fired again since it was ended
    assert mock_enqueue.call_count == calls_before_end

