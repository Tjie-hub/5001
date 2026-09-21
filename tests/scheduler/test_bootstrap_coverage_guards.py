"""Tests for the bootstrap coverage guards (readiness audit 2026-09-16):
- check_same_day_finality()       — C1, same-WIB-day ohlcv finality monitor
- check_prior_session_flow_coverage() — C2, prior-session stockbit_flow gap

Both are alert-only DB reads; neither mutates anything. The 2026-08-25
stockbit_flow session is the recorded zero-coverage shape (DATA_GAP_AUDIT);
the 2026-09-15 pre-open 585-row event is the recorded finality defect.
"""
import sqlite3
from datetime import datetime

from scheduler.jobs import WIB, check_prior_session_flow_coverage, check_same_day_finality


def _mk_db(tmp_path, calendar=True, flow=True, ohlcv=False):
    db = str(tmp_path / "guards.db")
    conn = sqlite3.connect(db)
    if calendar:
        conn.execute("CREATE TABLE trading_calendar (date TEXT PRIMARY KEY, source TEXT)")
    if flow:
        conn.execute("CREATE TABLE stockbit_flow (ticker TEXT, trade_date TEXT, PRIMARY KEY(ticker, trade_date))")
    if ohlcv:
        conn.execute("CREATE TABLE ohlcv (ticker TEXT, date TEXT, open REAL, high REAL, low REAL, close REAL, volume REAL, is_final INTEGER)")
    conn.commit()
    conn.close()
    return db


def _seed_calendar(db, dates):
    conn = sqlite3.connect(db)
    conn.executemany("INSERT OR REPLACE INTO trading_calendar (date, source) VALUES (?, 'scraper_eod')",
                     [(d,) for d in dates])
    conn.commit()
    conn.close()


def _seed_flow(db, trade_date, n):
    conn = sqlite3.connect(db)
    conn.executemany("INSERT OR REPLACE INTO stockbit_flow (ticker, trade_date) VALUES (?, ?)",
                     [(f"T{i:04d}", trade_date) for i in range(n)])
    conn.commit()
    conn.close()


def _seed_final_bars(db, date_str, n):
    conn = sqlite3.connect(db)
    conn.executemany("INSERT INTO ohlcv (ticker, date, open, high, low, close, volume, is_final) VALUES (?, ?, 1, 1, 1, 1, 1, 1)",
                     [(f"T{i:04d}", date_str) for i in range(n)])
    conn.commit()
    conn.close()


# ── C1: same-day finality ────────────────────────────────────────────────────

def test_finality_violation_when_same_day_final_bars_exist(tmp_path):
    db = _mk_db(tmp_path, ohlcv=True)
    _seed_final_bars(db, "2026-09-16", 585)
    now_wib = WIB.localize(datetime(2026, 9, 16, 9, 30))
    s = check_same_day_finality(db, now_wib)
    assert s == {"date": "2026-09-16", "count": 585, "before_eod": True, "violation": True}


def test_finality_silent_when_same_day_provisional(tmp_path):
    db = _mk_db(tmp_path, ohlcv=True)
    _seed_final_bars(db, "2026-09-15", 824)          # yesterday: settled, fine
    now_wib = WIB.localize(datetime(2026, 9, 16, 9, 30))
    s = check_same_day_finality(db, now_wib)
    assert s["count"] == 0
    assert s["violation"] is False


def test_finality_not_a_violation_after_eod_authority(tmp_path):
    db = _mk_db(tmp_path, ohlcv=True)
    _seed_final_bars(db, "2026-09-16", 824)
    now_wib = WIB.localize(datetime(2026, 9, 16, 17, 0))
    s = check_same_day_finality(db, now_wib)
    assert s["before_eod"] is False
    assert s["violation"] is False


# ── C2: prior-session flow gap ───────────────────────────────────────────────

def test_prior_session_zero_rows_alerts(tmp_path):
    """The exact 2026-08-25 shape: calendar proves the session completed,
    stockbit_flow has zero rows — next run must alert."""
    db = _mk_db(tmp_path)
    _seed_calendar(db, ["2026-08-21", "2026-08-24", "2026-08-25"])
    # no flow rows at all for 2026-08-25
    s = check_prior_session_flow_coverage(db, "2026-08-26")
    assert s["session"] == "2026-08-25"
    assert s["alert"] is True
    assert s["n_tickers"] == 0


def test_prior_session_covered_no_alert(tmp_path):
    db = _mk_db(tmp_path)
    _seed_calendar(db, ["2026-08-25", "2026-08-26"])
    _seed_flow(db, "2026-08-25", 870)
    s = check_prior_session_flow_coverage(db, "2026-08-26")
    assert s["alert"] is False
    assert s["covered"] is True


def test_prior_session_partial_distinguishable_from_zero(tmp_path):
    db = _mk_db(tmp_path)
    _seed_calendar(db, ["2026-08-25", "2026-08-26"])
    _seed_flow(db, "2026-08-25", 12)
    s = check_prior_session_flow_coverage(db, "2026-08-26")
    assert s["alert"] is False                        # partial never alerts here
    assert s["n_tickers"] == 12                       # but stays visible


def test_weekend_no_false_alert(tmp_path):
    """Saturday run: prior expected session is Friday via the calendar — no
    manual weekday logic, and a covered Friday never alerts."""
    db = _mk_db(tmp_path)
    _seed_calendar(db, ["2026-08-27", "2026-08-28"])  # Thu, Fri — no Sat/Sun rows
    _seed_flow(db, "2026-08-28", 870)
    s = check_prior_session_flow_coverage(db, "2026-08-29")   # Saturday
    assert s["session"] == "2026-08-28"
    assert s["alert"] is False


def test_empty_calendar_not_evaluable(tmp_path):
    db = _mk_db(tmp_path)                             # calendar table, no rows
    s = check_prior_session_flow_coverage(db, "2026-08-26")
    assert s["evaluable"] is False
    assert s["alert"] is False


def test_missing_tables_not_evaluable(tmp_path):
    """Pre-migration / fixture DB without the tables: fail-quiet, no alert."""
    db = str(tmp_path / "bare.db")
    sqlite3.connect(db).close()
    s = check_prior_session_flow_coverage(db, "2026-08-26")
    assert s["evaluable"] is False
    assert s["alert"] is False
