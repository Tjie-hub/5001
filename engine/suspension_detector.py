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


import os
import sqlite3
from typing import Dict


_DEFAULT_DB_PATH = os.getenv(
    "DB_PATH",
    "/home/tjiesar/10 Projects/idx-walkforward-5001/data/walkforward.db",
)


def _ensure_schema(conn: sqlite3.Connection) -> None:
    """Idempotent DDL. Called at the top of every public I/O function."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS suspension_events (
            ticker            TEXT NOT NULL,
            last_normal_date  TEXT NOT NULL,
            resume_date       TEXT NOT NULL,
            missing_td        INTEGER NOT NULL,
            gap_pct           REAL NOT NULL,
            classification    TEXT NOT NULL,
            detected_at       TEXT NOT NULL,
            PRIMARY KEY (ticker, last_normal_date, resume_date)
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_suspension_ticker_resume
            ON suspension_events(ticker, resume_date DESC)
    """)


def _load_ohlcv_bulk(conn: sqlite3.Connection) -> Dict[str, pd.DataFrame]:
    """Bulk-load the ohlcv table into {ticker: df}. Mirrors scheduler._load_ohlcv_bulk."""
    df = pd.read_sql("SELECT * FROM ohlcv ORDER BY ticker, date ASC", conn)
    for c in ["open", "high", "low", "close", "volume"]:
        df[c] = df[c].astype(float)
    return {t: g.reset_index(drop=True) for t, g in df.groupby("ticker")}


def scan_all(
    ohlcv_map: Optional[Dict[str, pd.DataFrame]] = None,
    *,
    threshold_days: int = 3,
    price_jump_pct: float = 10.0,
    conn: Optional[sqlite3.Connection] = None,
    db_path: Optional[str] = None,
) -> int:
    """Scan every ticker's OHLCV for gap events and persist them. Returns rows written."""
    own_conn = conn is None
    if own_conn:
        conn = sqlite3.connect(db_path or _DEFAULT_DB_PATH)
    try:
        _ensure_schema(conn)
        if ohlcv_map is None:
            ohlcv_map = _load_ohlcv_bulk(conn)
        total = 0
        for ticker, df in ohlcv_map.items():
            events = detect_gaps(
                df,
                threshold_days=threshold_days,
                price_jump_pct=price_jump_pct,
            )
            for ev in events:
                ev.ticker = ticker
                conn.execute(
                    "INSERT OR REPLACE INTO suspension_events "
                    "(ticker, last_normal_date, resume_date, missing_td, gap_pct, classification, detected_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        ev.ticker, ev.last_normal_date, ev.resume_date,
                        ev.missing_td, ev.gap_pct, ev.classification, ev.detected_at,
                    ),
                )
                total += 1
        conn.commit()
        return total
    finally:
        if own_conn:
            conn.close()


def _trading_days_inclusive(start: date, end: date) -> int:
    """Trading days from start to end, both inclusive. Returns 0 if start > end."""
    if start > end:
        return 0
    count = 0
    d = start
    while d <= end:
        ok, _ = is_trading_day(d)
        if ok:
            count += 1
        d += timedelta(days=1)
    return count


def get_status(
    ticker: str,
    *,
    as_of: Optional[date] = None,
    post_window: int = 14,
    conn: Optional[sqlite3.Connection] = None,
    db_path: Optional[str] = None,
) -> dict:
    """
    Return suspension/post-suspension flags for `ticker` evaluated at `as_of`.
    Reads the most recent event from suspension_events. See spec §get_status.
    """
    if as_of is None:
        as_of = date.today()
    elif isinstance(as_of, str):
        as_of = date.fromisoformat(as_of)

    own_conn = conn is None
    if own_conn:
        conn = sqlite3.connect(db_path or _DEFAULT_DB_PATH)
    try:
        _ensure_schema(conn)
        row = conn.execute(
            "SELECT last_normal_date, resume_date, missing_td, gap_pct, classification, detected_at "
            "FROM suspension_events WHERE ticker = ? ORDER BY resume_date DESC LIMIT 1",
            (ticker,),
        ).fetchone()

        if not row:
            return {
                "ticker": ticker,
                "suspended_now": False,
                "post_suspension": False,
                "days_since_resume": None,
                "last_event": None,
            }

        last_normal = date.fromisoformat(row[0])
        resume = date.fromisoformat(row[1])
        last_event = {
            "last_normal_date": row[0],
            "resume_date": row[1],
            "missing_td": row[2],
            "gap_pct": row[3],
            "classification": row[4],
            "detected_at": row[5],
        }

        suspended_now = last_normal < as_of < resume

        if as_of < resume:
            days_since_resume = None
        else:
            days_since_resume = _trading_days_inclusive(resume, as_of) - 1

        is_suspension = row[4] == "suspension"
        post_suspension = bool(
            is_suspension
            and days_since_resume is not None
            and days_since_resume <= post_window
        )

        return {
            "ticker": ticker,
            "suspended_now": suspended_now,
            "post_suspension": post_suspension,
            "days_since_resume": days_since_resume,
            "last_event": last_event,
        }
    finally:
        if own_conn:
            conn.close()
