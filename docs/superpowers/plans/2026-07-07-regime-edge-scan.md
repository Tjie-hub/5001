# Regime-Conditional Edge Scan Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Scan all 14 roster strategies × 3 regimes for a positive, persistent OOS edge (especially SIDEWAYS), reusing the NR7 study's statistics — producing a ranked CONFIRMED/PROMISING candidate list or a decisive "roster has none".

**Architecture:** Reuse `engine/nr7_study.py` (pure stats) unchanged. One new orchestration script `scripts/regime_edge_scan.py` generalizes the NR7 trade collector to any strategy function, loops `STRATEGY_FUNCS` × the liquid universe, builds a strategy×regime matrix, runs a cell-scaled CV persistence test on cells that clear the regime bar, and writes a results doc. Research only — no production/scan-path change.

**Tech Stack:** Python 3 + pandas; `engine.nr7_study`, `engine.walkforward_multi` (`STRATEGY_FUNCS`, `walk_forward_split`), `engine.regime_filter.detect_regime`, `engine.liquidity`, `engine.exits.costs`. pytest for TDD.

---

## Reused, unchanged

`engine/nr7_study.py`: `round_trip_net_pct`, `pool`, `cv_split`,
`select_positive_tickers`, `stratify_by_regime`, `THRESHOLDS`. Covered by
`tests/test_nr7_study.py` — do NOT duplicate those tests.

## Study-trade shape (identical to NR7 study, plus `strategy`)

```python
{'strategy': 'vwap_reversion', 'ticker': 'BBCA', 'entry_date': '2025-03-14',
 'raw_entry': 1000.0, 'raw_exit': 1085.0, 'regime': 'SIDEWAYS'}
```

## Scan-local constant (pre-registered)

`T2_MIN_N = 60` — cell-scaled late-CV sample floor (universe uses 150; a single
regime cell is much smaller). Not tuned after seeing results.

---

### Task 1: Generalized per-strategy trade collector

**Files:**
- Create: `scripts/regime_edge_scan.py`
- Test: `tests/test_regime_edge_scan.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_regime_edge_scan.py
"""Wiring tests for the regime-conditional edge scan (Phase 4 second increment).
Statistics are the pure module's job (tests/test_nr7_study.py) — here we test the
generalized collector's shape contract and the scan matrix wiring only."""
import numpy as np
import pandas as pd

import scripts.regime_edge_scan as scan
from engine.strategies import strategy_vwap_reversion, strategy_vwma_breakout_pullback


def _synth_df(ticker, start='2019-01-01', n=500, base=1000.0):
    dates = pd.date_range(start, periods=n, freq='B')
    rng = np.random.default_rng(abs(hash(ticker)) % 2**32)
    close = base * (1 + 0.0002 * np.arange(n) + rng.normal(0, 0.015, n)).cumprod()
    return pd.DataFrame({'date': dates.astype(str), 'open': close,
                         'high': close * 1.015, 'low': close * 0.985,
                         'close': close, 'volume': 1_000_000})


def test_collect_trades_for_strategy_shape_contract():
    df = _synth_df('SMOKE')
    trades = scan.collect_trades_for_strategy(
        strategy_vwap_reversion, 'vwap_reversion', 'SMOKE', df)
    for t in trades:
        assert set(t) >= {'strategy', 'ticker', 'entry_date',
                          'raw_entry', 'raw_exit', 'regime'}
        assert t['strategy'] == 'vwap_reversion'
        assert t['ticker'] == 'SMOKE'
        assert t['regime'] in ('BULL', 'SIDEWAYS', 'BEAR')
        assert t['raw_entry'] > 0 and t['raw_exit'] > 0


def test_collect_handles_vwma_no_filters_signature():
    # strategy_vwma_breakout_pullback takes no `filters` kwarg — must not raise.
    df = _synth_df('VWMA')
    trades = scan.collect_trades_for_strategy(
        strategy_vwma_breakout_pullback, 'VWMA Breakout Pullback', 'VWMA', df)
    assert isinstance(trades, list)
```

