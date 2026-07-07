# NR7 Edge-Generalization Study Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reproducible study that decides — against pre-registered thresholds — whether NR7 Breakout's +1.75%/trade edge generalizes beyond the 44 reporting-bar tickers, or is selection bias.

**Architecture:** A pure, fully-unit-tested aggregation module (`engine/nr7_study.py`) holds all statistics (cost normalization, trade-weighted pooling, chronological CV, regime stratification, threshold evaluation). A thin orchestration script (`scripts/nr7_generalization_study.py`) runs NR7 walk-forward across the liquid universe, labels each OOS trade with its entry regime, feeds the pure module, and writes a results doc + JSON. No production/scan-path code is touched.

**Tech Stack:** Python 3 stdlib + pandas, existing `engine.strategies.strategy_nr7_breakout`, `engine.walkforward_multi.walk_forward_split`, `engine.regime_filter.detect_regime`, `engine.liquidity.get_adv_value_30d`, `engine.exits.costs`. pytest for TDD.

---

## Trade record shape (used across all pure functions)

A study trade is a plain dict:
```python
{'ticker': 'BBCA', 'entry_date': '2025-03-14', 'raw_entry': 1000.0,
 'raw_exit': 1085.0, 'regime': 'BULL'}   # regime ∈ {'BULL','SIDEWAYS','BEAR'}
```
Net P&L is always derived from `raw_entry`/`raw_exit` via `round_trip_net_pct` —
never stored, so cost handling lives in exactly one place.

## Thresholds (pre-registered — do not change after seeing results)

```python
THRESHOLDS = {
    'min_net_exp':        0.50,   # %/trade net, the bar for "tradeable"
    't1_min_n':           300,    # universe pooled trade count
    't2_select_min':      5,      # min early trades for a ticker to be "selected"
    't2_min_n':           150,    # held-out late pooled trade count
    't2_min_retention':   0.50,   # late_exp / early_exp on selected tickers
    't3_min_n':           100,    # per-regime stratum trade count
}
```

---

### Task 1: Round-trip cost normalization (pure)

**Files:**
- Create: `engine/nr7_study.py`
- Test: `tests/test_nr7_study.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_nr7_study.py
import math
import pytest
import engine.nr7_study as ns


def test_round_trip_net_pct_applies_both_legs():
    # raw 100 -> 110 gross = +10%. Round-trip cost 0.60% (buy .25%, sell .35%).
    # buy_fill = 100*(1+.0015+.001)=100.25 ; sell_fill = 110*(1-.0025-.001)=109.615
    # net = (109.615-100.25)/100.25*100
    exp = (110*(1-0.0025-0.001) - 100*(1+0.0015+0.001)) / (100*(1+0.0015+0.001)) * 100
    assert ns.round_trip_net_pct(100.0, 110.0) == pytest.approx(exp, abs=1e-9)


def test_round_trip_net_pct_loss_is_more_negative_than_gross():
    # A flat trade (raw 100->100) must be negative after round-trip costs.
    assert ns.round_trip_net_pct(100.0, 100.0) < 0
    assert ns.round_trip_net_pct(100.0, 100.0) == pytest.approx(-0.599, abs=0.01)
```

- [ ] **Step 2: Run to verify failure**

Run: `./venv/bin/python -m pytest tests/test_nr7_study.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'engine.nr7_study'`

- [ ] **Step 3: Implement**

```python
# engine/nr7_study.py
"""NR7 edge-generalization study — pure statistics (audit Phase 4, first increment).

No DB, no I/O, no scheduler imports. Every number the study reports comes from
these functions so the methodology is unit-tested independent of a 5y backtest.
Net P&L is always full round-trip: costs applied to BOTH legs from raw prices.
"""
from engine.exits.costs import apply_costs


def round_trip_net_pct(raw_entry: float, raw_exit: float) -> float:
    """Net %/trade after full round-trip costs, from RAW prices.

    Applies the buy leg to entry and the sell leg to exit via the single cost
    authority (engine.exits.costs), so this does not trust any upstream cost
    handling. Long-only (BUY entry, SELL exit)."""
    buy_fill = apply_costs(raw_entry, 'BUY')
    sell_fill = apply_costs(raw_exit, 'SELL')
    return (sell_fill - buy_fill) / buy_fill * 100.0
```

