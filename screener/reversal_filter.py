"""
reversal_filter.py — EOD delta-reversal pre-scan for liquid day trades
======================================================================
Anticipate next-day bounce/fade setups on LQ45 / IDX30 names *the evening
before*, using signals already present at today's close:

  LONG  bounce : order-flow delta flips negative -> positive,
                 broker flips to ACCUMULATION / BULLISH,
                 price is oversold (>= 15% below its 30-day high).
  SHORT fade   : delta flips positive -> negative,
                 broker flips to STRONG_SELL / BEARISH,
                 price is extended (>= 15% above its 30-day low).

Reference: BRPT at Jun-9 EOD (delta -506M -> +567M, ACCUMULATION, ~32% below
30d high, LQ45) flagged the +16% Jun-10 bounce a day early.

Usage:
    python -m screener.reversal_filter                 # table, latest EOD
    python -m screener.reversal_filter --date 2026-06-09
    python -m screener.reversal_filter --json
    python -m screener.reversal_filter --direction long
"""
from __future__ import annotations

import os
import re
import sys
import json
import sqlite3
import argparse
from typing import Optional

# ── Paths ──────────────────────────────────────────────────────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT = os.path.dirname(_HERE)
_DB_PATH = os.path.join(_PROJECT, "data", "walkforward.db")

# ── Tunables ───────────────────────────────────────────────────────────────────
OVERSOLD_PCT = 15.0          # min distance from 30d extreme to qualify
MIN_DELTA_FLIP = 0.0         # delta must cross zero (sign flip)

_BULLISH_SMART = {"ACCUMULATION", "STRONG_BUY"}
_BEARISH_SMART = {"STRONG_SELL", "MORNING_TRAP", "DISTRIBUTION"}


def _norm(text: Optional[str]) -> str:
    """Uppercase alpha-only token — strips emoji, whitespace, punctuation."""
    if not text:
        return ""
    return re.sub(r"[^A-Za-z]", "", text).upper()


def _broker_bullish(smart_money: Optional[str], verdict: Optional[str]) -> bool:
    sm = _norm(smart_money)
    if sm in _BEARISH_SMART:
        return False
    return sm in _BULLISH_SMART or _norm(verdict) == "BULLISH"


def _broker_bearish(smart_money: Optional[str], verdict: Optional[str]) -> bool:
    sm = _norm(smart_money)
    if sm in _BULLISH_SMART:
        return False
    return sm in _BEARISH_SMART or _norm(verdict) == "BEARISH"


def classify_reversal(
    prev_delta: float,
    today_delta: float,
    smart_money: Optional[str],
    verdict: Optional[str],
    pct_below_30d_high: float,
    pct_above_30d_low: float,
    in_lq45: int,
    in_idx30: int,
    oversold_pct: float = OVERSOLD_PCT,
) -> Optional[dict]:
    """Classify a single ticker's EOD state as a long/short reversal setup.

    Returns {"direction", "conviction", "reasons"} or None when no setup.
    """
    # Mandatory: must be liquid enough to trade in and out cleanly.
    if not (in_lq45 or in_idx30):
        return None

    prev_delta = prev_delta or 0.0
    today_delta = today_delta or 0.0

    # ── LONG bounce: delta flips up, broker bullish, oversold ──
    if prev_delta < 0 < today_delta and _broker_bullish(smart_money, verdict):
        if pct_below_30d_high >= oversold_pct:
            return _build("long", smart_money, _BULLISH_SMART,
                          extreme_pct=pct_below_30d_high, oversold_pct=oversold_pct,
                          in_idx30=in_idx30, prev_delta=prev_delta, today_delta=today_delta)

    # ── SHORT fade: delta flips down, broker bearish, extended ──
    if prev_delta > 0 > today_delta and _broker_bearish(smart_money, verdict):
        if pct_above_30d_low >= oversold_pct:
            return _build("short", smart_money, _BEARISH_SMART,
                          extreme_pct=pct_above_30d_low, oversold_pct=oversold_pct,
                          in_idx30=in_idx30, prev_delta=prev_delta, today_delta=today_delta)

    return None


# Conviction budget (sums to 100 at the cap):
#   base 40 + broker 18 + idx30 12 + oversold depth 15 + delta swing 15
_SWING_FULL_BONUS_AT = 1_000_000_000.0   # IDR swing that earns the full 15 pts


