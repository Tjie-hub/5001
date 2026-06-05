# engine/circuit_breaker.py
"""Auto circuit breaker for market risk (C9).

OPEN  → auto-trading paused; only CRITICAL tier triggers this.
CLOSED → trading allowed.

Design: fail-open (CLOSED) on missing/malformed input so infra errors
don't accidentally halt all trading.
"""
from enum import Enum


class CircuitBreakerState(Enum):
    OPEN = "OPEN"      # trading paused
    CLOSED = "CLOSED"  # trading allowed


def check_circuit_breaker(risk_result: dict) -> tuple:
    """Return (CircuitBreakerState, reason_str).

    Only CRITICAL tier opens the breaker. All other tiers or bad input
    return CLOSED (fail-open).
    """
    try:
        tier = risk_result.get('tier', '')
        score = risk_result.get('score', 0.0)
        if tier == 'CRITICAL':
            return (
                CircuitBreakerState.OPEN,
                f"Market risk CRITICAL (score={score:.1f}) — auto-trading paused",
            )
        return CircuitBreakerState.CLOSED, "OK"
    except Exception:
        return CircuitBreakerState.CLOSED, "OK (fail-open)"