- [ ] **Step 4: Run to verify pass**

Run: `./venv/bin/python -m pytest tests/test_nr7_study.py -q`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add engine/nr7_study.py tests/test_nr7_study.py
git commit -m "feat(study): NR7 round-trip cost normalization (Phase 4 study)"
```

---

### Task 2: Trade-weighted pool

**Files:**
- Modify: `engine/nr7_study.py`
- Test: `tests/test_nr7_study.py`

- [ ] **Step 1: Write the failing test**

```python
def _t(ticker, date, entry, exit_, regime='BULL'):
    return {'ticker': ticker, 'entry_date': date, 'raw_entry': entry,
            'raw_exit': exit_, 'regime': regime}


def test_pool_trade_weighted_and_win_rate():
    trades = [_t('A', '2025-01-01', 100, 110),   # net ~ +9.4%
              _t('A', '2025-01-02', 100, 90),    # net ~ -10.6%
              _t('B', '2025-01-03', 100, 100)]   # net ~ -0.6%
    r = ns.pool(trades)
    assert r['n'] == 3
    nets = [ns.round_trip_net_pct(100, 110), ns.round_trip_net_pct(100, 90),
            ns.round_trip_net_pct(100, 100)]
    assert r['exp_pct'] == pytest.approx(sum(nets) / 3, abs=1e-9)
    assert r['win_rate'] == pytest.approx(100 * 1 / 3, abs=1e-9)  # only 100->110 wins


def test_pool_empty_is_zero_n():
    r = ns.pool([])
    assert r == {'exp_pct': 0.0, 'n': 0, 'win_rate': 0.0}
```

- [ ] **Step 2: Run to verify failure**

Run: `./venv/bin/python -m pytest tests/test_nr7_study.py -k pool -q`
Expected: FAIL — `AttributeError: module 'engine.nr7_study' has no attribute 'pool'`

- [ ] **Step 3: Implement** (append to `engine/nr7_study.py`)

```python
def pool(trades) -> dict:
    """Trade-weighted pooled net expectancy over a list of study trades."""
    n = len(trades)
    if n == 0:
        return {'exp_pct': 0.0, 'n': 0, 'win_rate': 0.0}
    nets = [round_trip_net_pct(t['raw_entry'], t['raw_exit']) for t in trades]
    wins = sum(1 for x in nets if x > 0)
    return {'exp_pct': sum(nets) / n, 'n': n, 'win_rate': 100.0 * wins / n}
```

- [ ] **Step 4: Run to verify pass**

Run: `./venv/bin/python -m pytest tests/test_nr7_study.py -k pool -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add engine/nr7_study.py tests/test_nr7_study.py
git commit -m "feat(study): trade-weighted pool (Phase 4 study)"
```

---

### Task 3: Chronological CV split + ticker selection

**Files:**
- Modify: `engine/nr7_study.py`
- Test: `tests/test_nr7_study.py`

- [ ] **Step 1: Write the failing test**

```python
def test_cv_split_partitions_by_date():
    trades = [_t('A', '2024-01-01', 100, 110), _t('A', '2025-06-01', 100, 90)]
    early, late = ns.cv_split(trades, '2025-01-01')
    assert [t['entry_date'] for t in early] == ['2024-01-01']
    assert [t['entry_date'] for t in late] == ['2025-06-01']


def test_select_positive_tickers_needs_min_trades_and_positive():
    # A: 6 early trades, net positive. B: positive but only 2 trades (below min).
    early = ([_t('A', '2024-01-0%d' % i, 100, 110) for i in range(1, 7)]
             + [_t('B', '2024-02-01', 100, 110), _t('B', '2024-02-02', 100, 110)])
    picked = ns.select_positive_tickers(early, min_trades=5)
    assert picked == {'A'}


def test_select_excludes_negative_ticker():
    early = [_t('C', '2024-01-0%d' % i, 100, 90) for i in range(1, 7)]  # all losers
    assert ns.select_positive_tickers(early, min_trades=5) == set()