- [ ] **Step 2: Run to verify failure**

Run: `./venv/bin/python -m pytest tests/test_regime_edge_scan.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.regime_edge_scan'`

- [ ] **Step 3: Implement the collector (file header + collector)**

```python
#!/usr/bin/env python3
"""Regime-conditional edge scan (audit Phase 4, second increment).

Runs every roster strategy through walk-forward across the liquid universe,
labels each OOS trade's entry regime, and classifies each (strategy, regime)
cell CONFIRMED / PROMISING / REJECTED against pre-registered thresholds. Reuses
engine.nr7_study for all statistics. Read-only w.r.t. production.
"""
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

from data.db import connect as db_connect
from engine.liquidity import get_adv_value_30d, VALUE_LIQ_MIN_IDR
from engine.walkforward_multi import STRATEGY_FUNCS, walk_forward_split
from engine.regime_filter import detect_regime
from engine.exits.costs import COMMISSION_SELL, SLIPPAGE
import engine.nr7_study as ns

DB_PATH = os.getenv('DB_PATH', os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), 'data', 'walkforward.db'))
RESULTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       'docs', 'superpowers', 'results',
                       '2026-07-07-regime-edge-scan.md')

WARMUP_BARS = 60                       # matches run_walk_forward (wf_edge parity)
_SELL_ADJ = 1.0 - COMMISSION_SELL - SLIPPAGE
T2_MIN_N = 60                          # cell-scaled late-CV sample floor
_VWMA_NAME = 'VWMA Breakout Pullback'  # the one no-`filters` strategy


def _regime_at(full_df: pd.DataFrame, entry_date: str) -> str:
    hist = full_df[full_df['date'] <= entry_date].tail(250)
    if len(hist) < 30:
        return 'SIDEWAYS'
    return detect_regime(hist.reset_index(drop=True))


def collect_trades_for_strategy(strategy_fn, name: str, ticker: str,
                                df: pd.DataFrame) -> list:
    """OOS trades for one (strategy, ticker) as study-trade dicts.

    Mirrors run_walk_forward: 60-bar warmup tail per test window, drop trades
    entered before test_start. Recovers raw_exit by inverting the strategy's
    SELL-leg cost so nr7_study applies full round-trip costs from raw prices."""
    df = df.sort_values('date').reset_index(drop=True)
    out = []
    for w in walk_forward_split(df, train_months=12, test_months=3):
        train_df, test_df, test_start = w['train'], w['test'], w['test_start']
        if len(test_df) < 25:
            continue
        warmup = train_df.tail(WARMUP_BARS) if len(train_df) >= WARMUP_BARS else train_df
        extended = pd.concat([warmup, test_df], ignore_index=True)
        if name == _VWMA_NAME:
            res = strategy_fn(extended)          # takes no filters kwarg
        else:
            res = strategy_fn(extended, filters=None)
        for tr in res.get('trades', []):
            entry = str(tr.entry_date)[:10]
            if entry < test_start:
                continue
            out.append({
                'strategy': name,
                'ticker': ticker,
                'entry_date': entry,
                'raw_entry': float(tr.entry_price),
                'raw_exit': float(tr.exit_price) / _SELL_ADJ,
                'regime': _regime_at(df, entry),
            })
    return out
```

- [ ] **Step 4: Run to verify pass**

Run: `./venv/bin/python -m pytest tests/test_regime_edge_scan.py -q`
Expected: PASS (2 passed). If `strategy_fn(extended, filters=None)` raises a
signature error for a strategy other than VWMA, that strategy has a different
signature — inspect it and extend the special-case branch. (Grounded: all
`STRATEGY_FUNCS` take `filters` except `strategy_vwma_breakout_pullback`, per
`run_walk_forward` in engine/walkforward_multi.py.)

- [ ] **Step 5: Commit**

```bash
git add scripts/regime_edge_scan.py tests/test_regime_edge_scan.py
git commit -m "feat(scan): generalized per-strategy trade collector (Phase 4 regime scan)"
```

