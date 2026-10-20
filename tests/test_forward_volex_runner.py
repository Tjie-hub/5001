"""FWD-PM-VOLEX-001 runner: Rupiah traded value is split-invariant (DEV-003, 2026-10-20).

load_panel() divides pre-ex prices by the split factor; traded value was computed AFTER that, from the adjusted
close times the raw share volume, so a recent split understated a name's liquidity by the factor in the
top-200 ranking."""
import importlib.util
import sqlite3
from pathlib import Path

import pandas as pd
import pytest

_P = Path(__file__).resolve().parents[1] / "docs/research_programs/P-M/forward_exclusion/run_forward.py"
_spec = importlib.util.spec_from_file_location("volex_run", _P)
rf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rf)


def test_traded_value_is_not_scaled_by_the_split_fix(tmp_path, monkeypatch):
    db = tmp_path / "w.db"
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE ohlcv (ticker TEXT, date TEXT, high REAL, low REAL, close REAL, volume REAL, "
                "is_final INTEGER)")
    con.execute("CREATE TABLE corporate_actions (ticker TEXT, date TEXT, action TEXT, value REAL)")
    con.execute("CREATE TABLE suspension_events (ticker TEXT, last_normal_date TEXT, resume_date TEXT)")
    days = [d.strftime("%Y-%m-%d") for d in pd.bdate_range("2026-07-01", periods=50)]
    for i, d in enumerate(days):
        # SPLT: 5:1 split on day 30, store unadjusted; Rupiah turnover stays Rp 1 bn a day throughout
        c, v = (1000.0, 1e6) if i < 30 else (200.0, 5e6)
        con.execute("INSERT INTO ohlcv VALUES ('SPLT', ?, ?, ?, ?, ?, 1)", (d, c * 1.01, c * 0.99, c, v))
        con.execute("INSERT INTO ohlcv VALUES ('CTRL', ?, 505, 495, 500, 2e6, 1)", (d,))
    con.execute("INSERT INTO corporate_actions VALUES ('SPLT', ?, 'split', 5)", (days[30],))
    con.commit()
    monkeypatch.setattr(rf, "DB", str(db))
    panel = rf.load_panel()
    assert panel["close"].loc[days[0], "SPLT"] == pytest.approx(200.0)      # the split fix still adjusts prices
    assert panel["tvm"].loc[days[-1], "SPLT"] == pytest.approx(1e9)         # liquidity is not cut by 5x
    assert panel["tvm"].loc[days[-1], "CTRL"] == pytest.approx(1e9)
