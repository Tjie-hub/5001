"""Tests for rank_bear_watchlist_and_notify().

REMOVED 2026-09-15: this ranking called the firm on up to 20 tickers per scan
cycle, outside the strict 2-invocations-per-trading-day contract
(engine.agent_firm_daily). It is now a pure no-op kept only so the
scheduled_multi_strategy_scan() call site needs no change — these tests
prove exactly that, and that it never imports or calls the firm.
"""
import sys

from scheduler.scanner import rank_bear_watchlist_and_notify


def test_ranking_is_a_noop_for_a_nonempty_watchlist():
    assert rank_bear_watchlist_and_notify(["BBCA", "BBRI"], "2026-06-05", "10:00") is None


def test_ranking_is_a_noop_for_an_empty_watchlist():
    assert rank_bear_watchlist_and_notify([], "2026-06-05", "10:00") is None


def test_ranking_never_sends_telegram(monkeypatch):
    sent = []
    monkeypatch.setattr("scheduler.scanner.send_telegram", sent.append)
    rank_bear_watchlist_and_notify(["BBCA"], "2026-06-05", "10:00")
    assert sent == []


def test_ranking_never_imports_or_touches_the_firm_module(monkeypatch):
    """A None entry in sys.modules makes any `from engine.agent_firm import
    firm` raise ImportError — proving the new body never even attempts it."""
    monkeypatch.setitem(sys.modules, "engine.agent_firm.firm", None)
    rank_bear_watchlist_and_notify(["BBCA"], "2026-06-05", "10:00")  # must not raise