---

### Task 2: Cell CV + three-state classification

**Files:**
- Modify: `scripts/regime_edge_scan.py`
- Test: `tests/test_regime_edge_scan.py`

- [ ] **Step 1: Write the failing tests**

```python
def _mk(ticker, date, entry, exit_, regime):
    return {'strategy': 'X', 'ticker': ticker, 'entry_date': date,
            'raw_entry': entry, 'raw_exit': exit_, 'regime': regime}


def test_classify_cell_rejected_when_regime_bar_fails():
    # Cell exp below +0.50% bar → REJECTED regardless of CV.
    cell = [_mk('A', '2024-01-0%d' % i, 100, 100, 'SIDEWAYS') for i in range(1, 9)]
    r = scan.classify_cell(cell, boundary='2024-06-01')
    assert r['state'] == 'REJECTED'


def test_classify_cell_promising_when_thin_late_sample():
    # Strong positive regime edge, persists early→late, but late N < 60.
    early = [_mk('A', '2023-01-%02d' % (i + 1), 100, 112, 'SIDEWAYS') for i in range(60)]
    late = [_mk('A', '2024-07-%02d' % (i + 1), 100, 112, 'SIDEWAYS') for i in range(20)]
    r = scan.classify_cell(early + late, boundary='2024-01-01')
    assert r['regime_pass'] is True
    assert r['state'] == 'PROMISING'      # late_n 20 < 60, retention high
    assert r['late_n'] == 20


def test_classify_cell_confirmed_when_persistent_and_enough_late():
    early = [_mk('A', '2023-%02d-01' % (m + 1), 100, 110, 'BULL') for m in range(12)] * 6
    late = [_mk('A', '2024-%02d-02' % ((i % 12) + 1), 100, 110, 'BULL') for i in range(70)]
    r = scan.classify_cell(early + late, boundary='2024-01-01')
    assert r['regime_pass'] is True
    assert r['late_n'] >= 60
    assert r['state'] == 'CONFIRMED'
```

- [ ] **Step 2: Run to verify failure**

Run: `./venv/bin/python -m pytest tests/test_regime_edge_scan.py -k classify -q`
Expected: FAIL — `classify_cell` missing

- [ ] **Step 3: Implement** (append to `scripts/regime_edge_scan.py`)

```python
def classify_cell(cell_trades, boundary: str) -> dict:
    """Classify one (strategy, regime) cell → CONFIRMED / PROMISING / REJECTED.

    Regime bar: cell pooled exp >= 0.50% net and N >= 100.
    CV: early-positive tickers' late pooled exp, retention vs their early exp.
    """
    me = ns.THRESHOLDS['min_net_exp']
    cell_pool = ns.pool(cell_trades)
    regime_pass = cell_pool['exp_pct'] >= me and cell_pool['n'] >= ns.THRESHOLDS['t3_min_n']

    early, late = ns.cv_split(cell_trades, boundary)
    picked = ns.select_positive_tickers(early, ns.THRESHOLDS['t2_select_min'])
    late_sel = [t for t in late if t['ticker'] in picked]
    early_sel = [t for t in early if t['ticker'] in picked]
    late_pool, early_pool = ns.pool(late_sel), ns.pool(early_sel)
    retention = (late_pool['exp_pct'] / early_pool['exp_pct']
                 if early_pool['exp_pct'] > 0 else 0.0)

    persistent = (retention >= ns.THRESHOLDS['t2_min_retention']
                  and late_pool['exp_pct'] > 0)
    if not regime_pass:
        state = 'REJECTED'
    elif persistent and late_pool['exp_pct'] >= me and late_pool['n'] >= T2_MIN_N:
        state = 'CONFIRMED'
    elif persistent:
        state = 'PROMISING'
    else:
        state = 'REJECTED'

    return {
        'state': state, 'regime_pass': regime_pass,
        'exp_pct': cell_pool['exp_pct'], 'n': cell_pool['n'],
        'win_rate': cell_pool['win_rate'],
        'late_exp': late_pool['exp_pct'], 'late_n': late_pool['n'],
        'early_exp': early_pool['exp_pct'], 'retention': retention,
    }
```

