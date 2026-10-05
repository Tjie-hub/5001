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
