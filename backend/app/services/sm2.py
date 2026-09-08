from datetime import datetime, timedelta

def calculate_sm2(quality: int, repetitions: int, previous_interval: float, previous_ease_factor: float):
    """
    Computes the SuperMemo-2 (SM-2) algorithm for Spaced Repetition.
    
    :param quality: 0-5 rating (0 = complete blackout, 5 = perfect recall)
    :param repetitions: Number of times this item has been consecutively recalled (quality >= 3)
    :param previous_interval: Previous interval in days
    :param previous_ease_factor: Previous ease factor (default 2.5)
    :return: (new_interval, new_repetitions, new_ease_factor)
    """
    
    if quality < 0 or quality > 5:
        raise ValueError("Quality must be between 0 and 5.")
        
    # 1. Update Ease Factor
    new_ease_factor = previous_ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    new_ease_factor = max(1.3, new_ease_factor) # Minimum EF is 1.3
    
    # 2. Handle failure vs success
    if quality < 3:
        # Failure: reset repetitions and interval
        new_repetitions = 0
        new_interval = 1.0
    else:
        # Success: increment repetitions and calculate next interval
        new_repetitions = repetitions + 1
        
        if new_repetitions == 1:
            new_interval = 1.0
        elif new_repetitions == 2:
            new_interval = 6.0
        else:
            new_interval = previous_interval * new_ease_factor
            
    return round(new_interval, 2), new_repetitions, round(new_ease_factor, 3)
