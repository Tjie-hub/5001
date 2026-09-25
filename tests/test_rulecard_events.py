"""Event-time Rule Card engine (research/rulecard/events.py, design 2026-09-25).

What must hold: entry at the next open and exit at the h-th own session's close; a stale exit
is flagged, never dropped; no event is dropped for anything inside its holding window (R-3);
a planted anti-edge is recovered, a null stays null, a placebo keeps the per-date count; power
never calls signal(); a card with formation: event freezes and runs through the unchanged
evaluate/verdict machinery.
"""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from research.rulecard import synthetic

ROOT = Path(__file__).resolve().parents[1]


def test_event_panel_plants_post_event_drift():
    P = synthetic.make_event_panel(n_tickers=60, years=2, effect_pct_per_event=-20.0, hold=20,
                                   event_rate=0.01, vol=0.001, seed=1)
    assert set(P.columns) >= {"ticker", "date", "open", "high", "low", "close", "volume", "ev"}
    x = P[P.ticker == "S000"].reset_index(drop=True)
    t = int(np.flatnonzero(x.ev.values > 0)[0])
    assert x.close[t + 20] / x.close[t] - 1 < -0.10
