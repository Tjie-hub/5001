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


def test_placebo_keeps_per_date_count_and_is_null():
    pan = _pan(n_tickers=120, years=4, effect_pct_per_event=-3.0, event_rate=0.005, seed=6)
    f = synthetic.ev_signal(pan.P)
    p = events.placebo_flags(pan, f, seed=7)
    el = pan.eligible.values
    a = pd.Series((f.values > 0) & el).groupby(pan.P.date.values).sum()
    b = pd.Series(p.values > 0).groupby(pan.P.date.values).sum()
    assert (a.values == b.values).all()
    months, _ = events.run_event_months(pan, p, EVCARD)
    assert abs(nw_t([m["primary"] for m in months if m.get("valid")], 3)) < 3.0


def test_random_flags_rate_and_event_checks():
    pan = _pan(n_tickers=80, years=2, event_rate=0.01, seed=8)
    r = events.random_flags(pan, 0.02, seed=1)
    share = r[pan.eligible].mean()
    assert 0.015 < share < 0.025 and r[~pan.eligible].sum() == 0
    E = events.build_events(pan, synthetic.ev_signal(pan.P), 20)
    assert events.event_order_check(E)["status"] == "PASS"
    assert events.event_nondegenerate(pan, synthetic.ev_signal(pan.P))["status"] == "PASS"
    assert events.event_nondegenerate(pan, pd.Series(1.0, index=pan.P.index))["status"] == "FAIL"
    assert events.event_nondegenerate(pan, pd.Series(0.0, index=pan.P.index))["status"] == "FAIL"


from research.rulecard import card as cardmod  # noqa: E402


def event_card():
    from tests.test_rulecard_engine import valid_card
    c = valid_card()
    c["tier"] = "N"
    c["trials"] = {"n_trials": 1}
    c.pop("monotonicity", None)
    c["signal"].update(formation="event", hold_sessions=20)
    c["portfolio"] = {"bucketing": "flag", "use": "avoid", "use_end": "high"}
    c["estimand"].update(primary_kind="bucket_minus_rest", aggregation="calendar_time")
    c["power"].update(event_rate=0.005, sigma_planning=1.0, sigma_noise_floor=1.0,
                      literature_effect=4.0, n_months=40)
    c["hurdle"] = {"t_min": 3.0}
    c["deployment"]["hurdle_t"] = 3.0
    return c


def test_event_card_validates():
    cardmod.validate(event_card(), strict=True)


@pytest.mark.parametrize("mut,msg", [
    (lambda c: c["signal"].pop("hold_sessions"), "hold_sessions"),
    (lambda c: c["portfolio"].update(bucketing="decile"), "bucketing: flag"),
    (lambda c: c["estimand"].pop("aggregation"), "calendar_time"),
    (lambda c: c["power"].update(event_rate="PENDING"), "event_rate"),
    (lambda c: c["signal"].update(formation="weekly"), "signal.formation")])
def test_event_card_refusals(mut, msg):
    c = event_card()
    mut(c)
    with pytest.raises(cardmod.CardError, match=msg):
        cardmod.validate(c, strict=True)


import textwrap  # noqa: E402

import yaml  # noqa: E402

from research.rulecard import runner  # noqa: E402

EV_RULE = textwrap.dedent('''
    from research.rulecard import synthetic

    def load_panel(ctx):
        return synthetic.make_event_panel(n_tickers=100, years=5, effect_pct_per_event=-3.0,
                                          event_rate=0.005, seed=3, low_adv_boost=2.0)

    def signal(panel):
        return synthetic.ev_signal(panel)
''')


@pytest.fixture
def ev_dir(tmp_path):
    d = tmp_path / "RC-EV"
    d.mkdir()
    c = event_card()
    c["windows"] = {"split": "2014-06-01"}
    (d / "CARD.yaml").write_text(yaml.safe_dump(c, sort_keys=False))
    (d / "rule.py").write_text(EV_RULE)
    return d


def test_event_dry_reports_rate_without_returns(ev_dir):
    out = runner.dry(ev_dir / "CARD.yaml")
    assert 0.003 < out["event_rate"] < 0.007 and out["events_per_year"]
    assert all(c["status"] == "PASS" for c in out["checks"]), out["checks"]


def test_event_power_never_calls_signal(ev_dir, monkeypatch):
    real = runner._load_module

    def guarded(p):
        m = real(p)

        def boom(*_):
            raise AssertionError("signal() called by power")
        m.signal = boom
        return m
    monkeypatch.setattr(runner, "_load_module", guarded)
    out = runner.power(ev_dir / "CARD.yaml", seeds=3)
    assert out["signal_called"] is False and out["sigma_noise_floor"] > 0


def test_event_card_freeze_run_pass(ev_dir, tmp_path):
    runner.freeze(ev_dir / "CARD.yaml", "Owner test")
    out = runner.run(ev_dir / "CARD.yaml", tmp_path / "ledger.jsonl")
    assert all(c["status"] == "PASS" for c in out["checks"]), out["checks"]
    assert out["verdict"]["verdict"] == "PASS", out["verdict"]


def test_rc0002_panel_is_pre2021_only(monkeypatch):
    import importlib.util
    p = ROOT / "docs/research_programs/P-M/rulecards/RC-0002-FB-PRE2021/rule.py"
    spec = importlib.util.spec_from_file_location("rc0002", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    fake = synthetic.make_event_panel(n_tickers=3, years=12, start="2012-01-02").drop(columns="ev")
    assert fake.date.max() >= pd.Timestamp("2021-07-05")
    monkeypatch.setattr(m, "load_extended_ohlcv", lambda: fake)
    P = m.load_panel({})
    assert P.date.max() < pd.Timestamp("2021-07-05")
    s = m.signal(engine.prepare(P))
    assert set(np.unique(s.values)) <= {0.0, 1.0} and s.sum() > 0
