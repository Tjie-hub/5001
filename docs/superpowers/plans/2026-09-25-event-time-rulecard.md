# Event-time Rule Card engine + RC-0002 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the D-055 Rule Card framework test event-time avoidance rules with a day-weighted,
calendar-time estimand. Then run the failed-breakdown anti-edge (HYP-PM-0012) once, on the never-used
pre-2021 backfill.

**Architecture:** A new `research/rulecard/events.py` turns daily 0/1 event flags into positions, then
into a daily excess series (signal leg minus EW liquid book), then into the same monthly records
`evaluate.py` and `checks.py` already consume. `card.py` accepts `formation: event`. `runner.py` branches
on formation for compute, dry and power. Freeze, run-once, ledger and verdict are unchanged.

**Tech Stack:** Python 3.12, pandas 3.0, numpy, pytest. Spec:
`docs/superpowers/specs/2026-09-25-event-time-rulecard-design.md`.

---

## File structure

| file | responsibility |
|---|---|
| `research/rulecard/events.py` (create) | event building, positions, daily/monthly calendar-time records, placebo/random flags, event checks |
| `research/rulecard/synthetic.py` (modify) | `make_event_panel`: synthetic panel with a planted post-event drift |
| `research/rulecard/card.py` (modify ~l.155) | accept `formation: event` and its required fields |
| `research/rulecard/runner.py` (modify `_compute`, `dry`, `power`) | branch on formation |
| `tests/test_rulecard_events.py` (create) | engine, card and runner tests for event mode |
| `docs/research_programs/P-M/rulecards/RC-0002-FB-PRE2021/{CARD.yaml, rule.py}` (create) | the card |

---

### Task 1: Synthetic event panel

**Files:** Modify `research/rulecard/synthetic.py` (append). Test: `tests/test_rulecard_events.py`.

- [ ] **Step 1: Failing test**

```python
from research.rulecard import synthetic

def test_event_panel_plants_post_event_drift():
    P = synthetic.make_event_panel(n_tickers=60, years=2, effect_pct_per_event=-20.0, hold=20,
                                   event_rate=0.01, vol=0.001, seed=1)
    assert set(P.columns) >= {"ticker", "date", "open", "high", "low", "close", "volume", "ev"}
    x = P[P.ticker == "S000"].reset_index(drop=True)
    t = int(np.flatnonzero(x.ev.values > 0)[0])
    assert x.close[t + 20] / x.close[t] - 1 < -0.10
```

- [ ] **Step 2:** `venv/bin/python -m pytest tests/test_rulecard_events.py -q` → FAIL (`make_event_panel` missing).

- [ ] **Step 3: Implement** (append to `synthetic.py`)

```python
def make_event_panel(n_tickers: int = 80, years: int = 4, effect_pct_per_event: float = 0.0,
                     hold: int = 20, event_rate: float = 0.005, vol: float = 0.02, seed: int = 0,
                     start: str = "2012-01-02", low_adv_boost: float | None = None) -> pd.DataFrame:
    """Random 0/1 events (column `ev`, known at that row's close); each event adds a drift of
    effect_pct_per_event spread evenly over the name's next `hold` sessions. low_adv_boost as in
    make_panel (even-numbered names trade 10x less value and carry the effect x boost)."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range(start, periods=252 * years)
    T = len(dates)
    frames = []
    for i in range(n_tickers):
        ev = rng.random(T) < event_rate
        ev[:30] = False
        low = low_adv_boost is not None and i % 2 == 0
        boost = low_adv_boost if low else 1.0
        volume = (5e6 if low else 5e7) if low_adv_boost is not None else 1e7
        drift = np.zeros(T)
        for t in np.flatnonzero(ev):
            drift[t + 1:t + 1 + hold] += effect_pct_per_event * boost / 100.0 / hold
        r = rng.normal(drift - vol ** 2 / 2, vol, T)
        close = 1000.0 * np.exp(np.cumsum(r))
        gap = np.exp(rng.normal(0, 0.002, T))
        open_ = np.r_[close[0], close[:-1]] * gap
        rngv = np.abs(rng.normal(0, vol, T)) + vol / 2
        hi = np.maximum(open_, close) * np.exp(rngv / 2)
        lo = np.minimum(open_, close) * np.exp(-rngv / 2)
        frames.append(pd.DataFrame({"ticker": f"S{i:03d}", "date": dates, "open": open_, "high": hi,
                                    "low": lo, "close": close, "volume": volume, "ev": ev.astype(float)}))
    return pd.concat(frames, ignore_index=True)


def ev_signal(panel: pd.DataFrame) -> pd.Series:
    return panel["ev"].astype(float)
```

