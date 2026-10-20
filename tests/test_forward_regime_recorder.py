"""FWD-PM-REGIME-002 recorder: the PROTOCOL section 2 contamination guard (DEV-003, 2026-10-19).

The recorder omitted the guard its reference backtest applies (scripts/ref002.py line 26): a split inside a
trade's window tripped the 3xATR stop and would have been recorded as a fake -80% trade."""
import importlib.util
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

_P = Path(__file__).resolve().parents[1] / "docs/research_programs/P-M/forward_regime/run_formation.py"
_spec = importlib.util.spec_from_file_location("regime_rec", _P)
rec = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rec)


def _trade_frame(bad_at=()):
    """One ticker: UP from row 30, a climb to row 50, then a drop that trips the 3xATR trail at row 55."""
    n = 80
    dates = pd.bdate_range("2026-01-05", periods=n)
    close = np.full(n, 1000.0)
    close[30:51] = 1000 + 5 * np.arange(21)
    close[51:] = 1100 - 20 * np.arange(1, n - 50)
    bad = np.zeros(n, dtype=int)
    for k in bad_at:
        bad[k] = 1
    return pd.DataFrame({"ticker": "AAA", "date": dates, "close": close, "high": close * 1.002,
                         "atr14": 10.0, "UP": np.arange(n) >= 30, "liq": True, "bad": bad})


def _run(df):
    ihsg = {pd.Timestamp(d): 7000.0 for d in df.date}
    stats = {}
    out = rec.closed_trades(df, ihsg, pd.Timestamp("2026-01-01"), {}, [], stats)
    return out, stats.get("excluded", 0)


def test_a_clean_window_is_recorded():
    out, excluded = _run(_trade_frame())
    assert len(out) == 1 and excluded == 0
    assert out[0]["entry_date"] == "2026-02-16"   # row 30, the regime onset


def test_a_split_inside_the_window_excludes_the_trade():
    out, excluded = _run(_trade_frame(bad_at=(40,)))
    assert out == [] and excluded == 1


def test_contamination_outside_entry_plus_one_to_exit_does_not_count():
    # the entry bar itself (row 30) and a bar after the exit are outside the protocol window
    out, excluded = _run(_trade_frame(bad_at=(30, 79)))
    assert len(out) == 1 and excluded == 0


def test_bad_marks_recorded_splits_and_moves_beyond_35pct():
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE ohlcv (ticker TEXT, date TEXT, open REAL, high REAL, low REAL, close REAL, "
                "volume REAL, is_final INTEGER)")
    con.execute("CREATE TABLE corporate_actions (ticker TEXT, date TEXT, action TEXT, value REAL)")
    days = [d.strftime("%Y-%m-%d") for d in pd.bdate_range("2026-03-02", periods=40)]
    for t, path in (("AAA", [1000.0] * 20 + [200.0] * 20),        # 5:1 split on day 20
                    ("BBB", [100.0] * 10 + [150.0] * 30),         # +50% with no recorded action
                    ("CCC", [500.0] * 40)):
        for d, c in zip(days, path):
            con.execute("INSERT INTO ohlcv VALUES (?, ?, ?, ?, ?, ?, 1e6, 1)", (t, d, c, c, c, c))
    con.execute("INSERT INTO corporate_actions VALUES ('AAA', ?, 'split', 5)", (days[20],))
    df = rec.features(rec.load_panel(con))
    flagged = {(r.ticker, r.date.strftime("%Y-%m-%d")) for r in df[df.bad == 1].itertuples()}
    assert flagged == {("AAA", days[20]), ("BBB", days[10])}
