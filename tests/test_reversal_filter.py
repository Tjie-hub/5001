"""Tests for screener.reversal_filter — EOD delta-reversal day-trade pre-scan.

The core is classify_reversal(): given yesterday vs today's order-flow delta,
the broker verdict, and where price sits inside its 30-day range, decide whether
a liquid stock is a LONG bounce, a SHORT fade, or no setup.

Reference case (BRPT, captured at Jun-9 EOD, played out Jun-10):
  prev_delta -506M  ->  today_delta +567M
  smart_money ACCUMULATION, verdict BULLISH
  ~32% below 30-day high (oversold), LQ45 member
  => LONG bounce.
"""
import sqlite3

import pytest

from screener.reversal_filter import (
    classify_reversal,
    scan_reversals,
    persist_watchlist,
)


# ── LONG bounce ────────────────────────────────────────────────────────────────

def test_brpt_style_flip_is_long_bounce():
    """Distribution -> accumulation on an oversold liquid name = long bounce."""
    sig = classify_reversal(
        prev_delta=-506_000_000,
        today_delta=+567_000_000,
        smart_money="ACCUMULATION",
        verdict="BULLISH",
        pct_below_30d_high=31.6,
        pct_above_30d_low=13.7,
        in_lq45=1,
        in_idx30=0,
    )
    assert sig is not None
    assert sig["direction"] == "long"
    assert 0 <= sig["conviction"] <= 100
    assert sig["reasons"]  # non-empty rationale


def test_emoji_verdict_is_normalized():
    """Broker verdict arrives as '🟢 BULLISH' — emoji/whitespace must not break it."""
    sig = classify_reversal(
        prev_delta=-200_000_000,
        today_delta=+150_000_000,
        smart_money="ACCUMULATION",
        verdict="🟢 BULLISH",
        pct_below_30d_high=20.0,
        pct_above_30d_low=10.0,
        in_lq45=1,
        in_idx30=0,
    )
    assert sig is not None
    assert sig["direction"] == "long"


# ── SHORT fade ───────────────────────────────────────────────────────────────────

def test_accumulation_to_distribution_is_short_fade():
    """Accumulation -> distribution on an overbought liquid name = short fade."""
    sig = classify_reversal(
        prev_delta=+400_000_000,
        today_delta=-350_000_000,
        smart_money="STRONG_SELL",
        verdict="BEARISH",
        pct_below_30d_high=5.0,
        pct_above_30d_low=40.0,
        in_lq45=1,
        in_idx30=1,
    )
    assert sig is not None
    assert sig["direction"] == "short"


# ── Rejections ───────────────────────────────────────────────────────────────────

def test_no_delta_flip_returns_none():
    """Both days accumulating — no reversal, no signal."""
    sig = classify_reversal(
        prev_delta=+100_000_000,
        today_delta=+200_000_000,
        smart_money="ACCUMULATION",
        verdict="BULLISH",
        pct_below_30d_high=20.0,
        pct_above_30d_low=10.0,
        in_lq45=1,
        in_idx30=0,
    )
    assert sig is None


def test_illiquid_stock_returns_none():
    """A perfect flip on a non-LQ45/non-IDX30 name is filtered out (not tradeable)."""
    sig = classify_reversal(
        prev_delta=-506_000_000,
        today_delta=+567_000_000,
        smart_money="ACCUMULATION",
        verdict="BULLISH",
        pct_below_30d_high=31.6,
        pct_above_30d_low=13.7,
        in_lq45=0,
        in_idx30=0,
    )
    assert sig is None


def test_long_flip_not_oversold_returns_none():
    """Delta flips up but price sits near its 30-day high — no bounce edge."""
    sig = classify_reversal(
        prev_delta=-300_000_000,
        today_delta=+250_000_000,
        smart_money="ACCUMULATION",
        verdict="BULLISH",
        pct_below_30d_high=4.0,   # only 4% below high — not oversold
        pct_above_30d_low=60.0,
        in_lq45=1,
        in_idx30=0,
    )
    assert sig is None


def test_long_flip_but_broker_still_bearish_returns_none():
    """Delta ticks up but smart money still reads STRONG_SELL — broker must confirm."""
    sig = classify_reversal(
        prev_delta=-300_000_000,
        today_delta=+50_000_000,
        smart_money="STRONG_SELL",
        verdict="BEARISH",
        pct_below_30d_high=25.0,
        pct_above_30d_low=10.0,
        in_lq45=1,
        in_idx30=0,
    )
    assert sig is None


# ── Conviction ordering ──────────────────────────────────────────────────────────

def test_idx30_strong_broker_outranks_weak_lq45():
    """Higher-quality confirmation should score higher conviction."""
    strong = classify_reversal(
        prev_delta=-500_000_000, today_delta=+500_000_000,
        smart_money="STRONG_BUY", verdict="BULLISH",
        pct_below_30d_high=35.0, pct_above_30d_low=10.0,
        in_lq45=1, in_idx30=1,
    )
    weak = classify_reversal(
        prev_delta=-100_000_000, today_delta=+20_000_000,
        smart_money="NEUTRAL", verdict="BULLISH",
        pct_below_30d_high=16.0, pct_above_30d_low=10.0,
        in_lq45=1, in_idx30=0,
    )
    assert strong is not None and weak is not None
    assert strong["conviction"] > weak["conviction"]


