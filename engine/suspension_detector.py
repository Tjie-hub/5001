"""
suspension_detector.py — Detects trading suspensions and data-fetch gaps in
OHLCV history. See docs/superpowers/specs/2026-05-28-suspension-detector-design.md.

Three layers:
  detect_gaps(df, ...)  — pure, no I/O, returns list[GapEvent]
  scan_all(...)         — runs detect_gaps across all tickers, persists to SQLite
  get_status(ticker)    — read API for downstream consumers
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional

import pandas as pd

from engine.calendar_filter import is_trading_day


@dataclass
class GapEvent:
    ticker: str
    last_normal_date: str   # ISO date (YYYY-MM-DD)
    resume_date: str        # ISO date (YYYY-MM-DD)
    missing_td: int         # trading-day count, calendar-aware
    gap_pct: float          # (resume_open - last_close) / last_close
    classification: str     # 'suspension' | 'data_gap'
    detected_at: str        # ISO timestamp


def _count_missing_trading_days(start_exclusive: date, end_exclusive: date) -> int:
    """Trading days strictly between two dates (both endpoints excluded)."""
    if end_exclusive <= start_exclusive:
        return 0
    count = 0
    d = start_exclusive + timedelta(days=1)
    while d < end_exclusive:
        ok, _ = is_trading_day(d)
        if ok:
            count += 1
        d += timedelta(days=1)
    return count


def detect_gaps(
    df: Optional[pd.DataFrame],
    *,
    threshold_days: int = 3,
    price_jump_pct: float = 10.0,
    detected_at: Optional[str] = None,
) -> List[GapEvent]:
    """Detect trading-day gaps in df. Pure — no DB, no I/O."""
    if df is None or len(df) < 2:
        return []
    if detected_at is None:
        detected_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    dates = pd.to_datetime(df["date"]).dt.date.tolist()
    closes = df["close"].tolist()
    opens = df["open"].tolist()

    events: List[GapEvent] = []
    for i in range(len(df) - 1):
        d0, d1 = dates[i], dates[i + 1]
        missing = _count_missing_trading_days(d0, d1)
        if missing <= threshold_days:
            continue
        last_close = closes[i]
        resume_open = opens[i + 1]
        if last_close <= 0:
            continue
        gap_pct = (resume_open - last_close) / last_close
        classification = (
            "suspension" if abs(gap_pct) * 100.0 >= price_jump_pct else "data_gap"
        )
        events.append(GapEvent(
            ticker="",
            last_normal_date=d0.isoformat(),
            resume_date=d1.isoformat(),
            missing_td=missing,
            gap_pct=float(gap_pct),
            classification=classification,
            detected_at=detected_at,
        ))
    return events
