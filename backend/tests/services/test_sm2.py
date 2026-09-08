import pytest
from app.services.sm2 import calculate_sm2

def test_sm2_perfect_recall():
    """
    Validates SM-2 interval expansion for perfect recall (quality = 5).
    """
    # First repetition
    interval, reps, ef = calculate_sm2(quality=5, repetitions=0, previous_interval=1.0, previous_ease_factor=2.5)
    assert interval == 1.0
    assert reps == 1
    assert ef == 2.6 # 2.5 + (0.1 - (0)*(...)) = 2.6
    
    # Second repetition
    interval, reps, ef = calculate_sm2(quality=5, repetitions=reps, previous_interval=interval, previous_ease_factor=ef)
    assert interval == 6.0
    assert reps == 2
    assert ef == 2.7
    
    # Third repetition
    interval, reps, ef = calculate_sm2(quality=5, repetitions=reps, previous_interval=interval, previous_ease_factor=ef)
    assert interval == round(6.0 * 2.8, 2) # 16.8
    assert reps == 3
    assert ef == 2.8

def test_sm2_failure_reset():
    """
    Validates that a quality rating < 3 resets the interval to 1 day.
    """
    interval, reps, ef = calculate_sm2(quality=2, repetitions=5, previous_interval=30.0, previous_ease_factor=2.5)
    assert interval == 1.0
    assert reps == 0
    # EF drops due to failure
    assert ef < 2.5