- [ ] **Step 4: Run to verify pass**

Run: `./venv/bin/python -m pytest tests/test_regime_edge_scan.py -k classify -q`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add scripts/regime_edge_scan.py tests/test_regime_edge_scan.py
git commit -m "feat(scan): cell CV + CONFIRMED/PROMISING/REJECTED classify (Phase 4 regime scan)"
```

---

### Task 3: Scan driver (matrix build) + smoke test

**Files:**
- Modify: `scripts/regime_edge_scan.py`
- Test: `tests/test_regime_edge_scan.py`

- [ ] **Step 1: Write the failing smoke test**

```python
def test_build_matrix_smoke_two_strategies():
    dfs = {'AAA': _synth_df('AAA'), 'BBB': _synth_df('BBB')}
    strategies = {'vwap_reversion': strategy_vwap_reversion}
    matrix = scan.build_matrix(strategies, dfs)
    # matrix keyed by strategy → {regime → classify_cell dict}
    assert 'vwap_reversion' in matrix
    for regime, cell in matrix['vwap_reversion'].items():
        assert regime in ('BULL', 'SIDEWAYS', 'BEAR')
        assert cell['state'] in ('CONFIRMED', 'PROMISING', 'REJECTED')
```

- [ ] **Step 2: Run to verify failure**

Run: `./venv/bin/python -m pytest tests/test_regime_edge_scan.py -k build_matrix -q`
Expected: FAIL — `build_matrix` missing

- [ ] **Step 3: Implement** (append)

```python
def build_matrix(strategies: dict, dfs: dict) -> dict:
    """strategies={name: fn}, dfs={ticker: df} → {strategy: {regime: cell}}.

    Collects all trades, computes the global median-date CV boundary once, and
    classifies every observed (strategy, regime) cell."""
    all_trades = []
    for name, fn in strategies.items():
        for ticker, df in dfs.items():
            if len(df) < 300:
                continue
            all_trades.extend(collect_trades_for_strategy(fn, name, ticker, df))

    dates = sorted(t['entry_date'] for t in all_trades)
    boundary = dates[len(dates) // 2] if dates else '2099-01-01'

    matrix = {}
    for name in strategies:
        strat_trades = [t for t in all_trades if t['strategy'] == name]
        by_regime = {}
        for regime in ('BULL', 'SIDEWAYS', 'BEAR'):
            cell = [t for t in strat_trades if t['regime'] == regime]
            if cell:
                by_regime[regime] = classify_cell(cell, boundary)
        matrix[name] = by_regime
    return matrix
```

- [ ] **Step 4: Run to verify pass**

Run: `./venv/bin/python -m pytest tests/test_regime_edge_scan.py -q`
Expected: PASS (all scan tests green)

- [ ] **Step 5: Commit**

```bash
git add scripts/regime_edge_scan.py tests/test_regime_edge_scan.py
git commit -m "feat(scan): build_matrix driver + smoke (Phase 4 regime scan)"
```

---

### Task 4: Corpus runner + results writer

**Files:**
- Modify: `scripts/regime_edge_scan.py`

- [ ] **Step 1: Implement `run()` + `_write_results()` + `__main__`** (append)

```python
def _load_liquid_dfs(conn, as_of):
    tickers = [r[0] for r in conn.execute(
        "SELECT DISTINCT ticker FROM ohlcv WHERE ticker != 'IHSG'")]
    dfs = {}
    for t in tickers:
        adv = get_adv_value_30d(conn, t, as_of)
        if adv is None or adv < VALUE_LIQ_MIN_IDR:
            continue
        df = pd.read_sql("SELECT date, open, high, low, close, volume FROM ohlcv "
                         "WHERE ticker=? ORDER BY date", conn, params=(t,))
        if len(df) >= 300:
            dfs[t] = df
    return dfs


def run():
    conn = db_connect(DB_PATH)
    as_of = conn.execute("SELECT MAX(date) FROM ohlcv").fetchone()[0]
    dfs = _load_liquid_dfs(conn, as_of)
    conn.close()
    matrix = build_matrix(STRATEGY_FUNCS, dfs)
    _write_results(as_of, len(dfs), matrix)
    confirmed = [(s, r) for s, rr in matrix.items() for r, c in rr.items()
                 if c['state'] == 'CONFIRMED']
    promising = [(s, r) for s, rr in matrix.items() for r, c in rr.items()
                 if c['state'] == 'PROMISING']
    print(f"CONFIRMED: {confirmed or 'none'}")
    print(f"PROMISING: {promising or 'none'}")
    return matrix


def _write_results(as_of, n_universe, matrix):
    os.makedirs(os.path.dirname(RESULTS), exist_ok=True)
    L = ["# Regime-Conditional Edge Scan — Results", "",
         f"Run: {datetime.now().isoformat(timespec='seconds')} | corpus as-of {as_of} | "
         f"liquid universe {n_universe} tickers | bar +0.50% net, N>=100 (T3), "
         f"late N>=60 (CV)", "",
         "## Matrix — pooled net expectancy per (strategy, regime)", "",
         "| strategy | BULL | SIDEWAYS | BEAR |", "|---|---|---|---|"]
    for name, rr in matrix.items():
        cells = []
        for regime in ('BULL', 'SIDEWAYS', 'BEAR'):
            c = rr.get(regime)
            if c is None:
                cells.append("—")
            else:
                flag = {'CONFIRMED': '✓✓', 'PROMISING': '✓?', 'REJECTED': ''}[c['state']]
                cells.append(f"{c['exp_pct']:+.2f}% (N{c['n']},{c['win_rate']:.0f}%){flag}")
        L.append(f"| {name} | {cells[0]} | {cells[1]} | {cells[2]} |")
    L += ["", "Legend: ✓✓ CONFIRMED · ✓? PROMISING (thin CV) · blank REJECTED", ""]

    # CV detail for every cell that cleared the regime bar
    L += ["## CV detail (cells clearing the +0.50%/N>=100 regime bar)", ""]
    any_cv = False
    for name, rr in matrix.items():
        for regime, c in rr.items():
            if c['regime_pass']:
                any_cv = True
                L.append(f"- **{name} / {regime}** [{c['state']}]: cell {c['exp_pct']:+.2f}% "
                         f"N{c['n']} | late {c['late_exp']:+.2f}% N{c['late_n']} "
                         f"| early {c['early_exp']:+.2f}% | retention {c['retention']:.2f}")
    if not any_cv:
        L.append("- (no cell cleared the regime bar)")

    confirmed = sorted(((s, r, c) for s, rr in matrix.items() for r, c in rr.items()
                        if c['state'] == 'CONFIRMED'), key=lambda x: -x[2]['exp_pct'])
    promising = sorted(((s, r, c) for s, rr in matrix.items() for r, c in rr.items()
                        if c['state'] == 'PROMISING'), key=lambda x: -x[2]['exp_pct'])
    L += ["", "## CONFIRMED candidates (ranked)"]
    L += ([f"- {s} / {r}: {c['exp_pct']:+.2f}% net (N{c['n']}, win {c['win_rate']:.0f}%)"
           for s, r, c in confirmed] or ["- none"])
    L += ["", "## PROMISING candidates (thin CV — SHADOW to gather data)"]
    L += ([f"- {s} / {r}: {c['exp_pct']:+.2f}% net (N{c['n']}, win {c['win_rate']:.0f}%)"
           for s, r, c in promising] or ["- none"])

    L += ["", "```json", json.dumps(matrix, indent=2, default=float), "```", ""]
    with open(RESULTS, 'w') as f:
        f.write("\n".join(L))


if __name__ == "__main__":
    run()
```

- [ ] **Step 2: Verify the module still imports and tests pass**

Run: `./venv/bin/python -c "import scripts.regime_edge_scan" && ./venv/bin/python -m pytest tests/test_regime_edge_scan.py -q`
Expected: import OK; PASS

- [ ] **Step 3: Commit**

```bash
git add scripts/regime_edge_scan.py
git commit -m "feat(scan): corpus runner + results writer (Phase 4 regime scan)"
```

---

### Task 5: Run the scan for real → results doc + verdict

**Files:**
- Create (generated): `docs/superpowers/results/2026-07-07-regime-edge-scan.md`

- [ ] **Step 1: Run against the prod corpus**

Run: `DB_PATH="/home/tjiesar/10 Projects/idx-walkforward-5001/data/walkforward.db" ./venv/bin/python scripts/regime_edge_scan.py`
Expected: prints `CONFIRMED: …` and `PROMISING: …` lines and writes the results
doc. Runtime ≈ 14 strategies × ~189 liquid tickers × ~16 windows — several
minutes; run with an extended timeout (up to 600000 ms) or in the background.

- [ ] **Step 2: Sanity-check the output**

Run: `sed -n '1,40p' docs/superpowers/results/2026-07-07-regime-edge-scan.md`
Expected: a 14-row matrix with BULL/SIDEWAYS/BEAR columns; NR7's BULL cell should
reproduce ≈ +1.18% (N≈346) — a sanity anchor against the prior study. Confirm the
CONFIRMED/PROMISING lists render.

- [ ] **Step 3: Commit results**

```bash
git add docs/superpowers/results/2026-07-07-regime-edge-scan.md
git commit -m "docs(scan): regime-conditional edge scan results + verdict (Phase 4)"
```

---

### Task 6: Regression + finish

- [ ] **Step 1: Full suite**

Run: `./venv/bin/python -m pytest -q`
Expected: baseline (≈1082 passed) + the new scan tests, 3 skipped, no new failures.

- [ ] **Step 2: Finish the branch**

Use **superpowers:finishing-a-development-branch**: push, PR to `master`, wait CI,
manual merge. **No app restart / prod-branch deploy** — research code only
(scripts/ + tests/ + results doc), no live path touched.

- [ ] **Step 3: Report verdict + recommend next increment**

Summarize the matrix to the user: any CONFIRMED `(strategy, regime)` → next
increment wires it regime-gated to SHADOW; PROMISING → SHADOW to accumulate data;
all REJECTED → the roster has no persistent regime edge, so designing a new
SIDEWAYS strategy is justified.

---

## Self-Review Notes

- **Spec coverage:** generalized collector (Task 1); cell CV + three-state
  classify with `T2_MIN_N=60` (Task 2); `build_matrix` over `STRATEGY_FUNCS` ×
  liquid universe (Tasks 3–4); results doc with matrix + CV detail + ranked
  CONFIRMED/PROMISING + JSON (Task 4); real run + verdict (Task 5). All spec
  deliverables mapped. Pure stats reused from `engine/nr7_study.py`, not
  reimplemented.
- **Multiple-comparisons discipline:** two-hurdle (regime bar in `regime_pass` +
  CV in `persistent`/`late_n`), full 14×3 matrix reported (all cells, not just
  winners), PROMISING kept distinct from CONFIRMED, SHADOW-before-enforce noted.
- **Type consistency:** study-trade dict keys `{strategy, ticker, entry_date,
  raw_entry, raw_exit, regime}` consistent across collector, classify, matrix,
  tests. `classify_cell` returns a dict with `state` used identically by
  `build_matrix`, the runner, and the writer.
- **No production changes:** only `scripts/`, `tests/`, results doc; `engine/
  nr7_study.py` reused unchanged; scan path / regime map untouched (spec "out of
  scope").
- **Placeholder scan:** every step has real code/commands; the one runtime note
  (extend timeout for the real run) is operational, not a deferred implementation.
