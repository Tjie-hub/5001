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
from typing import List, Optional

import pandas as pd


@dataclass
class GapEvent:
    ticker: str
    last_normal_date: str   # ISO date (YYYY-MM-DD)
    resume_date: str        # ISO date (YYYY-MM-DD)
    missing_td: int         # trading-day count, calendar-aware
    gap_pct: float          # (resume_open - last_close) / last_close
    classification: str     # 'suspension' | 'data_gap'
    detected_at: str        # ISO timestamp


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
    return []