- [ ] **Step 4:** re-run → PASS.
- [ ] **Step 5:** commit `feat(rulecard): synthetic event panel with planted post-event drift`.

### Task 2: `events.py` core (build events, positions, monthly records)

**Files:** Create `research/rulecard/events.py`. Test: `tests/test_rulecard_events.py`.

- [ ] **Step 1: Failing tests**

```python
from research.rulecard import engine, events
from research.rulecard.stats import nw_t

EVCARD = {"signal": {"hold_sessions": 20}, "costs": {"round_trip_pct": 0.60}}

def _pan(**kw):
    return engine.Panel(synthetic.make_event_panel(**kw))

def test_entry_next_open_exit_hth_close_and_stale():
    pan = _pan(n_tickers=60, years=2, event_rate=0.01, seed=2)
    E = events.build_events(pan, synthetic.ev_signal(pan.P), 20)
    T = E[E.tradeable]
    assert (T.entry_row == T.signal_row + 1).all()
    ok = ~T.stale
    assert (T.exit_row[ok] == T.signal_row[ok] + 20).all()
    last = pan.P.groupby("ticker").cumcount(ascending=False).values
    assert (last[T.exit_row[T.stale]] == 0).all()          # stale exits at the last row

def test_planted_anti_edge_is_recovered():
    pan = _pan(n_tickers=120, years=5, effect_pct_per_event=-3.0, event_rate=0.005, seed=4)
    months, _ = events.run_event_months(pan, synthetic.ev_signal(pan.P), EVCARD)
    prim = [m["primary"] for m in months if m.get("valid")]
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
    raw.loc[m, ["open", "high", "low", "close"]] *= 1.5     # +50% jump inside the hold
    pan = engine.Panel(raw)
    E = events.build_events(pan, synthetic.ev_signal(pan.P), 20)
    assert len(E[E.tradeable]) == len(E0[E0.tradeable])
    months, _ = events.run_event_months(pan, synthetic.ev_signal(pan.P), EVCARD)
    assert sum(r.get("big_moves_in_hold", 0) for r in months) >= 1
```

- [ ] **Step 2:** run → FAIL (module missing).

- [ ] **Step 3: Implement `research/rulecard/events.py`** (full file in the repository; key contract):
  - `build_events(pan, flags, hold, start=None, end=None) -> DataFrame`, with columns `ticker, signal_row,
    entry_row, exit_row, signal_date, entry_date, exit_date, tradeable, stale, adv_terc, px_terc`.
  - `run_event_months(pan, flags, card, start=None, end=None, with_returns=True) -> (list[dict], E)`.
  - Month keys: `month, formation, entry, exit, valid, reason?, events, not_tradeable_at_entry, univ,
    stale_exits, position_days, book_median`, plus, with returns, `primary, deployment, fp_adv_low/high,
    fp_price_low/high, zero_returns, big_moves_in_hold, max_abs_move_in_hold, uplift_net, turn_book,
    turn_univ, state`.
  - Month value = mean daily excess on position-days × sessions in month × 100.
  - Valid iff `position_days >= MIN_EVENT_DAYS (5)` and `book_median >= engine.MIN_UNIVERSE`.

- [ ] **Step 4:** run → PASS.
- [ ] **Step 5:** commit `feat(rulecard): event-time calendar-time engine (events.py)`.

### Task 3: placebo / random flags and event checks

- [ ] **Step 1: Failing tests**