```

- [ ] **Step 2: Run to verify failure**

Run: `./venv/bin/python -m pytest tests/test_nr7_study.py -k "cv_split or select" -q`
Expected: FAIL — attributes `cv_split` / `select_positive_tickers` missing

- [ ] **Step 3: Implement** (append)

```python
def cv_split(trades, boundary_date: str):
    """Partition trades into (early, late) by entry_date < boundary_date."""
    early = [t for t in trades if t['entry_date'] < boundary_date]
    late = [t for t in trades if t['entry_date'] >= boundary_date]
    return early, late


def select_positive_tickers(trades, min_trades: int) -> set:
    """Tickers with >= min_trades and positive pooled net expectancy."""
    by_ticker = {}
    for t in trades:
        by_ticker.setdefault(t['ticker'], []).append(t)
    picked = set()
    for ticker, ts in by_ticker.items():
        if len(ts) >= min_trades and pool(ts)['exp_pct'] > 0:
            picked.add(ticker)
    return picked
```

- [ ] **Step 4: Run to verify pass**

Run: `./venv/bin/python -m pytest tests/test_nr7_study.py -k "cv_split or select" -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add engine/nr7_study.py tests/test_nr7_study.py
git commit -m "feat(study): chronological CV split + ticker selection (Phase 4 study)"
```

---

### Task 4: Regime stratification

**Files:**
- Modify: `engine/nr7_study.py`
- Test: `tests/test_nr7_study.py`

- [ ] **Step 1: Write the failing test**

```python
def test_stratify_by_regime_buckets_and_pools():
    trades = [_t('A', '2025-01-01', 100, 110, 'BULL'),
              _t('A', '2025-01-02', 100, 90, 'SIDEWAYS'),
              _t('B', '2025-01-03', 100, 108, 'SIDEWAYS')]
    strata = ns.stratify_by_regime(trades)
    assert set(strata) == {'BULL', 'SIDEWAYS'}
    assert strata['BULL']['n'] == 1
    assert strata['SIDEWAYS']['n'] == 2
    assert strata['SIDEWAYS']['exp_pct'] == pytest.approx(
        (ns.round_trip_net_pct(100, 90) + ns.round_trip_net_pct(100, 108)) / 2, abs=1e-9)
```

- [ ] **Step 2: Run to verify failure**

Run: `./venv/bin/python -m pytest tests/test_nr7_study.py -k stratify -q`
Expected: FAIL — `stratify_by_regime` missing

- [ ] **Step 3: Implement** (append)

```python
def stratify_by_regime(trades) -> dict:
    """Pool net expectancy separately per entry-regime label."""
    buckets = {}
    for t in trades:
        buckets.setdefault(t['regime'], []).append(t)
    return {regime: pool(ts) for regime, ts in buckets.items()}
```

- [ ] **Step 4: Run to verify pass**

Run: `./venv/bin/python -m pytest tests/test_nr7_study.py -k stratify -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add engine/nr7_study.py tests/test_nr7_study.py
git commit -m "feat(study): regime stratification (Phase 4 study)"
```

---

### Task 5: Threshold evaluation + decision (boundary-tested)

**Files:**
- Modify: `engine/nr7_study.py`
- Test: `tests/test_nr7_study.py`

- [ ] **Step 1: Write the failing test**

```python
def test_evaluate_widen_universe_when_t1_and_t2_pass():
    t1 = {'exp_pct': 0.9, 'n': 400, 'win_rate': 55}
    t2 = {'late_exp': 0.8, 'late_n': 200, 'early_exp': 1.2, 'retention': 0.667}
    t3 = {'SIDEWAYS': {'exp_pct': 0.2, 'n': 120, 'win_rate': 45},
          'BULL': {'exp_pct': 1.5, 'n': 150, 'win_rate': 60}}
    r = ns.evaluate(t1, t2, t3, ns.THRESHOLDS)
    assert r['T1']['pass'] is True
    assert r['T2']['pass'] is True
    assert r['widen_universe'] is True
    assert r['T3']['SIDEWAYS']['pass'] is False    # 0.2 < 0.50
    assert r['widen_sideways'] is False
    assert 'WIDEN-UNIVERSE' in r['decision']


