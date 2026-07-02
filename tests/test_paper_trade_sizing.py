"""Position sizing correctness (audit C-2 / plan 1A item 1.5).

Old bug: lots = risk_rp / (ATR × 100) regardless of the actual stop distance,
so a 2×ATR stop risked 2× the configured risk_pct, and strategy-provided SLs
(e.g. Crash Recovery's resume low) were ignored for sizing entirely.

New behavior: sizing delegates to engine.strategies.lot_size — the same
authority the backtests use — fed the ACTUAL stop percentage.
"""
import sqlite3

import pytest


@pytest.fixture()
def pt_db(tmp_path, monkeypatch):
    """Isolated paper_trade DB with OHLCV for ticker TEST (ATR14 ≈ 20)."""
    import paper_trade as pt
    db = str(tmp_path / "pt.db")
    monkeypatch.setattr(pt, "DB_PATH", db)
    pt.init_paper_table()
    conn = sqlite3.connect(db)
    conn.execute(
        "CREATE TABLE ohlcv (ticker TEXT, date TEXT, open REAL, high REAL, "
        "low REAL, close REAL, volume REAL)"
    )
    # 20 identical bars: high-low = 20 → TR = 20 → ATR14 = 20.
    for i in range(20):
        conn.execute(
            "INSERT INTO ohlcv VALUES ('TEST', ?, 1000, 1010, 990, 1000, 1000000)",
            (f"2026-06-{i + 1:02d}",),
        )
    conn.commit()
    conn.close()
    return db


def test_lots_sized_on_actual_stop_distance(pt_db):
    """entry 1000, explicit SL 900 (10%): risk = 2% × 50M = 1,000,000;
    risk per lot = 1000×100×0.10 = 10,000 → 100 lots.
    Old ATR-based code produced 150 (risk_rp/(ATR×100)=500, capped at 30%)."""
    import paper_trade as pt
    res = pt.open_trade("TEST", 1000.0, sl_price=900.0, notify=False)
    assert "error" not in res, res
    assert res["lots"] == 100


def test_atr_stop_risks_configured_pct(pt_db):
    """No explicit SL → SL = entry − 2×ATR = 960 (4%): risk per lot = 4,000
    → 1,000,000/4,000 = 250 lots, capped at 30% of capital = 150 lots.
    (Old code sized on 1×ATR: 500 lots pre-cap — same cap here, so the
    distinguishing case is the explicit-SL test above; this pins the cap.)"""
    import paper_trade as pt
    res = pt.open_trade("TEST", 1000.0, notify=False)
    assert "error" not in res, res
    assert res["lots"] == 150  # 30% cap: int(15M / 100k)


def test_aggregate_exposure_cap_blocks_over_capital(pt_db):
    """Audit C-2: 5 × 30% positions = 150% notional was possible. With 45M of
    50M already deployed, a new 10M position (100 lots × 100k) must be
    rejected."""
    import paper_trade as pt
    conn = sqlite3.connect(pt_db)
    for t in ("AAAA", "BBBB", "CCCC"):
        conn.execute(
            "INSERT INTO paper_trades (ticker, strategy, entry_date, entry_price,"
            " lots, capital_used, tp_price, sl_price, status)"
            " VALUES (?, 'momentum', '2026-06-20', 1000, 150, 15000000, 1200, 900, 'OPEN')",
            (t,),
        )
    conn.commit()
    conn.close()
    res = pt.open_trade("TEST", 1000.0, sl_price=900.0, notify=False)
    assert "error" in res
    assert "aggregate" in res["error"].lower()


def test_aggregate_cap_allows_within_capital(pt_db):
    """25M deployed + 10M new = 35M ≤ 50M → allowed."""
    import paper_trade as pt
    conn = sqlite3.connect(pt_db)
    conn.execute(
        "INSERT INTO paper_trades (ticker, strategy, entry_date, entry_price,"
        " lots, capital_used, tp_price, sl_price, status)"
        " VALUES ('AAAA', 'momentum', '2026-06-20', 1000, 250, 25000000, 1200, 900, 'OPEN')"
    )
    conn.commit()
    conn.close()
    res = pt.open_trade("TEST", 1000.0, sl_price=900.0, notify=False)
    assert "error" not in res, res