```python
def test_placebo_keeps_per_date_count_and_is_null():
    pan = _pan(n_tickers=120, years=4, effect_pct_per_event=-3.0, event_rate=0.005, seed=6)
    f = synthetic.ev_signal(pan.P)
    p = events.placebo_flags(pan, f, seed=7)
    el = pan.eligible.values
    a = pd.Series((f.values > 0) & el).groupby(pan.P.date.values).sum()
    b = pd.Series(p.values > 0).groupby(pan.P.date.values).sum()
    assert (a == b).all()
    months, _ = events.run_event_months(pan, p, EVCARD)
    assert abs(nw_t([m["primary"] for m in months if m.get("valid")], 3)) < 3.0

def test_random_flags_rate_and_checks():
    pan = _pan(n_tickers=80, years=2, event_rate=0.01, seed=8)
    r = events.random_flags(pan, 0.02, seed=1)
    share = r[pan.eligible].mean()
    assert 0.015 < share < 0.025 and r[~pan.eligible].sum() == 0
    E = events.build_events(pan, synthetic.ev_signal(pan.P), 20)
    assert events.event_order_check(E)["status"] == "PASS"
    assert events.event_nondegenerate(pan, synthetic.ev_signal(pan.P))["status"] == "PASS"
    assert events.event_nondegenerate(pan, pd.Series(1.0, index=pan.P.index))["status"] == "FAIL"
```

- [ ] **Step 2–4:** implement `placebo_flags`, `random_flags`, `event_order_check`, `event_nondegenerate`
  in `events.py`, then run → PASS.
- [ ] **Step 5:** commit `feat(rulecard): event placebo, random flags and event checks`.

### Task 4: card validation for `formation: event`

**Files:** Modify `research/rulecard/card.py`, replacing the `month_end`-only check at l.155–157.

- [ ] **Step 1: Failing tests**

```python
from research.rulecard import card as cardmod
from tests.test_rulecard_engine import valid_card

def event_card():
    c = valid_card()
    c["tier"] = "N"; c["trials"] = {"n_trials": 1}; c.pop("monotonicity", None)
    c["signal"].update(formation="event", hold_sessions=20)
    c["portfolio"] = {"bucketing": "flag", "use": "avoid", "use_end": "high"}
    c["estimand"].update(primary_kind="bucket_minus_rest", aggregation="calendar_time")
    c["power"].update(event_rate=0.005, sigma_planning=1.0, literature_effect=4.0, n_months=40)
    c["hurdle"] = {"t_min": 3.0}
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
    c = event_card(); mut(c)
    with pytest.raises(cardmod.CardError, match=msg):
        cardmod.validate(c, strict=True)
```

- [ ] **Step 2:** run → FAIL.
- [ ] **Step 3:** implement with `FORMATIONS = {"month_end", "event"}`. For event, require an integer
  `hold_sessions >= 1`, `bucketing: flag`, `primary_kind: bucket_minus_rest` and
  `aggregation: calendar_time`. At strict, also require a numeric `power.event_rate` in (0, 0.5].
- [ ] **Step 4:** run this file plus `tests/test_rulecard_engine.py` → PASS.
- [ ] **Step 5:** commit `feat(rulecard): card validation for event formation`.

### Task 5: runner branches (compute, dry, power) + end-to-end

**Files:** Modify `research/rulecard/runner.py`.

- [ ] **Step 1: Failing tests**