def test_evaluate_do_not_widen_when_t2_fails_retention():
    t1 = {'exp_pct': 0.9, 'n': 400, 'win_rate': 55}
    t2 = {'late_exp': 0.55, 'late_n': 200, 'early_exp': 1.5, 'retention': 0.367}  # <0.50
    t3 = {'SIDEWAYS': {'exp_pct': 0.6, 'n': 120, 'win_rate': 48}}
    r = ns.evaluate(t1, t2, t3, ns.THRESHOLDS)
    assert r['T2']['pass'] is False
    assert r['widen_universe'] is False
    assert r['widen_sideways'] is True             # SIDEWAYS stratum still passes
    assert r['decision'] == 'WIDEN-SIDEWAYS'


def test_evaluate_t1_boundary_exact_threshold_passes():
    t1 = {'exp_pct': 0.50, 'n': 300, 'win_rate': 50}   # exactly at both bars
    t2 = {'late_exp': 0.0, 'late_n': 0, 'early_exp': 1.0, 'retention': 0.0}
    r = ns.evaluate(t1, t2, {}, ns.THRESHOLDS)
    assert r['T1']['pass'] is True
    assert r['widen_universe'] is False            # T2 fails → no widen
    assert r['decision'] == 'DO-NOT-WIDEN'
```

- [ ] **Step 2: Run to verify failure**

Run: `./venv/bin/python -m pytest tests/test_nr7_study.py -k evaluate -q`
Expected: FAIL — `evaluate` / `THRESHOLDS` missing

- [ ] **Step 3: Implement** (append)

```python
THRESHOLDS = {
    'min_net_exp':      0.50,
    't1_min_n':         300,
    't2_select_min':    5,
    't2_min_n':         150,
    't2_min_retention': 0.50,
    't3_min_n':         100,
}


def evaluate(t1, t2, t3, thr) -> dict:
    """Apply pre-registered thresholds → PASS/FAIL per test + widen decision.

    t1: pool dict for the full liquid universe.
    t2: {'late_exp','late_n','early_exp','retention'} on early-selected tickers.
    t3: {regime: pool dict}.
    """
    me = thr['min_net_exp']
    t1_pass = t1['exp_pct'] >= me and t1['n'] >= thr['t1_min_n']
    t2_pass = (t2['late_exp'] >= me and t2['late_n'] >= thr['t2_min_n']
               and t2['retention'] >= thr['t2_min_retention'])
    t3_out = {}
    for regime, p in (t3 or {}).items():
        t3_out[regime] = {**p, 'pass': p['exp_pct'] >= me and p['n'] >= thr['t3_min_n']}

    widen_universe = t1_pass and t2_pass
    widen_sideways = bool(t3_out.get('SIDEWAYS', {}).get('pass'))
    parts = []
    if widen_universe:
        parts.append('WIDEN-UNIVERSE')
    if widen_sideways:
        parts.append('WIDEN-SIDEWAYS')
    decision = '+'.join(parts) if parts else 'DO-NOT-WIDEN'

    return {
        'T1': {**t1, 'pass': t1_pass},
        'T2': {**t2, 'pass': t2_pass},
        'T3': t3_out,
        'widen_universe': widen_universe,
        'widen_sideways': widen_sideways,
        'decision': decision,
    }
```

- [ ] **Step 4: Run to verify pass**

Run: `./venv/bin/python -m pytest tests/test_nr7_study.py -q`
Expected: PASS (all study unit tests green)

- [ ] **Step 5: Commit**

```bash
git add engine/nr7_study.py tests/test_nr7_study.py
git commit -m "feat(study): threshold evaluation + widen decision (Phase 4 study)"
```

---

### Task 6: Orchestration script + smoke test

**Files:**
- Create: `scripts/nr7_generalization_study.py`
- Test: `tests/test_nr7_study_script.py`

**Grounding note:** Before writing, open `engine/walkforward_multi.py:272` (`run_walk_forward`)
and confirm the per-window strategy call convention: the study MUST run
`strategy_nr7_breakout` on the **OOS test window** (`w['test']`) exactly as
`run_walk_forward` does, for comparability with the existing `wf_edge`. The keys
returned by `walk_forward_split` are `{'train','test','window',...}`.

- [ ] **Step 1: Write the failing smoke test**

```python
# tests/test_nr7_study_script.py
"""Thin wiring smoke test — proves the orchestration runs end-to-end on a tiny
slice. Does NOT assert statistics (that's the pure module's job)."""
import pandas as pd
import scripts.nr7_generalization_study as study