def _build(direction, smart_money, strong_set, *, extreme_pct, oversold_pct,
           in_idx30, prev_delta, today_delta) -> dict:
    """Assemble conviction score + human-readable reasons for a qualified setup."""
    reasons = []
    conviction = 40.0

    swing = abs(today_delta - prev_delta)
    reasons.append(f"delta flip {prev_delta/1e9:+.2f}B -> {today_delta/1e9:+.2f}B (swing {swing/1e9:.2f}B)")

    if _norm(smart_money) in strong_set:
        conviction += 18.0
        reasons.append(f"broker {_norm(smart_money)} (strong)")
    else:
        reasons.append("broker confirms direction")

    if in_idx30:
        conviction += 12.0
        reasons.append("IDX30 (top liquidity)")
    else:
        reasons.append("LQ45")

    depth_bonus = min(15.0, (extreme_pct - oversold_pct) / 2.0)
    conviction += max(0.0, depth_bonus)
    edge = "below 30d high" if direction == "long" else "above 30d low"
    reasons.append(f"{extreme_pct:.1f}% {edge}")

    swing_bonus = min(15.0, swing / _SWING_FULL_BONUS_AT * 15.0)
    conviction += swing_bonus
    reasons.append(f"swing {swing/1e9:.2f}B (+{swing_bonus:.0f})")

    return {
        "direction": direction,
        "conviction": round(min(100.0, conviction), 1),
        "reasons": reasons,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# SCAN LAYER (DB-backed)
# ═══════════════════════════════════════════════════════════════════════════════

def _get_conn(db_path: str = _DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _latest_screen_date(conn) -> Optional[str]:
    row = conn.execute("SELECT MAX(date) FROM daily_screen").fetchone()
    return row[0] if row else None


def scan_reversals(conn: sqlite3.Connection, screen_date: str) -> list[dict]:
    """Scan one EOD date for liquid long/short reversal setups.

    Joins today's delta against the prior trading day's delta, today's broker
    verdict, the 30-day OHLCV range, and index membership; runs each row through
    classify_reversal(); returns qualified setups sorted by conviction desc.
    """
    query = """
        SELECT
            t.ticker, t.close, t.delta AS today_delta,
            p.delta AS prev_delta,
            f.smart_money, f.verdict, f.net_value,
            it.in_lq45, it.in_idx30,
            rng.high_30d, rng.low_30d
        FROM daily_screen t
        JOIN (
            SELECT ds.ticker, ds.delta
            FROM daily_screen ds
            JOIN (
                SELECT ticker, MAX(date) AS pdate
                FROM daily_screen WHERE date < ? GROUP BY ticker
            ) last ON ds.ticker = last.ticker AND ds.date = last.pdate
        ) p ON t.ticker = p.ticker
        JOIN idx_tickers it ON t.ticker = it.ticker
        LEFT JOIN (
            SELECT ticker, smart_money, verdict, net_value
            FROM stockbit_flow WHERE trade_date = ?
        ) f ON t.ticker = f.ticker
        LEFT JOIN (
            SELECT ticker, MAX(high) AS high_30d, MIN(low) AS low_30d
            FROM ohlcv
            WHERE date >= date(?, '-30 days') AND date <= ?
            GROUP BY ticker
        ) rng ON t.ticker = rng.ticker
        WHERE t.date = ?
          AND (it.in_lq45 = 1 OR it.in_idx30 = 1)
    """
    rows = conn.execute(
        query, (screen_date, screen_date, screen_date, screen_date, screen_date)
    ).fetchall()

    results = []
    for r in rows:
        high_30d = r["high_30d"]
        low_30d = r["low_30d"]
        close = r["close"]
        if not high_30d or not low_30d or not close:
            continue
        pct_below_high = (high_30d - close) / high_30d * 100.0
        pct_above_low = (close - low_30d) / low_30d * 100.0

        sig = classify_reversal(
            prev_delta=r["prev_delta"],
            today_delta=r["today_delta"],
            smart_money=r["smart_money"],
            verdict=r["verdict"],
            pct_below_30d_high=pct_below_high,
            pct_above_30d_low=pct_above_low,
            in_lq45=r["in_lq45"],
            in_idx30=r["in_idx30"],
        )
        if sig is None:
            continue
        results.append({
            "ticker": r["ticker"],
            "close": close,
            "direction": sig["direction"],
            "conviction": sig["conviction"],
            "reasons": sig["reasons"],
            "prev_delta": r["prev_delta"],
            "today_delta": r["today_delta"],
            "smart_money": r["smart_money"],
            "verdict": r["verdict"],
            "net_value": r["net_value"],
            "pct_below_30d_high": round(pct_below_high, 1),
            "pct_above_30d_low": round(pct_above_low, 1),
            "in_lq45": r["in_lq45"],
            "in_idx30": r["in_idx30"],
        })

    results.sort(key=lambda x: x["conviction"], reverse=True)
    return results


_WATCHLIST_DDL = """
CREATE TABLE IF NOT EXISTS reversal_watchlist (
    scan_date   TEXT NOT NULL,
    ticker      TEXT NOT NULL,
    direction   TEXT NOT NULL,
    conviction  REAL,
    close       INTEGER,
    smart_money TEXT,
    verdict     TEXT,
    net_value   INTEGER,
    reasons     TEXT,
    created_at  TEXT DEFAULT (datetime('now','localtime')),
    PRIMARY KEY (scan_date, ticker)
)
"""


def persist_watchlist(conn: sqlite3.Connection, screen_date: str,
                      results: list[dict]) -> int:
    """Write scan results to reversal_watchlist for next-morning use.

    Idempotent: clears any prior rows for screen_date before inserting.
    Returns the number of rows written.
    """
    conn.execute(_WATCHLIST_DDL)
    conn.execute("DELETE FROM reversal_watchlist WHERE scan_date=?", (screen_date,))
    conn.executemany(
        """INSERT INTO reversal_watchlist
           (scan_date, ticker, direction, conviction, close,
            smart_money, verdict, net_value, reasons)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        [
            (screen_date, r["ticker"], r["direction"], r["conviction"], r["close"],
             r.get("smart_money"), r.get("verdict"), r.get("net_value"),
             json.dumps(r.get("reasons", [])))
            for r in results
        ],
    )
    conn.commit()
    return len(results)


def run_scan(screen_date: Optional[str] = None, db_path: str = _DB_PATH) -> list[dict]:
    """Convenience wrapper: open the project DB, default to latest EOD date."""
    conn = _get_conn(db_path)
    try:
        if screen_date is None:
            screen_date = _latest_screen_date(conn)
            if not screen_date:
                return []
        return scan_reversals(conn, screen_date)
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# OUTPUT
# ═══════════════════════════════════════════════════════════════════════════════

def format_table(results: list[dict], screen_date: str) -> str:
    if not results:
        return f"No reversal setups found for {screen_date}."
    header = (f"{'#':>3} {'Ticker':<7} {'Dir':<6} {'Conv':>5} {'Close':>8} "
              f"{'Liq':<5} {'Broker':<13} {'BelowHi%':>8} {'AboveLo%':>8}")
    lines = [f"REVERSAL WATCHLIST — {screen_date} EOD (for next session)",
             "=" * len(header), header, "-" * len(header)]
    for i, r in enumerate(results, 1):
        d = "▲LONG" if r["direction"] == "long" else "▼SHORT"
        liq = "IDX30" if r["in_idx30"] else "LQ45"
        lines.append(
            f"{i:>3} {r['ticker']:<7} {d:<6} {r['conviction']:>5.1f} "
            f"{r['close']:>8,} {liq:<5} {(_norm(r['smart_money']) or '-'):<13} "
            f"{r['pct_below_30d_high']:>8.1f} {r['pct_above_30d_low']:>8.1f}"
        )
    longs = sum(1 for r in results if r["direction"] == "long")
    shorts = len(results) - longs
    lines += ["-" * len(header),
              f"Total: {len(results)} setups | ▲ {longs} long | ▼ {shorts} short"]
    return "\n".join(lines)


def format_json(results: list[dict], screen_date: str) -> str:
    return json.dumps({"scan_date": screen_date, "count": len(results),
                       "results": results}, indent=2, default=str)


def main():
    p = argparse.ArgumentParser(description="EOD delta-reversal pre-scan (liquid day trades)")
    p.add_argument("--date", type=str, default=None, help="EOD date (default: latest)")
    p.add_argument("--json", action="store_true")
    p.add_argument("--direction", choices=["long", "short"], default=None)
    p.add_argument("--persist", action="store_true", help="Write to reversal_watchlist table")
    args = p.parse_args()

    conn = _get_conn()
    try:
        screen_date = args.date or _latest_screen_date(conn)
        if not screen_date:
            print("No daily_screen data found.", file=sys.stderr)
            return
        results = scan_reversals(conn, screen_date)
        if args.direction:
            results = [r for r in results if r["direction"] == args.direction]
        if args.persist:
            n = persist_watchlist(conn, screen_date, results)
            print(f"Persisted {n} setups to reversal_watchlist ({screen_date})", file=sys.stderr)
        print(format_json(results, screen_date) if args.json
              else format_table(results, screen_date))
    finally:
        conn.close()


if __name__ == "__main__":
    main()