```python
import textwrap, yaml
from research.rulecard import runner

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
    d = tmp_path / "RC-EV"; d.mkdir()
    c = event_card(); c["windows"] = {"split": "2014-06-01"}
    (d / "CARD.yaml").write_text(yaml.safe_dump(c, sort_keys=False))
    (d / "rule.py").write_text(EV_RULE)
    return d

def test_event_dry_reports_rate_without_returns(ev_dir):
    out = runner.dry(ev_dir / "CARD.yaml")
    assert 0.003 < out["event_rate"] < 0.007 and out["events_per_year"]
    assert all(c["status"] == "PASS" for c in out["checks"]), out["checks"]

def test_event_power_never_calls_signal(ev_dir, monkeypatch):
    import research.rulecard.runner as R
    real = R._load_module
    def guarded(p):
        m = real(p); m.signal = lambda *_: (_ for _ in ()).throw(AssertionError("signal called"))
        return m
    monkeypatch.setattr(R, "_load_module", guarded)
    out = runner.power(ev_dir / "CARD.yaml", seeds=3)
    assert out["signal_called"] is False and out["sigma_noise_floor"] > 0

def test_event_card_freeze_run_pass(ev_dir, tmp_path):
    runner.freeze(ev_dir / "CARD.yaml", "Owner test")
    out = runner.run(ev_dir / "CARD.yaml", tmp_path / "ledger.jsonl")
    assert all(c["status"] == "PASS" for c in out["checks"]), out["checks"]
    assert out["verdict"]["verdict"] == "PASS", out["verdict"]
```

- [ ] **Step 2:** run → FAIL.
- [ ] **Step 3:** in `runner.py`:
  - `_compute`: if the formation is `event`, run `events.run_event_months` for the months. Check dates =
    sorted unique signal dates of tradeable events. The checks are `prefix_invariance`,
    `traded_days_guard`, `event_nondegenerate` and `event_order_check`; with returns also
    `forward_returns_nontrivial`, `split_band` and `placebo` (on `placebo_flags`).
  - `dry`: add `events_per_year` and `event_rate` (events ÷ eligible rows in the window).
  - `power`: in event mode, use `random_flags` with `power.event_rate` (refuse if it is missing), never
    calling `signal()`.
- [ ] **Step 4:** run `tests/test_rulecard_*.py` → all PASS.
- [ ] **Step 5:** commit `feat(rulecard): runner support for event-time cards`.

### Task 6: RC-0002 card + rule + data fence

**Files:** Create `docs/research_programs/P-M/rulecards/RC-0002-FB-PRE2021/{CARD.yaml, rule.py}`. Test:
`tests/test_rulecard_events.py::test_rc0002_panel_is_pre2021_only`.

- [ ] **Step 1: Failing test**

```python
def test_rc0002_panel_is_pre2021_only(monkeypatch):
    import importlib.util
    p = ROOT / "docs/research_programs/P-M/rulecards/RC-0002-FB-PRE2021/rule.py"
    spec = importlib.util.spec_from_file_location("rc0002", p); m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    fake = synthetic.make_event_panel(n_tickers=3, years=12, start="2012-01-02").drop(columns="ev")
    monkeypatch.setattr(m, "load_extended_ohlcv", lambda: fake)
    P = m.load_panel({})
    assert P.date.max() < pd.Timestamp("2021-07-05")
    s = m.signal(engine.prepare(P))
    assert set(np.unique(s.values)) <= {0.0, 1.0}
```

- [ ] **Step 2–4:** write `rule.py`:
  - `load_panel` = `load_extended_ohlcv()` cut at `< 2021-07-05`.
  - `signal` = `(low < lo20) & (close > lo20)`, where `lo20` = the per-ticker rolling-20 min of `low`,
    shifted 1.

  Write `CARD.yaml` with the spec §2 values. Then run `cli validate` (lenient OK) → PASS.
- [ ] **Step 5:** commit `feat(P-M): RC-0002 failed-breakdown pre-2021 replication card`.

### Task 7: dry → power → freeze → run (real data)

- [ ] `venv/bin/python -m research.rulecard.cli dry <CARD>`. Copy `event_rate` into the card; check the
  events per year and valid months.
- [ ] `... cli power <CARD>`. Copy `sigma_noise_floor` and `months_valid` into `power`. If the result is
  inadmissible: add a `disposition` of NOT_TESTED_UNDERPOWERED, then stop (RC-0001 precedent).
- [ ] `... cli validate` strict → OK. Then `cli freeze --owner "Owner 2026-09-25 ('complete all path with
  your recommendation'), D-060"`, then `cli run`.
- [ ] Interpretation lines in VERDICT.md; DECISION_LOG D-060; HYPOTHESIS_REGISTRY row for HYP-PM-0012
  evidence; FAILURE_REGISTRY only if the verdict is FAIL; commit.