def _synth_df(ticker, start='2020-01-01', n=400, base=1000.0):
    dates = pd.date_range(start, periods=n, freq='B')
    # gentle uptrend with noise so NR7 can find some setups
    import numpy as np
    rng = np.random.default_rng(abs(hash(ticker)) % 2**32)
    close = base * (1 + 0.0003 * np.arange(n) + rng.normal(0, 0.01, n)).cumprod()
    high = close * 1.01
    low = close * 0.99
    return pd.DataFrame({'date': dates.astype(str), 'open': close,
                         'high': high, 'low': low, 'close': close,
                         'volume': 1_000_000})


def test_collect_trades_for_ticker_returns_study_trades():
    df = _synth_df('SMOKE')
    trades = study.collect_trades_for_ticker('SMOKE', df)
    # shape contract only — every trade has the required keys and valid regime
    for t in trades:
        assert set(t) >= {'ticker', 'entry_date', 'raw_entry', 'raw_exit', 'regime'}
        assert t['regime'] in ('BULL', 'SIDEWAYS', 'BEAR')
        assert t['raw_entry'] > 0 and t['raw_exit'] > 0
```

- [ ] **Step 2: Run to verify failure**

Run: `./venv/bin/python -m pytest tests/test_nr7_study_script.py -q`
Expected: FAIL — module/function missing

- [ ] **Step 3: Implement the script**

```python
#!/usr/bin/env python3
"""NR7 edge-generalization study runner (audit Phase 4, first increment).

Runs NR7 walk-forward across the liquid universe, labels each OOS trade with its
entry regime, feeds engine.nr7_study, and writes a results doc + JSON. Read-only
w.r.t. production: creates no live-path changes, only the results file.
"""
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

from data.db import connect as db_connect
from engine.liquidity import get_adv_value_30d, VALUE_LIQ_MIN_IDR
from engine.strategies import strategy_nr7_breakout
from engine.walkforward_multi import walk_forward_split
from engine.regime_filter import detect_regime
from engine.exits.costs import COMMISSION_SELL, SLIPPAGE
import engine.nr7_study as ns

DB_PATH = os.getenv('DB_PATH', os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), 'data', 'walkforward.db'))
RESULTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       'docs', 'superpowers', 'results',
                       '2026-07-07-nr7-generalization-study.md')
_SELL_ADJ = 1.0 - COMMISSION_SELL - SLIPPAGE   # invert strategy's SELL-leg cost


def _regime_at(full_df: pd.DataFrame, entry_date: str) -> str:
    """Regime from trailing data only (<= entry_date), no look-ahead."""
    hist = full_df[full_df['date'] <= entry_date].tail(250)
    if len(hist) < 30:
        return 'SIDEWAYS'
    return detect_regime(hist.reset_index(drop=True))


def collect_trades_for_ticker(ticker: str, df: pd.DataFrame) -> list:
    """NR7 OOS trades for one ticker as study-trade dicts (raw prices + regime).

    strategy_nr7_breakout stores raw entry but SELL-cost-adjusted exit; we invert
    that one adjustment to recover raw_exit, so nr7_study applies full round-trip
    costs from raw prices (single cost authority)."""
    df = df.sort_values('date').reset_index(drop=True)
    out = []
    for w in walk_forward_split(df, train_months=12, test_months=3):
        test_df = w['test']
        if len(test_df) < 25:
            continue
        res = strategy_nr7_breakout(test_df)
        for tr in res.get('trades', []):
            raw_exit = tr.exit_price / _SELL_ADJ
            out.append({
                'ticker': ticker,
                'entry_date': str(tr.entry_date)[:10],
                'raw_entry': float(tr.entry_price),
                'raw_exit': float(raw_exit),
                'regime': _regime_at(df, str(tr.entry_date)[:10]),
            })
    return out


