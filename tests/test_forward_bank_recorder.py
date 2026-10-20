"""FWD-PM-BANK-001 recorder: the frozen signal rule, de-dup, voiding, pending and the cost leg."""
import importlib.util
from pathlib import Path

import numpy as np

_P = Path(__file__).resolve().parents[1] / "docs/research_programs/P-M/forward_bank/run_recorder.py"
_spec = importlib.util.spec_from_file_location("bank_rec", _P)
rec = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rec)


def _series(n=60, crash_at=(40,), drop=0.12):
    c = np.full(n, 1000.0)
    for k in crash_at:
        c[k:] *= 1 - drop              # one-bar collapse to a new 20-day low
    last = max(crash_at)
    c[last + 1:] *= np.cumprod(np.full(n - last - 1, 1.01))   # then a steady recovery
    return c, c * 1.005, c * 0.995


def test_fires_on_a_two_atr_climax_low_only():
    c, h, l = _series()
    assert rec.signal_index(c, h, l) == [40]
    flat = np.full(60, 1000.0)
    assert rec.signal_index(flat, flat * 1.005, flat * 0.995) == []


def test_repeat_within_ten_sessions_is_the_same_event():
    c, h, l = _series(crash_at=(40, 44))
    assert rec.signal_index(c, h, l) == [40]


def test_event_row_pending_void_and_cost():
    dates = [f"2026-11-{i:02d}" for i in range(1, 31)]
    opens = [100.0] * 30
    closes = [100.0] * 30
    closes[15] = 110.0                 # exit close for a firing at i = 5
    book = {"2026-11-06": 0.01}
    ihsg = {("open", "2026-11-07"): 6000.0, ("close", "2026-11-16"): 6060.0}
    row = rec.event_row("BBCA", dates, opens, closes, 5, book, ihsg, set())
    assert row["net_return"] == round(0.10 - rec.COST, 6)
    assert row["excess_ewbook"] == round(0.10 - rec.COST - 0.01, 6)
    assert row["primary"] is True
    assert rec.event_row("BBCA", dates, opens, closes, 25, book, ihsg, set()) == "pending"
    assert rec.event_row("BBCA", dates, opens, closes, 5, book, ihsg, {"2026-11-09"}) == "void"
    jump = closes[:]
    jump[8] = 160.0                    # |ret| > 35% inside the window
    assert rec.event_row("BBCA", dates, opens, jump, 5, book, ihsg, set()) == "void"


def _book_db():
    """A, B flat; C climbs then splits 5:1 on day 35 (recorded). All liquid (ADV20 >= Rp 10 B)."""
    import sqlite3

    import pandas as pd

    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE ohlcv (ticker TEXT, date TEXT, open REAL, high REAL, low REAL, close REAL, "
                "volume REAL, is_final INTEGER)")
    con.execute("CREATE TABLE corporate_actions (ticker TEXT, date TEXT, action TEXT, value REAL)")
    con.execute("CREATE TABLE corporate_action_events (ticker TEXT, action_type TEXT, event_date TEXT)")
    days = [d.strftime("%Y-%m-%d") for d in pd.bdate_range("2026-03-02", periods=50)]
    paths = {"A": [1000.0] * 50, "B": [2000.0] * 50, "IHSG": [7000.0] * 50,
             "C": [1000.0 + 10 * k for k in range(35)] + [200.0] * 15}
    for t, path in paths.items():
        for d, c in zip(days, path):
            con.execute("INSERT INTO ohlcv VALUES (?, ?, ?, ?, ?, ?, 2e7, 1)", (t, d, c, c, c, c))
    con.execute("INSERT INTO corporate_actions VALUES ('C', ?, 'split', 5)", (days[35],))
    return con, days


def test_book_leaves_out_a_member_whose_window_holds_a_price_step():
    """DEV-001 (2026-10-20): the bank leg was voided on price steps, the EW book was not, so a member's split
    entered the benchmark as a -80% 'return' and lifted the bank's excess (July 2026: up to -1.85 pp)."""
    import pytest

    con, days = _book_db()
    _, book, _, voids = rec.load(con)
    assert book[days[20]] == pytest.approx((1300 / 1210 - 1) / 3)   # C clean: in the book
    assert book[days[28]] == pytest.approx(0.0)                     # C's window holds the split: left out
    assert voids == {"C": {days[35]}}
