"""P0.E2.S1.T2 — minimal last-bar freshness guard wired into monitor.py
(audit H-3: _evaluate_swing_trend's R1-R7 rule evaluation must not run
against a stale last bar, and check_all_open_trades must skip closing/
alerting on stale trades while logging one aggregate warning).

_check_trade's half of the guard is covered in test_monitor_kernel_exits.py
(test_check_trade_skips_evaluation_on_stale_bar), next to the rest of the
kernel-exit fixtures it shares.
"""
import logging
import sqlite3
from datetime import date, timedelta
from unittest.mock import patch

import pytest

TODAY = date.today()


def _d(offset_days: int) -> str:
    return (TODAY + timedelta(days=offset_days)).isoformat()


@pytest.fixture()
def mon_db(tmp_path, monkeypatch):
    import monitor as mon
    db = str(tmp_path / "mon.db")
    monkeypatch.setattr(mon, "DB_PATH", db)
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE ohlcv (ticker TEXT, date TEXT, open REAL, "
                 "high REAL, low REAL, close REAL, volume REAL)")
    conn.commit()
    conn.close()
    return db


def _insert_bars(db, ticker, dates, o=1000, h=1010, l=990, c=1000, v=1000000):
    conn = sqlite3.connect(db)
    for d in dates:
        conn.execute("INSERT INTO ohlcv VALUES (?,?,?,?,?,?,?)", (ticker, d, o, h, l, c, v))
    conn.commit()
    conn.close()


def test_evaluate_swing_trend_skips_on_stale_bar(mon_db):
    """55 bars of history (clears the insufficient_history guard), but the
    last one is several sessions stale -> 'stale' key set, no rule
    evaluated (message == 'stale_bar')."""
    import monitor as mon
    dates = [_d(-59 + i) for i in range(55)]  # last bar = _d(-5), well beyond fresh
    _insert_bars(mon_db, "SWSTALE", dates)
    trade = {"ticker": "SWSTALE", "entry_price": 1000.0, "sl_price": 940.0,
             "adx_peak": 0.0, "highest_seen": 1000.0}
    res = mon._evaluate_swing_trend(trade)
    assert res["stale"] is True
    assert res["message"] == "stale_bar"
    assert res["action"] == "OK"


def test_evaluate_swing_trend_evaluates_normally_on_fresh_bar(mon_db):
    """Control case: same-day last bar is fresh and the rule engine runs
    (no 'stale' key, message isn't the stale marker)."""
    import monitor as mon
    dates = [_d(-54 + i) for i in range(55)]  # last bar = today
    _insert_bars(mon_db, "SWFRESH", dates)
    trade = {"ticker": "SWFRESH", "entry_price": 1000.0, "sl_price": 940.0,
             "adx_peak": 0.0, "highest_seen": 1000.0}
    res = mon._evaluate_swing_trend(trade)
    assert res.get("stale") is None
    assert res["message"] != "stale_bar"


def test_check_all_open_trades_skips_close_and_logs_aggregate_on_stale(monkeypatch, caplog):
    """Both a non-swing and a swing-trend trade reporting stale=True must
    not be closed or alerted on, and the run logs exactly one aggregate
    stale-skip warning."""
    import monitor
    import paper_trade

    non_swing_trade = {"id": 1, "ticker": "STALE_NS", "strategy": "crash recovery",
                        "entry_price": 1000, "sl_price": 850, "tp_price": 1200,
                        "atr14": 20.0, "highest_seen": 1000, "entry_date": _d(-5)}
    swing_trade = {"id": 2, "ticker": "STALE_SW", "strategy": "swing trend",
                   "entry_price": 1000, "sl_price": 940, "tp_price": None,
                   "atr14": 20.0, "highest_seen": 1000, "adx_peak": 0.0, "entry_date": _d(-5)}

    monkeypatch.setattr(paper_trade, "get_open_trades", lambda: [non_swing_trade, swing_trade])
    monkeypatch.setattr(monitor, "_check_trade", lambda t: {
        "should_close": False, "alerts": [], "trail_update": None,
        "exit_reason": None, "exit_price": None, "stale": True,
    })
    monkeypatch.setattr(monitor, "_evaluate_swing_trend", lambda t: {
        "action": "OK", "reason": None, "message": "stale_bar", "new_sl": None, "stale": True,
    })

    close_calls = []
    monkeypatch.setattr(paper_trade, "close_trade", lambda *a, **kw: close_calls.append(a))

    with caplog.at_level(logging.WARNING), patch("monitor.send_telegram"):
        total_alerts = monitor.check_all_open_trades()

    assert close_calls == [], "close_trade must NOT be called for stale trades"
    assert total_alerts == 0
    stale_warnings = [r.message for r in caplog.records if "stale last bar" in r.message]
    assert len(stale_warnings) == 1
    assert "2/2" in stale_warnings[0]