def liquid_universe(conn, as_of: str) -> list:
    tickers = [r[0] for r in conn.execute(
        "SELECT DISTINCT ticker FROM ohlcv WHERE ticker != 'IHSG'")]
    liq = []
    for t in tickers:
        adv = get_adv_value_30d(conn, t, as_of)
        if adv is not None and adv >= VALUE_LIQ_MIN_IDR:
            liq.append(t)
    return liq


def run():
    conn = db_connect(DB_PATH)
    as_of = conn.execute("SELECT MAX(date) FROM ohlcv").fetchone()[0]
    universe = liquid_universe(conn, as_of)
    all_trades = []
    for t in universe:
        df = pd.read_sql(
            "SELECT date, open, high, low, close, volume FROM ohlcv "
            "WHERE ticker=? ORDER BY date", conn, params=(t,))
        if len(df) < 300:
            continue
        all_trades.extend(collect_trades_for_ticker(t, df))
    conn.close()

    # boundary = midpoint of the trade-date span (chronological CV)
    dates = sorted(t['entry_date'] for t in all_trades)
    boundary = dates[len(dates) // 2] if dates else '2099-01-01'

    t1 = ns.pool(all_trades)
    early, late = ns.cv_split(all_trades, boundary)
    picked = ns.select_positive_tickers(early, ns.THRESHOLDS['t2_select_min'])
    late_sel = [x for x in late if x['ticker'] in picked]
    early_sel = [x for x in early if x['ticker'] in picked]
    late_pool, early_pool = ns.pool(late_sel), ns.pool(early_sel)
    retention = (late_pool['exp_pct'] / early_pool['exp_pct']
                 if early_pool['exp_pct'] > 0 else 0.0)
    t2 = {'late_exp': late_pool['exp_pct'], 'late_n': late_pool['n'],
          'early_exp': early_pool['exp_pct'], 'retention': retention}
    t3 = ns.stratify_by_regime(all_trades)
    verdict = ns.evaluate(t1, t2, t3, ns.THRESHOLDS)

    _write_results(as_of, len(universe), boundary, t1, t2, t3, verdict)
    print("DECISION:", verdict['decision'])
    return verdict


def _write_results(as_of, n_universe, boundary, t1, t2, t3, verdict):
    os.makedirs(os.path.dirname(RESULTS), exist_ok=True)
    lines = [
        "# NR7 Edge-Generalization Study — Results", "",
        f"Run: {datetime.now().isoformat(timespec='seconds')} | corpus as-of {as_of} | "
        f"liquid universe {n_universe} tickers | CV boundary {boundary}", "",
        "## T1 — universe pooled (net of round-trip costs)",
        f"- exp {t1['exp_pct']:+.3f}%/trade | N {t1['n']} | win {t1['win_rate']:.1f}% "
        f"| **{'PASS' if verdict['T1']['pass'] else 'FAIL'}** "
        f"(bar ≥ +0.50%, N ≥ 300)", "",
        "## T2 — selection / chronological CV",
        f"- early-selected tickers: late exp {t2['late_exp']:+.3f}% | late N {t2['late_n']} "
        f"| early exp {t2['early_exp']:+.3f}% | retention {t2['retention']:.2f} "
        f"| **{'PASS' if verdict['T2']['pass'] else 'FAIL'}** "
        f"(bar ≥ +0.50%, N ≥ 150, retention ≥ 0.50)", "",
        "## T3 — regime strata",
    ]
    for regime, p in verdict['T3'].items():
        lines.append(f"- {regime}: exp {p['exp_pct']:+.3f}% | N {p['n']} | win {p['win_rate']:.1f}% "
                     f"| **{'PASS' if p['pass'] else 'FAIL'}** (bar ≥ +0.50%, N ≥ 100)")
    lines += ["", f"## DECISION: **{verdict['decision']}**", "",
              "```json", json.dumps(verdict, indent=2), "```", ""]
    with open(RESULTS, 'w') as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    run()
```

- [ ] **Step 4: Run to verify pass**

Run: `./venv/bin/python -m pytest tests/test_nr7_study_script.py -q`
Expected: PASS (1 passed) — if `collect_trades_for_ticker` yields 0 trades on the
synthetic df, the loop body simply doesn't execute and the test still passes
(shape contract on whatever trades exist). If it errors on `walk_forward_split`
keys, fix the key names to match the grounded API before proceeding.

- [ ] **Step 5: Commit**

```bash
git add scripts/nr7_generalization_study.py tests/test_nr7_study_script.py
git commit -m "feat(study): NR7 study orchestration + smoke test (Phase 4 study)"
```

---

### Task 7: Run the study for real → results doc + verdict

**Files:**
- Create (generated): `docs/superpowers/results/2026-07-07-nr7-generalization-study.md`

- [ ] **Step 1: Run the study against the prod corpus**

Run: `./venv/bin/python scripts/nr7_generalization_study.py`
Expected: prints `DECISION: <WIDEN-UNIVERSE|WIDEN-SIDEWAYS|...|DO-NOT-WIDEN>` and
writes the results doc. Runtime ≈ 1–3 min (liquid universe × ~16 windows).

- [ ] **Step 2: Sanity-check the output**

Run: `sed -n '1,40p' docs/superpowers/results/2026-07-07-nr7-generalization-study.md`
Expected: three test tables populated with real numbers, each PASS/FAIL, and a
DECISION line. Confirm N in T1 is plausibly large (hundreds+), and that the
regime strata sum (roughly) to the universe trade count.

- [ ] **Step 3: Commit the results**

```bash
git add docs/superpowers/results/2026-07-07-nr7-generalization-study.md
git commit -m "docs(study): NR7 generalization study results + verdict (Phase 4)"
```

---

### Task 8: Regression + finish

- [ ] **Step 1: Full suite**

Run: `./venv/bin/python -m pytest -q`
Expected: baseline (≈1070 passed) + the new study tests, 3 skipped, no new failures.

- [ ] **Step 2: Finish the branch**

Use **superpowers:finishing-a-development-branch**: push, PR to `master`, wait CI,
manual merge. **No app restart / prod-branch deploy needed** — this increment adds
only research code (engine/nr7_study.py, scripts/, tests/, results doc) and touches
no live path, so nothing to activate. Merging to master is the full deploy.

- [ ] **Step 3: Report the verdict + recommend the next increment**

Summarize the DECISION to the user. If WIDEN-*, the next increment is the SHADOW
widening rollout (its own spec). If DO-NOT-WIDEN, recommend pivoting to Phase-4
fallback (hunt a second, uncorrelated edge — e.g. 4.5 ORB), and record that NR7's
44-name edge is selection-biased.

---

## Self-Review Notes

- **Spec coverage:** engine/nr7_study.py pure module (T1 `pool`, T2 `cv_split`+
  `select_positive_tickers`, T3 `stratify_by_regime`, `evaluate`+`THRESHOLDS`,
  `round_trip_net_pct`) — Tasks 1–5. Orchestration + regime labelling + liquid
  universe + results/JSON — Task 6. Real run + verdict — Task 7. All spec
  deliverables mapped.
- **Cost handling:** spec says "apply both legs, don't trust the strategy's
  SELL-only deduction" → `round_trip_net_pct` works from RAW prices; orchestration
  recovers `raw_exit` by inverting the strategy's known SELL adjustment
  (`/_SELL_ADJ`). Single cost authority (`engine.exits.costs`) throughout.
- **No look-ahead:** `_regime_at` uses only `date <= entry_date` trailing data.
- **Type consistency:** trade dict keys `{ticker, entry_date, raw_entry, raw_exit,
  regime}` identical across every function and test; `pool` return
  `{exp_pct, n, win_rate}` used consistently by CV, stratify, evaluate.
- **No production changes:** only new files; `_edge_selectable`,
  `_REGIME_STRATEGY_MAP`, scan path untouched (spec "out of scope").
- **Placeholder scan:** all steps carry real code/commands; the one grounding note
  (verify `run_walk_forward` per-window convention) is a read-check, not a
  deferred implementation.