# ── Scan layer (DB-backed) ───────────────────────────────────────────────────────

def _seed_db():
    """In-memory DB with the four tables scan_reversals reads."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE daily_screen (date TEXT, ticker TEXT, close INTEGER, delta INTEGER);
        CREATE TABLE stockbit_flow (ticker TEXT, trade_date TEXT, smart_money TEXT, verdict TEXT, net_value INTEGER);
        CREATE TABLE idx_tickers (ticker TEXT, in_lq45 INTEGER, in_idx30 INTEGER, in_idx80 INTEGER);
        CREATE TABLE ohlcv (ticker TEXT, date TEXT, high REAL, low REAL, close REAL);
        """
    )
    # BRPT: distribution -> accumulation, oversold, LQ45  => LONG
    conn.executemany(
        "INSERT INTO daily_screen VALUES (?,?,?,?)",
        [
            ("2026-06-08", "BRPT", 1390, -506_000_000),
            ("2026-06-09", "BRPT", 1580, +567_000_000),
            # GUDG: same flip but illiquid => excluded
            ("2026-06-08", "GUDG", 800, -200_000_000),
            ("2026-06-09", "GUDG", 850, +180_000_000),
            # BBCA: no flip (both positive) => excluded
            ("2026-06-08", "BBCA", 5000, +100_000_000),
            ("2026-06-09", "BBCA", 5100, +200_000_000),
        ],
    )
    conn.executemany(
        "INSERT INTO stockbit_flow VALUES (?,?,?,?,?)",
        [
            ("BRPT", "2026-06-09", "ACCUMULATION", "🟢 BULLISH", 79_000_000_000),
            ("GUDG", "2026-06-09", "ACCUMULATION", "BULLISH", 5_000_000_000),
            ("BBCA", "2026-06-09", "NEUTRAL", "NEUTRAL", 1_000_000_000),
        ],
    )
    conn.executemany(
        "INSERT INTO idx_tickers VALUES (?,?,?,?)",
        [
            ("BRPT", 1, 0, 1),
            ("GUDG", 0, 0, 0),
            ("BBCA", 1, 1, 1),
        ],
    )
    # 30-day OHLCV extremes: BRPT high 2310 / low 1375 -> 31.6% below high (oversold)
    ohlcv_rows = [("BRPT", "2026-05-12", 2310, 1375, 2000),
                  ("BRPT", "2026-06-09", 1600, 1375, 1580),
                  ("GUDG", "2026-05-12", 1200, 700, 1000),
                  ("GUDG", "2026-06-09", 900, 700, 850),
                  ("BBCA", "2026-05-12", 5200, 4900, 5000),
                  ("BBCA", "2026-06-09", 5150, 4900, 5100)]
    conn.executemany("INSERT INTO ohlcv VALUES (?,?,?,?,?)", ohlcv_rows)
    conn.commit()
    return conn


def test_scan_flags_brpt_long_and_excludes_others():
    conn = _seed_db()
    results = scan_reversals(conn, "2026-06-09")
    tickers = {r["ticker"] for r in results}
    assert "BRPT" in tickers          # qualified long bounce
    assert "GUDG" not in tickers       # illiquid
    assert "BBCA" not in tickers       # no delta flip
    brpt = next(r for r in results if r["ticker"] == "BRPT")
    assert brpt["direction"] == "long"
    assert brpt["close"] == 1580


def test_scan_sorts_by_conviction_desc():
    conn = _seed_db()
    results = scan_reversals(conn, "2026-06-09")
    convs = [r["conviction"] for r in results]
    assert convs == sorted(convs, reverse=True)


def test_persist_watchlist_writes_rows():
    conn = _seed_db()
    results = scan_reversals(conn, "2026-06-09")
    n = persist_watchlist(conn, "2026-06-09", results)
    assert n == len(results)
    stored = conn.execute(
        "SELECT ticker, direction FROM reversal_watchlist WHERE scan_date=?",
        ("2026-06-09",),
    ).fetchall()
    assert {row["ticker"] for row in stored} == {r["ticker"] for r in results}
    assert any(row["direction"] == "long" for row in stored)


def test_persist_watchlist_is_idempotent():
    """Re-running the same EOD scan replaces, never duplicates."""
    conn = _seed_db()
    results = scan_reversals(conn, "2026-06-09")
    persist_watchlist(conn, "2026-06-09", results)
    persist_watchlist(conn, "2026-06-09", results)
    count = conn.execute(
        "SELECT COUNT(*) FROM reversal_watchlist WHERE scan_date=?", ("2026-06-09",)
    ).fetchone()[0]
    assert count == len(results)
