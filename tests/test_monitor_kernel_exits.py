"""monitor._check_trade must execute the strategy's OWN exit policy via the
shared kernel (plan 1B Task 8 / audit C-3): TFB trails 3xATR + MA20-break,
Panic Rebound is never price-stopped, fixed-level strategies respect their
stored levels, time stops count BARS from ohlcv (not calendar days).
"""
import sqlite3

import pytest


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
                  entry_date="2026-06-20"):
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
                  1000.0, 940.0, None, 20.0, highest=1100.0)
    _insert_bar(mon_db, "TFB1", "2026-06-23", 1050, 1060, 1035, 1055)
    trade = _open_row(mon_db, "TFB1")
    res = mon._check_trade(trade)
    assert res["should_close"] is True
    assert res["exit_reason"] == "TRAIL"
    assert res["exit_price"] == pytest.approx(1040.0)


def test_tfb_ma20_break_closes(mon_db):
    """No trail hit, but close < SMA20 -> MA_BREAK close at the close."""
    import monitor as mon
    _insert_trade(mon_db, "TFB2", "Trend Following Breakout",
                  1000.0, 940.0, None, 20.0, highest=1010.0)
    for i in range(20):                        # SMA20 dominated by 1200s
        _insert_bar(mon_db, "TFB2", f"2026-05-{i+1:02d}", 1200, 1210, 1190, 1200)
    _insert_bar(mon_db, "TFB2", "2026-06-23", 1000, 1005, 995, 998)
    trade = _open_row(mon_db, "TFB2")
    res = mon._check_trade(trade)
    assert res["should_close"] is True
    assert res["exit_reason"] == "MA_BREAK"
    assert res["exit_price"] == pytest.approx(998.0)


def test_panic_rebound_is_never_price_stopped(mon_db):
    """Panic no_sl: 25% crash through the stored SL must NOT close."""
    import monitor as mon
    _insert_trade(mon_db, "PAN1", "Panic Rebound", 1000.0, 950.0, 1100.0, 20.0)
    _insert_bar(mon_db, "PAN1", "2026-06-21", 990, 995, 750, 760)
    trade = _open_row(mon_db, "PAN1")
    res = mon._check_trade(trade)
    assert res["should_close"] is False


def test_panic_rebound_time_stop_after_5_bars(mon_db):
    import monitor as mon
    _insert_trade(mon_db, "PAN2", "Panic Rebound", 1000.0, 950.0, 9999.0, 20.0)
    for i in range(5):                         # 5 completed bars after entry
        _insert_bar(mon_db, "PAN2", f"2026-06-2{i+1}", 1000, 1005, 995, 1000)
    trade = _open_row(mon_db, "PAN2")
    res = mon._check_trade(trade)
    assert res["should_close"] is True
    assert res["exit_reason"] == "TIME"


def test_fixed_level_strategy_respects_stored_sl(mon_db):
    """Crash Recovery: stored SL (resume low) is the stop, not an ATR level."""
    import monitor as mon
    _insert_trade(mon_db, "CRA1", "Crash Recovery", 1000.0, 850.0, 1200.0, 20.0)
    _insert_bar(mon_db, "CRA1", "2026-06-21", 900, 910, 845, 860)
    trade = _open_row(mon_db, "CRA1")
    res = mon._check_trade(trade)
    assert res["should_close"] is True
    assert res["exit_reason"] == "SL"
    assert res["exit_price"] == pytest.approx(850.0)
