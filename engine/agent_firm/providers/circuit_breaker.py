"""Per-provider circuit breaker (design doc §3). One instance per provider,
owned by the Router, in-memory only (single-process app).

allow_request() has no `await` inside it, so Python's cooperative
scheduling makes the whole check-and-flip-state sequence atomic with
respect to other coroutines — that's what actually guarantees only one
HALF_OPEN trial is in flight at a time, without needing a real lock object.
"""

import time
from typing import Literal


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 3, cooldown_s: float = 30.0):
        self.consecutive_failures = 0
        self.last_failure: float | None = None  # time.monotonic() timestamp
        self.state: Literal["CLOSED", "OPEN", "HALF_OPEN"] = "CLOSED"
        self.failure_threshold = failure_threshold
        self.cooldown_s = cooldown_s
        self._trial_in_flight = False

    def allow_request(self) -> bool:
        if self.state == "CLOSED":
            return True
        if self.state == "OPEN":
            if self.last_failure is not None and \
               time.monotonic() - self.last_failure >= self.cooldown_s:
                self.state = "HALF_OPEN"
            else:
                return False
        # HALF_OPEN: allow exactly one trial through
        if self._trial_in_flight:
            return False
        self._trial_in_flight = True
        return True

    def record_success(self) -> bool:
        """Returns True if this success just closed a previously OPEN/HALF_OPEN circuit."""
        was_open = self.state != "CLOSED"
        self.consecutive_failures = 0
        self.last_failure = None
        self._trial_in_flight = False
        self.state = "CLOSED"
        return was_open

    def record_failure(self) -> bool:
        """Returns True if this failure just caused a fresh transition to OPEN."""
        was_open = self.state == "OPEN"
        self.consecutive_failures += 1
        self.last_failure = time.monotonic()
        self._trial_in_flight = False
        if self.consecutive_failures >= self.failure_threshold or self.state == "HALF_OPEN":
            self.state = "OPEN"
        return self.state == "OPEN" and not was_open

    def release_trial(self) -> None:
        """Call when a HALF_OPEN trial slot was acquired via allow_request()
        but the caller decided not to actually attempt generate() (e.g. the
        daily call cap was hit) — frees the slot for a future retry."""
        self._trial_in_flight = False
