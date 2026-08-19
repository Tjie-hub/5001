"""T7 invariant #9 -- every production admission must be explainable after
the fact: what strategy, what registry entry/state, what admission
decision, when.

paper_trades already records `strategy` (the strategy_fn) and `entry_date`
(when). What was missing: which registry state and which admission
decision (clean evidence vs. a _LIFECYCLE_DEBT grandfather exception vs.
not registry-governed at all) authorized the trade -- previously only
reconstructable by manually correlating entry_date against
`git log -- registry/edge_registry.yaml`. Two nullable columns close this:
`admission_path` (engine.registry_loader.admission_path()'s classification)
and `registry_hash` (get_registry()['hash'] at the moment of admission --
a git commit short-hash or content hash an auditor can `git show` directly).

No duplicate registry: both values are read straight off the existing
get_registry() at admission time and merely recorded on the trade row.
"""
import sqlite3

import pytest


@pytest.fixture()
def pt_db(tmp_path, monkeypatch):
    import paper_trade as pt
    db = str(tmp_path / "pt.db")
    monkeypatch.setattr(pt, "DB_PATH", db)
    pt.init_paper_table()
    conn = sqlite3.connect(db)
    conn.execute(
        "CREATE TABLE ohlcv (ticker TEXT, date TEXT, open REAL, high REAL, "
        "low REAL, close REAL, volume REAL)"
    )
    for i in range(20):
        conn.execute(
            "INSERT INTO ohlcv VALUES ('TEST', ?, 1000, 1010, 990, 1000, 1000000)",
            (f"2026-06-{i + 1:02d}",),
        )
    conn.commit()
    conn.close()
    return db


def test_init_paper_table_adds_admission_columns(pt_db):
    conn = sqlite3.connect(pt_db)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(paper_trades)").fetchall()}
    conn.close()
    assert "admission_path" in cols
    assert "registry_hash" in cols


def test_open_trade_records_admission_path_and_registry_hash(pt_db):
    import paper_trade as pt
    res = pt.open_trade("TEST", 1000.0, sl_price=900.0, notify=False,
                        admission_path="APPROVED_CLEAN", registry_hash="abc1234")
    assert "error" not in res, res
    conn = sqlite3.connect(pt_db)
    row = conn.execute(
        "SELECT admission_path, registry_hash FROM paper_trades WHERE id=?",
        (res["id"],)
    ).fetchone()
    conn.close()
    assert row == ("APPROVED_CLEAN", "abc1234")


def test_open_trade_without_admission_info_leaves_columns_null(pt_db):
    """Callers that don't know/care (manual API, premover) are unaffected --
    the columns are optional, not a required contract on every open_trade()
    call site."""
    import paper_trade as pt
    res = pt.open_trade("TEST", 1000.0, sl_price=900.0, notify=False)
    assert "error" not in res, res
    conn = sqlite3.connect(pt_db)
    row = conn.execute(
        "SELECT admission_path, registry_hash FROM paper_trades WHERE id=?",
        (res["id"],)
    ).fetchone()
    conn.close()
    assert row == (None, None)
