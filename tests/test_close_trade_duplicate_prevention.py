"""Production Operational Validation Phase 2 finding: close_trade() had no guard
against closing an already-CLOSED trade — unlike open_trade()'s own explicit
"already has an open position" check, close_trade() unconditionally overwrote
exit_date/exit_price/pnl on any trade_id, regardless of current status. Under
normal sequential scheduler cycles this is masked (check_all_open_trades() only
ever sees status='OPEN' rows), but a second close attempt racing the first
(e.g. a manual API close arriving while the scheduled monitor is also closing
the same trade) would silently corrupt the realized P&L with a second exit
price/reason. Found and fixed during the "verify open-position management
across scheduler cycles" / "no duplicate trades" objective of Phase 2.
"""
import sqlite3

import pytest


@pytest.fixture()
def pt_db(tmp_path, monkeypatch):
    import paper_trade as pt
    db = str(tmp_path / "pt.db")
    monkeypatch.setattr(pt, "DB_PATH", db)
    pt.init_paper_table()
    return db


def _insert_open_trade(db_path, ticker="TEST"):
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO paper_trades (ticker, strategy, entry_date, entry_price, lots, "
        "capital_used, tp_price, sl_price, status) VALUES (?,?,?,?,?,?,?,?, 'OPEN')",
        (ticker, "swing trend", "2026-01-01", 1000.0, 10, 1_000_000.0, 1100.0, 900.0),
    )
    conn.commit()
    trade_id = conn.execute("SELECT id FROM paper_trades WHERE ticker=?", (ticker,)).fetchone()[0]
    conn.close()
    return trade_id


def test_close_trade_second_call_is_rejected_not_reapplied(pt_db):
    """The second close_trade() call for an already-closed trade must be a
    no-op error, not a silent P&L overwrite."""
    import paper_trade as pt
    trade_id = _insert_open_trade(pt_db)

    first = pt.close_trade(trade_id, 1050.0, "TP", notify=False)
    assert "error" not in first

    second = pt.close_trade(trade_id, 800.0, "SL", notify=False)
    assert "error" in second, "closing an already-closed trade must be rejected"

    conn = sqlite3.connect(pt_db)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM paper_trades WHERE id=?", (trade_id,)).fetchone()
    conn.close()
    assert row["exit_price"] == 1050.0, "the first close's exit_price must survive untouched"
    assert row["exit_reason"] == "TP"
    assert row["status"] == "CLOSED"


def test_close_trade_on_unknown_id_still_errors(pt_db):
    import paper_trade as pt
    result = pt.close_trade(9999, 1000.0, "MANUAL", notify=False)
    assert "error" in result


def test_check_all_open_trades_never_double_closes_same_trade(pt_db, monkeypatch):
    """The real monitor entry point, run twice in a row against the same DB
    (simulating two scheduler cycles firing back-to-back), must not touch an
    already-closed trade on the second pass."""
    import paper_trade as pt
    import monitor

    trade_id = _insert_open_trade(pt_db, "TEST")

    # Force an immediate SL-style close on the first monitor pass.
    monkeypatch.setattr(monitor, "_get_current_price", lambda ticker: 850.0)
    monkeypatch.setattr(monitor, "_fetch_recent_closes", lambda ticker, n=5: [850.0] * n)
    monkeypatch.setattr(monitor, "_fetch_atr", lambda ticker, periods=14: 20.0)

    monitor.check_all_open_trades()

    conn = sqlite3.connect(pt_db)
    conn.row_factory = sqlite3.Row
    row1 = dict(conn.execute("SELECT * FROM paper_trades WHERE id=?", (trade_id,)).fetchone())
    conn.close()

    # Second pass: get_open_trades() must no longer surface this trade, so
    # monitor has nothing to (re-)close.
    monitor.check_all_open_trades()

    conn = sqlite3.connect(pt_db)
    conn.row_factory = sqlite3.Row
    row2 = dict(conn.execute("SELECT * FROM paper_trades WHERE id=?", (trade_id,)).fetchone())
    conn.close()

    if row1["status"] == "CLOSED":
        assert row2 == row1, "a second monitor pass must not alter an already-closed trade"
