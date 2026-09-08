import os
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"

class CircuitBreaker:
    """
    Per-provider, per-capability circuit breaker.
    """
    def __init__(self, failure_threshold=3):
        self.state = CircuitState.CLOSED
        self.failures = 0
        self.failure_threshold = failure_threshold

    def record_failure(self):
        self.failures += 1
        if self.failures >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning("Circuit breaker OPENED.")

    def record_success(self):
        self.failures = 0
        if self.state != CircuitState.CLOSED:
            logger.info("Circuit breaker CLOSED (recovered).")
        self.state = CircuitState.CLOSED

    def can_execute(self) -> bool:
        return self.state != CircuitState.OPEN
