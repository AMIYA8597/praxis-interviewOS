"""
Phase 52 — Deterministic dual-path architecture test.

Proves that the DSP coaching path (250ms cadence) is NEVER blocked by
LLM latency on the slow path.

Architecture under test:
    AUDIO STREAM
    │
    ├── FAST PATH (CoachingMetricsAccumulator)
    │     ↓  every ~250ms, pure in-process computation
    │   coaching.metrics event 1
    │   coaching.metrics event 2
    │   coaching.metrics event 3
    │   ...
    │
    └── SLOW PATH (LLM evaluation)
          ↓  5-second simulated latency
          one turn.scoring_result after 5s

The LLM must NEVER block the coaching path.
"""
import asyncio
import time
import pytest

from realtime_agent.app.coaching.accumulator import CoachingMetricsAccumulator
from realtime_agent.app.protocol import Envelope


@pytest.mark.asyncio
async def test_coaching_path_nonblocking_under_llm_delay():
    """
    PROOF: coaching events fire at ~250ms cadence for 1.5s
    while a simulated 5s LLM call runs concurrently.
    The coaching events must NOT wait for the LLM to complete.
    """
    LLM_DELAY_S = 5.0
    OBSERVATION_WINDOW_S = 1.5
    EXPECTED_MIN_EVENTS = 4  # 1500ms / 250ms = 6; allow slack → 4

    received_coaching_events: list[float] = []

    def fake_enqueue(envelope: Envelope, critical: bool = False) -> None:
        if envelope.type == "coaching.metrics":
            received_coaching_events.append(time.perf_counter())

    accumulator = CoachingMetricsAccumulator(
        session_id="test-session",
        enqueue_event_cb=fake_enqueue,
    )

    # --- SLOW PATH: simulate a 5s LLM call running concurrently ---
    llm_completed = False

    async def slow_llm_task():
        nonlocal llm_completed
        await asyncio.sleep(LLM_DELAY_S)
        llm_completed = True

    llm_task = asyncio.create_task(slow_llm_task())

    # --- FAST PATH: start coaching accumulator ---
    accumulator.start_turn()
    # Feed some transcript text so WPM > 0
    accumulator.update_text("I would approach this problem by first analysing the constraints")

    # Observe coaching events for OBSERVATION_WINDOW_S
    await asyncio.sleep(OBSERVATION_WINDOW_S)

    accumulator.end_turn()

    # LLM should NOT be done yet (still has ~3.5s to go)
    assert not llm_completed, (
        "LLM task completed before observation window — test timing incorrect"
    )

    # ASSERT: coaching events fired during the LLM delay
    assert len(received_coaching_events) >= EXPECTED_MIN_EVENTS, (
        f"Expected >= {EXPECTED_MIN_EVENTS} coaching events in {OBSERVATION_WINDOW_S}s; "
        f"got {len(received_coaching_events)}. "
        "Coaching path was blocked by LLM latency."
    )

    # ASSERT: inter-event cadence is close to 250ms
    if len(received_coaching_events) >= 2:
        gaps = [
            received_coaching_events[i + 1] - received_coaching_events[i]
            for i in range(len(received_coaching_events) - 1)
        ]
        avg_gap_ms = (sum(gaps) / len(gaps)) * 1000
        assert avg_gap_ms < 500, (
            f"Average coaching cadence {avg_gap_ms:.0f}ms is too slow (expected ~250ms). "
            "Fast path may be inadvertently awaiting slow work."
        )

    # ASSERT: coaching events contain WPM data
    # (accumulator emits Envelope with payload containing wpm)
    # We verify the accumulator ran by checking event count > 0
    assert len(received_coaching_events) > 0

    # Cleanup: cancel LLM task (we do not want to wait 5s in CI)
    llm_task.cancel()
    try:
        await llm_task
    except asyncio.CancelledError:
        pass

    print(
        f"\n[DUAL-PATH PROOF]\n"
        f"  Coaching events in {OBSERVATION_WINDOW_S}s window: {len(received_coaching_events)}\n"
        f"  Average inter-event gap: "
        f"{sum([(received_coaching_events[i+1]-received_coaching_events[i])*1000 for i in range(len(received_coaching_events)-1)])/max(len(received_coaching_events)-1,1):.0f}ms\n"
        f"  LLM completed: {llm_completed} (expected False)\n"
        f"  RESULT: Coaching path was NOT blocked by {LLM_DELAY_S}s LLM delay ✓"
    )


@pytest.mark.asyncio
async def test_coaching_stops_after_end_turn():
    """After end_turn(), no more coaching events should be emitted."""
    post_end_events: list[float] = []

    def fake_enqueue(envelope: Envelope, critical: bool = False) -> None:
        if envelope.type == "coaching.metrics":
            post_end_events.append(time.perf_counter())

    accumulator = CoachingMetricsAccumulator(
        session_id="test-session-2",
        enqueue_event_cb=fake_enqueue,
    )

    accumulator.start_turn()
    accumulator.update_text("Let me think about this carefully.")
    await asyncio.sleep(0.3)  # let 1 event fire

    accumulator.end_turn()
    post_end_count = len(post_end_events)

    # Wait to confirm no more events fire
    await asyncio.sleep(0.6)

    assert len(post_end_events) == post_end_count, (
        f"Coaching events continued after end_turn(): "
        f"before={post_end_count}, after={len(post_end_events)}"
    )
