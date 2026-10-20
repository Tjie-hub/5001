"""FWD-PM-FADE-001 recorder: the contamination window is the holding window t+1 .. t+h (DEV-002, 2026-10-20).

The frozen in-sample script's `s.shift(-1).rolling(h)` sums t-h+2 .. t+1, the sessions BEFORE the signal
(pandas rolling is right-aligned). The recorder now uses `s.shift(-h).rolling(h)`."""
import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd

_P = Path(__file__).resolve().parents[1] / "docs/research_programs/P-M/forward_fade/run_recorder.py"
_spec = importlib.util.spec_from_file_location("fade_rec", _P)
rec = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rec)


def _built(bad_row=20, n=40):
    dates = pd.bdate_range("2026-03-02", periods=n)
    c = np.full(n, 1000.0)
    d = pd.DataFrame({"ticker": "AAA", "date": dates, "open": c, "high": c, "low": c, "close": c, "volume": 1e6})
    splits = pd.DataFrame({"ticker": ["AAA"], "date": [dates[bad_row]], "is_split": [1]})
    return rec.build(d, splits)


def test_the_guard_covers_the_holding_window_only():
    d = _built()
    for h, first in ((5, 15), (10, 10), (20, 0)):
        flagged = [i for i, v in enumerate(d[f"bad_{h}"]) if v > 0]
        assert flagged == list(range(first, 20)), (h, flagged)   # signals whose t+1 .. t+h holds row 20


def test_sessions_after_the_bad_day_are_not_voided():
    d = _built()
    assert d.loc[20:23, "bad_5"].sum() == 0   # the frozen shift(-1) form flagged rows 19 .. 23
