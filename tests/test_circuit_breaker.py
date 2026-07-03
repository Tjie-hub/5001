"""Tests for C9 — auto circuit breaker.

When market risk = CRITICAL, auto-trading is paused automatically.
Hooks into premover auto-execution via check_circuit_breaker gate.
"""
from unittest.mock import patch, MagicMock

from engine.circuit_breaker import check_circuit_breaker, CircuitBreakerState


# ── State constants ───────────────────────────────────────────────────────────

def test_state_has_open_and_closed():
    assert hasattr(CircuitBreakerState, 'OPEN')
    assert hasattr(CircuitBreakerState, 'CLOSED')


# ── check_circuit_breaker ─────────────────────────────────────────────────────

def test_critical_risk_triggers_circuit_breaker():
    """CRITICAL risk tier → OPEN."""
    state, reason = check_circuit_breaker({'tier': 'CRITICAL', 'score': 92.0})
    assert state == CircuitBreakerState.OPEN
    assert 'CRITICAL' in reason


def test_red_risk_does_not_trigger():
    state, reason = check_circuit_breaker({'tier': 'RED', 'score': 78.0})
    assert state == CircuitBreakerState.CLOSED


def test_green_risk_does_not_trigger():
    state, reason = check_circuit_breaker({'tier': 'GREEN', 'score': 15.0})
    assert state == CircuitBreakerState.CLOSED


def test_orange_risk_does_not_trigger():
    state, reason = check_circuit_breaker({'tier': 'ORANGE', 'score': 62.0})
    assert state == CircuitBreakerState.CLOSED


def test_reason_is_nonempty_string():
    _, reason = check_circuit_breaker({'tier': 'CRITICAL', 'score': 95.0})
    assert isinstance(reason, str) and len(reason) > 0


def test_missing_tier_defaults_to_closed():
    """Malformed input → fail-open (CLOSED), don't block trading by default."""
    state, _ = check_circuit_breaker({})
    assert state == CircuitBreakerState.CLOSED


# ── run_premover_eod integration gate ────────────────────────────────────────

def test_run_premover_eod_skips_trades_when_breaker_open(capsys):
    """run_premover_eod should not open trades when circuit breaker is OPEN."""
    from scheduler.jobs import run_premover_eod

    # Bypass the holiday/weekend gate so this exercises the breaker branch
    # regardless of the calendar date the suite runs on (was failing every
    # weekend: run_premover_eod short-circuits on _holiday_skip before the
    # circuit-breaker logic).
    with patch('scheduler.jobs._holiday_skip', return_value=False), \
         patch('scheduler.jobs.get_market_risk_for_circuit_breaker',
               return_value={'tier': 'CRITICAL', 'score': 92.0}), \
         patch('scheduler.jobs.send_telegram', MagicMock()), \
         patch('paper_trade.get_premover_mode', return_value='auto'):
        run_premover_eod()

    out = capsys.readouterr().out
    assert 'circuit' in out.lower() or 'CRITICAL' in out or 'breaker' in out.lower()


def test_run_premover_eod_proceeds_when_breaker_closed(capsys):
    """run_premover_eod should attempt scans when circuit breaker is CLOSED."""
    from scheduler.jobs import run_premover_eod

    with patch('scheduler.jobs.get_market_risk_for_circuit_breaker',
               return_value={'tier': 'GREEN', 'score': 15.0}), \
         patch('scheduler.jobs.send_telegram', MagicMock()), \
         patch('engine.premover_detector.run_scan', return_value=[]), \
         patch('paper_trade.get_premover_mode', return_value='shadow'):
        run_premover_eod()

    out = capsys.readouterr().out
    # Circuit breaker must NOT have blocked the scan
    assert 'Circuit breaker OPEN' not in out
