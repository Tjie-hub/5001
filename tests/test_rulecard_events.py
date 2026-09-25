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


from research.rulecard import engine, events  # noqa: E402
from research.rulecard.stats import nw_t  # noqa: E402

EVCARD = {"signal": {"hold_sessions": 20}, "costs": {"round_trip_pct": 0.60}}


def _pan(**kw):
    return engine.Panel(synthetic.make_event_panel(**kw))


def test_entry_next_open_exit_hth_close_and_stale():
    pan = _pan(n_tickers=60, years=2, event_rate=0.01, seed=2)
    E = events.build_events(pan, synthetic.ev_signal(pan.P), 20)
    T = E[E.tradeable]
    assert len(T) > 50
    assert (T.entry_row == T.signal_row + 1).all()
    ok = ~T.stale
    assert (T.exit_row[ok] == T.signal_row[ok] + 20).all()
    last = pan.P.groupby("ticker", sort=False).cumcount(ascending=False).values
    assert T.stale.any() and (last[T.exit_row[T.stale].values] == 0).all()


def test_planted_anti_edge_is_recovered():
    pan = _pan(n_tickers=120, years=5, effect_pct_per_event=-3.0, event_rate=0.005, seed=4)
    months, _ = events.run_event_months(pan, synthetic.ev_signal(pan.P), EVCARD)
    prim = [m["primary"] for m in months if m.get("valid")]
    assert len(prim) > 50
    assert np.mean(prim) < 0 and nw_t(prim, 3) < -3.0


def test_null_is_null():
    ts = []
    for s in range(3):
        pan = _pan(n_tickers=120, years=4, effect_pct_per_event=0.0, event_rate=0.005, seed=10 + s)
        months, _ = events.run_event_months(pan, synthetic.ev_signal(pan.P), EVCARD)
        ts.append(nw_t([m["primary"] for m in months if m.get("valid")], 3))
    assert abs(np.mean(ts)) < 2.0


def test_no_event_dropped_for_holding_window_content():
    raw = synthetic.make_event_panel(n_tickers=60, years=2, event_rate=0.01, seed=5)
    pan0 = engine.Panel(raw)
    E0 = events.build_events(pan0, synthetic.ev_signal(pan0.P), 20)
    ev = E0[E0.tradeable & ~E0.stale].iloc[0]
    tk, d = ev.ticker, pan0.P.loc[ev.signal_row + 10, "date"]
    m = (raw.ticker == tk) & (raw.date >= d)
    raw.loc[m, ["open", "high", "low", "close"]] *= 1.5       # +50% jump inside the hold
    pan = engine.Panel(raw)
    E = events.build_events(pan, synthetic.ev_signal(pan.P), 20)
    assert ((E.ticker == tk) & (E.signal_row == ev.signal_row) & E.tradeable).any()
    months, _ = events.run_event_months(pan, synthetic.ev_signal(pan.P), EVCARD)
    assert sum(r.get("big_moves_in_hold", 0) for r in months) >= 1
