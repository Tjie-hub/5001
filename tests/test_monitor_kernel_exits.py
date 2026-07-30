"""monitor._check_trade must execute the strategy's OWN exit policy via the
shared kernel (plan 1B Task 8 / audit C-3): TFB trails 3xATR + MA20-break,
Panic Rebound is never price-stopped, fixed-level strategies respect their
stored levels, time stops count BARS from ohlcv (not calendar days).

Dates are all expressed as offsets from today (see `_d`), not fixed calendar
strings: the P0.E2.S1.T2 freshness guard in monitor._check_trade requires
each test's last bar to be fresh relative to whenever the suite actually
runs. Offsets preserve each test's original day-gaps (entry-to-bar, bar
counts for SMA/time-stop math) exactly — only the reference point moved.
"""
import sqlite3
from datetime import date, timedelta

import pytest

TODAY = date.today()


def _d(offset_days: int) -> str:
    """ISO date `offset_days` from today (negative = past)."""
    return (TODAY + timedelta(days=offset_days)).isoformat()


@pytest.fixture()
def mon_db(tmp_path, monkeypatch):
    import monitor as mon
    import paper_trade as pt
    db = str(tmp_path / "mon.db")
    monkeypatch.setattr(mon, "DB_PATH", db)
    monkeypatch.setattr(pt, "DB_PATH", db)
    pt.init_paper_table()
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE ohlcv (ticker TEXT, date TEXT, open REAL, "
                 "high REAL, low REAL, close REAL, volume REAL)")
    conn.commit()
    conn.close()
    return db


def _insert_trade(db, ticker, strategy, entry, sl, tp, atr, highest=None,
                  entry_date=None):
    entry_date = entry_date if entry_date is not None else _d(-10)
    conn = sqlite3.connect(db)
    conn.execute(
        "INSERT INTO paper_trades (ticker, strategy, entry_date, entry_price,"
        " lots, capital_used, tp_price, sl_price, atr14, highest_seen, status)"
        " VALUES (?,?,?,?,10,1000000,?,?,?,?,'OPEN')",
        (ticker, strategy, entry_date, entry, tp, sl, atr, highest or entry))
    conn.commit()
    conn.close()


def _insert_bar(db, ticker, date, o, h, l, c):
    conn = sqlite3.connect(db)
    conn.execute("INSERT INTO ohlcv VALUES (?,?,?,?,?,?,1000000)",
                 (ticker, date, o, h, l, c))
    conn.commit()
    conn.close()


def _open_row(db, ticker):
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM paper_trades WHERE ticker=? AND status='OPEN'",
                       (ticker,)).fetchone()
    conn.close()
    return dict(row)


def test_tfb_trails_from_high_extreme(mon_db):
    """TFB @1000, ATR 20, highest_seen 1100 -> trail stop 1040. Bar low 1035
    hits it -> close with reason TRAIL at the stop level."""
    import monitor as mon
    _insert_trade(mon_db, "TFB1", "Trend Following Breakout",
                  1000.0, 940.0, None, 20.0, highest=1100.0, entry_date=_d(-3))
    _insert_bar(mon_db, "TFB1", _d(0), 1050, 1060, 1035, 1055)
    trade = _open_row(mon_db, "TFB1")
    res = mon._check_trade(trade)
    assert res["should_close"] is True
    assert res["exit_reason"] == "TRAIL"
    assert res["exit_price"] == pytest.approx(1040.0)


def test_tfb_ma20_break_closes(mon_db):
    """No trail hit, but close < SMA20 -> MA_BREAK close at the close."""
    import monitor as mon
    _insert_trade(mon_db, "TFB2", "Trend Following Breakout",
                  1000.0, 940.0, None, 20.0, highest=1010.0, entry_date=_d(-3))
    for i in range(20):                        # SMA20 dominated by 1200s
        _insert_bar(mon_db, "TFB2", _d(-53 + i), 1200, 1210, 1190, 1200)
    _insert_bar(mon_db, "TFB2", _d(0), 1000, 1005, 995, 998)
    trade = _open_row(mon_db, "TFB2")
    res = mon._check_trade(trade)
    assert res["should_close"] is True
    assert res["exit_reason"] == "MA_BREAK"
    assert res["exit_price"] == pytest.approx(998.0)


def test_panic_rebound_is_never_price_stopped(mon_db):
    """Panic no_sl: 25% crash through the stored SL must NOT close."""
    import monitor as mon
    _insert_trade(mon_db, "PAN1", "Panic Rebound", 1000.0, 950.0, 1100.0, 20.0, entry_date=_d(-1))
    _insert_bar(mon_db, "PAN1", _d(0), 990, 995, 750, 760)
    trade = _open_row(mon_db, "PAN1")
    res = mon._check_trade(trade)
    assert res["should_close"] is False


def test_panic_rebound_time_stop_after_5_bars(mon_db):
    import monitor as mon
    _insert_trade(mon_db, "PAN2", "Panic Rebound", 1000.0, 950.0, 9999.0, 20.0, entry_date=_d(-5))
    for i in range(5):                         # 5 completed bars after entry
        _insert_bar(mon_db, "PAN2", _d(-4 + i), 1000, 1005, 995, 1000)
    trade = _open_row(mon_db, "PAN2")
    res = mon._check_trade(trade)
    assert res["should_close"] is True
    assert res["exit_reason"] == "TIME"


def test_fixed_level_strategy_respects_stored_sl(mon_db):
    """Crash Recovery: stored SL (resume low) is the stop, not an ATR level."""
    import monitor as mon
    _insert_trade(mon_db, "CRA1", "Crash Recovery", 1000.0, 850.0, 1200.0, 20.0, entry_date=_d(-1))
    _insert_bar(mon_db, "CRA1", _d(0), 900, 910, 845, 860)
    trade = _open_row(mon_db, "CRA1")
    res = mon._check_trade(trade)
    assert res["should_close"] is True
    assert res["exit_reason"] == "SL"
    assert res["exit_price"] == pytest.approx(850.0)


def test_check_trade_skips_evaluation_on_stale_bar(mon_db):
    """P0.E2.S1.T2 (H-3): a last bar 2 trading sessions old (beyond the
    default 1-session threshold) must not be evaluated for SL/TP —
    _check_trade returns stale=True and should_close False, even though
    price crashed straight through the stored SL."""
    import monitor as mon
    _insert_trade(mon_db, "STALE1", "Crash Recovery", 1000.0, 950.0, 1200.0, 20.0, entry_date=_d(-10))
    _insert_bar(mon_db, "STALE1", _d(-4), 900, 910, 845, 860)  # would trip SL if evaluated
    trade = _open_row(mon_db, "STALE1")
    res = mon._check_trade(trade)
    assert res["stale"] is True
    assert res["should_close"] is False
    assert res["exit_reason"] is None
