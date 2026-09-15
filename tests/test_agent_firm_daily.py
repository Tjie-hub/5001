"""Tests for engine.agent_firm_daily — the strict 2-LLM-invocations-per-day contract.

Two runs per IDX trading day, both covering the SAME up-to-3 selected tickers:
  post_close  -- creates the next-session trade plan
  premarket   -- adjusts that plan using overnight information

This module owns: ticker-set capping (reusing engine.trade_plan.select_top),
next-trading-session lookup, the retry-safe once-per-(session_date, run_type)
billing guard, and the plan store premarket reads from.
"""
import sqlite3
from datetime import date

import pytest

import engine.agent_firm_daily as afd


# ── next_trading_session ──────────────────────────────────────────────────────

def test_next_trading_session_skips_non_trading_days(monkeypatch):
    """Friday -> Monday when Sat/Sun are non-trading days."""
    trading = {date(2026, 9, 18): True,   # Fri
               date(2026, 9, 19): False,  # Sat
               date(2026, 9, 20): False,  # Sun
               date(2026, 9, 21): True}   # Mon
    monkeypatch.setattr("engine.calendar_filter.is_trading_day",
                        lambda d=None: (trading.get(d, True), ""))
    assert afd.next_trading_session(date(2026, 9, 18)) == date(2026, 9, 21)


def test_next_trading_session_raises_if_none_found_in_window(monkeypatch):
    monkeypatch.setattr("engine.calendar_filter.is_trading_day", lambda d=None: (False, "closed"))
    with pytest.raises(RuntimeError):
        afd.next_trading_session(date(2026, 9, 18))


# ── select_daily_tickers ──────────────────────────────────────────────────────

def _cand(ticker, conviction):
    return {"ticker": ticker, "conviction": conviction, "net_value": 0,
            "sources": ["R"], "confluence": 1, "vol_ratio": 1.0, "reason": ""}


def test_select_daily_tickers_caps_at_three():
    cands = [_cand(f"TK{i}", i) for i in range(5)]
    picked = afd.select_daily_tickers(cands)
    assert len(picked) == 3
    assert [c["ticker"] for c in picked] == ["TK4", "TK3", "TK2"]  # highest conviction first


@pytest.mark.parametrize("n", [2, 1, 0])
def test_select_daily_tickers_returns_fewer_when_available(n):
    cands = [_cand(f"TK{i}", i) for i in range(n)]
    picked = afd.select_daily_tickers(cands)
    assert len(picked) == n


# ── begin_run / finish_run guard ──────────────────────────────────────────────

@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    yield c
    c.close()


def test_begin_run_first_call_allows_and_records_attempt_one(conn):
    guard = afd.begin_run(conn, "2026-09-16", afd.RUN_POST_CLOSE, ["BBCA"])
    assert guard.should_call is True
    assert guard.attempt == 1
    row = conn.execute(
        "SELECT status, attempt, tickers FROM agent_firm_daily_run WHERE id=?",
        (guard.run_id,)).fetchone()
    assert row[0] == "in_progress"
    assert row[1] == 1
    assert "BBCA" in row[2]


def test_begin_run_blocks_duplicate_after_success(conn):
    guard1 = afd.begin_run(conn, "2026-09-16", afd.RUN_POST_CLOSE, ["BBCA"])
    afd.finish_run(conn, guard1.run_id, status="success", provider="zai", reason="ok")

    guard2 = afd.begin_run(conn, "2026-09-16", afd.RUN_POST_CLOSE, ["BBCA"])
    assert guard2.should_call is False
    assert guard2.reason == "already_succeeded"


def test_begin_run_allows_retry_after_failure_with_incremented_attempt(conn):
    guard1 = afd.begin_run(conn, "2026-09-16", afd.RUN_POST_CLOSE, ["BBCA"])
    afd.finish_run(conn, guard1.run_id, status="failed", reason="provider timeout")

    guard2 = afd.begin_run(conn, "2026-09-16", afd.RUN_POST_CLOSE, ["BBCA"])
    assert guard2.should_call is True
    assert guard2.attempt == 2


def test_begin_run_is_independent_per_run_type(conn):
    """A successful post_close run must not block that same day's premarket run."""
    guard1 = afd.begin_run(conn, "2026-09-16", afd.RUN_POST_CLOSE, ["BBCA"])
    afd.finish_run(conn, guard1.run_id, status="success")

    guard2 = afd.begin_run(conn, "2026-09-16", afd.RUN_PREMARKET, ["BBCA"])
    assert guard2.should_call is True


def test_begin_run_is_independent_per_session_date(conn):
    guard1 = afd.begin_run(conn, "2026-09-16", afd.RUN_POST_CLOSE, ["BBCA"])
    afd.finish_run(conn, guard1.run_id, status="success")

    guard2 = afd.begin_run(conn, "2026-09-17", afd.RUN_POST_CLOSE, ["BBCA"])
    assert guard2.should_call is True


# ── persist_plan / load_plan ───────────────────────────────────────────────────

class _FakeDecision:
    def __init__(self, ticker, decision, confidence=None, size_tier=None, rationale=None):
        self.ticker = ticker
        self.decision = decision
        self.confidence = confidence
        self.size_tier = size_tier
        self.rationale = rationale


def test_persist_and_load_plan_roundtrip(conn):
    rows = [{"ticker": "BBCA"}, {"ticker": "BBRI"}]
    decisions = [
        _FakeDecision("BBCA", "approve", confidence=0.8, size_tier="normal", rationale="r1"),
        _FakeDecision("BBRI", "veto", confidence=0.2, rationale="r2"),
    ]
    afd.persist_plan(conn, "2026-09-16", rows, decisions, source=afd.RUN_POST_CLOSE)

    plan = afd.load_plan(conn, "2026-09-16")
    assert [p["ticker"] for p in plan] == ["BBCA", "BBRI"]
    assert plan[0]["rank"] == 1
    assert plan[0]["decision"] == "approve"
    assert plan[0]["source"] == afd.RUN_POST_CLOSE
    assert plan[1]["decision"] == "veto"


def test_persist_plan_upsert_updates_existing_row(conn):
    rows = [{"ticker": "BBCA"}]
    afd.persist_plan(conn, "2026-09-16", rows,
                     [_FakeDecision("BBCA", "approve", confidence=0.7)],
                     source=afd.RUN_POST_CLOSE)
    afd.persist_plan(conn, "2026-09-16", rows,
                     [_FakeDecision("BBCA", "approve", confidence=0.9)],
                     source=afd.RUN_PREMARKET)

    plan = afd.load_plan(conn, "2026-09-16")
    assert len(plan) == 1
    assert plan[0]["confidence"] == 0.9
    assert plan[0]["source"] == afd.RUN_PREMARKET


def test_load_plan_empty_when_no_rows(conn):
    assert afd.load_plan(conn, "2026-09-16") == []
