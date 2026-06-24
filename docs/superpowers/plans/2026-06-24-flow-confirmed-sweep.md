# Flow-Confirmed Liquidity Sweep Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a long-only liquidity-sweep entry that fires on a structural PDL/PWL stop-hunt and is confirmed by order flow when flow data exists, validated on full OHLCV history (price-only) with flow uplift measured on the recent 30–41-day window.

**Architecture:** A new `engine/smc_flow.py` joins the existing (but unwired) `engine/smc.py` sweep detector to the existing daily/intraday flow data. The strategy takes `ticker=None` so the existing walk-forward runner backtests it price-only on full history, while live/A-B paths pass a ticker to activate the flow gate. Gate is fail-open on missing data, fail-closed on negative flow.

**Tech Stack:** Python 3, pandas, numpy, sqlite3, pytest. Interpreter: `./venv/bin/python` (system `pytest` uses the wrong interpreter and produces false collection errors).

---

## ⚠️ Interpreter Rule (read first)

ALWAYS run tests with `./venv/bin/python -m pytest`. NEVER `source venv/bin/activate` (the space in `10 Projects` breaks `activate`). NEVER bare `pytest` (resolves to `~/.local/bin/pytest`, a different env missing `feedparser` → 10 false collection errors).

All commands assume CWD is the repo root: `/home/tjiesar/10 Projects/idx-walkforward-5001`.

## File Structure

| File | Responsibility |
|---|---|
| `engine/smc_flow.py` (new) | `confirm_sweep_flow(ticker, date)` — the flow-confirmation gate. Daily tier (`stockbit_flow.composite_score`), intraday tier (`delta_flow.session_delta_stats`), passthrough on missing data. |
| `engine/strategies.py` (modify) | `strategy_liquidity_sweep_flow(df, ticker=None, ...)` backtest + `check_sweep_flow_signal(df, ticker)` live check + dispatcher route. |
| `engine/walkforward_multi.py` (modify) | Register `'Liquidity Sweep'` in `STRATEGY_FUNCS`. |
| `engine/smc.py` (modify) | One-line deprecation note on `calc_fvg_signal` (direction-agnostic; not used). |
| `scheduler/scanner.py` (modify) | Surface the sweep+flow candidate in the multi-strategy scan. |
| `tests/engine/test_smc_flow.py` (new) | Unit tests for the gate + golden test for `detect_liquidity_sweep`. |
| `tests/engine/test_strategy_sweep_flow.py` (new) | Strategy + live-check integration tests. |
| `scratchpad/sweep_validation.py` (new, not committed) | Structural backtest + flow A/B harness → markdown report. |

## Reference: existing signatures (do not change)

- `engine/strategies.py:144` — `run_strategy(df, signals, ..., atr_sl_mult, atr_tp_mult, min_rr=2.0)`. Enters next bar open after `signals.iloc[i-1]` (no look-ahead). Long-only.
- `engine/smc.py:438` — `calc_sweep_signal(df) -> pd.Series` (True on bullish PDL/PWL sweep bars).
- `engine/smc.py:324` — `detect_liquidity_sweep(df, use_weekly=True, wick_pct_threshold=0.3) -> DataFrame[date, sweep_type, level, level_price, wick_pct, direction, signal]`.
- `engine/delta_flow.py:77` — `session_delta_stats(ticker, date, db_path=DB_PATH) -> {total_delta, buy_lot, sell_lot, net_value}` or `{..., 'note': str}` when no rows.
- `stockbit_flow` columns: `ticker, trade_date, ..., composite_score (int [-8,+8]), verdict, smart_money, foreign_score`. Coverage 2026-04-10 → present.
- `config.DB_PATH` — path to `data/walkforward.db`.
- `engine/strategies.py:1180` — `check_current_entry_signal(ticker, strategy, df)` routes by name, applies a weekly-trend gate after; counter-trend strategies `return` early to bypass it.
- `engine/walkforward_multi.py:171` — `STRATEGY_FUNCS` dict; each called as `func(df, capital=, filters=)`.

---

### Task 1: Golden-freeze test for `detect_liquidity_sweep`

Lock the foundation before building on it.

**Files:**
- Test: `tests/engine/test_smc_flow.py`

- [ ] **Step 1: Write the golden test**

```python
import pandas as pd
import numpy as np
from engine.smc import detect_liquidity_sweep, calc_sweep_signal


def _df(rows):
    """rows: list of (date, open, high, low, close, volume)."""
    return pd.DataFrame(rows, columns=['date', 'open', 'high', 'low', 'close', 'volume'])


def test_detect_bullish_pdl_sweep():
    # Bar 1 sets PDL low=100. Bar 2 wicks below 100 then closes back above → bullish sweep.
    df = _df([
        ('2026-05-01', 105, 110, 100, 108, 1_000_000),  # PDL = 100
        ('2026-05-02', 106, 109, 105, 107, 1_000_000),  # inside, no sweep
        ('2026-05-03', 106, 108,  95, 106, 1_500_000),  # low 95 < PDL(=109's prev low 105)...
    ])
    sweeps = detect_liquidity_sweep(df, use_weekly=False)
    # Bar 3 PDL is bar 2's low (105). Low 95 < 105, wick = (105-95)/(108-95)=0.77 >= 0.3,
    # close 106 > 105 → bullish sweep signal=1.
    assert not sweeps.empty
    bull = sweeps[sweeps['signal'] == 1]
    assert len(bull) == 1
    assert bull.iloc[0]['sweep_type'] == 'pdl'
    assert bull.iloc[0]['direction'] == 'bullish'
    assert bull.iloc[0]['wick_pct'] >= 0.3


def test_no_sweep_when_wick_too_small():
    # Low barely breaks PDL but wick < 30% of range → no sweep.
    df = _df([
        ('2026-05-01', 105, 110, 100, 108, 1_000_000),
        ('2026-05-02', 106, 109, 104, 107, 1_000_000),  # PDL for bar3 = 104
        ('2026-05-03', 106, 120, 103, 119, 1_500_000),  # low 103 < 104 but wick=(104-103)/(120-103)=0.06
    ])
    sweeps = detect_liquidity_sweep(df, use_weekly=False)
    assert sweeps[sweeps['signal'] == 1].empty


def test_calc_sweep_signal_marks_bullish_bar():
    df = _df([
        ('2026-05-01', 105, 110, 100, 108, 1_000_000),
        ('2026-05-02', 106, 109, 105, 107, 1_000_000),
        ('2026-05-03', 106, 108,  95, 106, 1_500_000),
    ])
    sig = calc_sweep_signal(df)
    assert sig.iloc[2] == True
    assert sig.iloc[0] == False
```

- [ ] **Step 2: Run to verify it passes against existing code**

Run: `./venv/bin/python -m pytest tests/engine/test_smc_flow.py -v`
Expected: 3 passed. (If a row's arithmetic is off, adjust the synthetic OHLC numbers until the asserted sweep is produced — do NOT change `smc.py`.)

- [ ] **Step 3: Commit**

```bash
git add tests/engine/test_smc_flow.py
git commit -m "test(smc): golden-freeze detect_liquidity_sweep bullish PDL"
```

---

### Task 2: Flow gate — daily tier

**Files:**
- Create: `engine/smc_flow.py`
- Test: `tests/engine/test_smc_flow.py`

- [ ] **Step 1: Write the failing test (append to test file)**

```python
import sqlite3
from engine.smc_flow import confirm_sweep_flow


def _flow_db(tmp_path, rows):
    """rows: list of (ticker, trade_date, composite_score). Returns db path str."""
    db = str(tmp_path / 'flow.db')
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE stockbit_flow (ticker TEXT, trade_date TEXT, composite_score INTEGER)")
    conn.execute("CREATE TABLE stockbit_flow_bars (ticker TEXT, trade_date TEXT, bar_time TEXT, "
                 "buy_lot INT, sell_lot INT, buy_freq INT, sell_freq INT, net_value INT, "
                 "price REAL, delta INT)")
    conn.executemany("INSERT INTO stockbit_flow VALUES (?,?,?)", rows)
    conn.commit(); conn.close()
    return db


def test_daily_positive_flow_confirms(tmp_path):
    db = _flow_db(tmp_path, [('BBCA', '2026-05-03', 5)])
    r = confirm_sweep_flow('BBCA', '2026-05-03', db_path=db)
    assert r['confirmed'] is True
    assert r['source'] == 'daily'
    assert r['score'] == 5.0


def test_daily_negative_flow_rejects(tmp_path):
    db = _flow_db(tmp_path, [('BBCA', '2026-05-03', -3)])
    r = confirm_sweep_flow('BBCA', '2026-05-03', db_path=db)
    assert r['confirmed'] is False
    assert r['source'] == 'daily'


def test_daily_zero_flow_rejects(tmp_path):
    db = _flow_db(tmp_path, [('BBCA', '2026-05-03', 0)])
    r = confirm_sweep_flow('BBCA', '2026-05-03', db_path=db)
    assert r['confirmed'] is False
```

- [ ] **Step 2: Run to verify it fails**

Run: `./venv/bin/python -m pytest tests/engine/test_smc_flow.py::test_daily_positive_flow_confirms -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'engine.smc_flow'`

- [ ] **Step 3: Implement the daily tier**

```python
"""Flow-confirmation gate for SMC liquidity-sweep entries.

Joins engine/smc.py sweep detection to the existing flow data:
  - daily tier:    stockbit_flow.composite_score (int [-8,+8])
  - intraday tier: stockbit_flow_bars via delta_flow.session_delta_stats
Gate is fail-open on missing data (so full-history backtests run price-only)
and fail-closed on negative flow (so live trades require real flow).
"""
import sqlite3
from config import DB_PATH
from engine.delta_flow import session_delta_stats


def _daily_flow_score(ticker: str, date: str, db_path: str):
    """composite_score for ticker/date as float, or None if absent/unparseable."""
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "SELECT composite_score FROM stockbit_flow WHERE ticker=? AND trade_date=?",
            (ticker.upper(), date)).fetchone()
    except sqlite3.Error:
        return None
    finally:
        conn.close()
    if row is None or row[0] is None:
        return None
    try:
        return float(row[0])
    except (TypeError, ValueError):
        return None


def confirm_sweep_flow(ticker: str, date: str, db_path: str = DB_PATH) -> dict:
    """Return {confirmed: bool, source: 'daily'|'intraday'|'none', reason, score}."""
    cs = _daily_flow_score(ticker, date, db_path)
    if cs is not None:
        if cs > 0:
            return {'confirmed': True, 'source': 'daily',
                    'reason': f'composite_score {cs:+.0f} > 0', 'score': cs}
        return {'confirmed': False, 'source': 'daily',
                'reason': f'composite_score {cs:+.0f} <= 0', 'score': cs}
    # intraday + passthrough handled in Task 3
    return {'confirmed': True, 'source': 'none',
            'reason': 'no flow data (passthrough)', 'score': None}
```

- [ ] **Step 4: Run to verify it passes**

Run: `./venv/bin/python -m pytest tests/engine/test_smc_flow.py -v`
Expected: all daily-tier tests pass.

- [ ] **Step 5: Commit**

```bash
git add engine/smc_flow.py tests/engine/test_smc_flow.py
git commit -m "feat(smc-flow): daily-tier flow confirmation gate"
```

---

### Task 3: Flow gate — intraday tier + passthrough

**Files:**
- Modify: `engine/smc_flow.py`
- Test: `tests/engine/test_smc_flow.py`

- [ ] **Step 1: Write the failing tests (append)**

```python
def test_intraday_positive_delta_confirms(tmp_path):
    # No daily row → falls through to intraday bars.
    db = _flow_db(tmp_path, [])  # empty stockbit_flow
    conn = sqlite3.connect(db)
    conn.executemany(
        "INSERT INTO stockbit_flow_bars VALUES (?,?,?,?,?,?,?,?,?,?)",
        [('BBCA', '2026-05-03', '09:00', 500, 200, 5, 2, 100, 4000.0, 300),
         ('BBCA', '2026-05-03', '09:01', 400, 300, 4, 3, 90, 4010.0, 100)])
    conn.commit(); conn.close()
    r = confirm_sweep_flow('BBCA', '2026-05-03', db_path=db)
    assert r['confirmed'] is True
    assert r['source'] == 'intraday'
    assert r['score'] == 400.0  # 300 + 100


def test_intraday_negative_delta_rejects(tmp_path):
    db = _flow_db(tmp_path, [])
    conn = sqlite3.connect(db)
    conn.execute("INSERT INTO stockbit_flow_bars VALUES (?,?,?,?,?,?,?,?,?,?)",
                 ('BBCA', '2026-05-03', '09:00', 100, 600, 1, 6, -50, 4000.0, -500))
    conn.commit(); conn.close()
    r = confirm_sweep_flow('BBCA', '2026-05-03', db_path=db)
    assert r['confirmed'] is False
    assert r['source'] == 'intraday'


def test_no_flow_data_passthrough(tmp_path):
    db = _flow_db(tmp_path, [])  # both tables empty
    r = confirm_sweep_flow('BBCA', '2026-01-01', db_path=db)
    assert r['confirmed'] is True
    assert r['source'] == 'none'
```

- [ ] **Step 2: Run to verify they fail**

Run: `./venv/bin/python -m pytest tests/engine/test_smc_flow.py::test_intraday_positive_delta_confirms -v`
Expected: FAIL — returns `source='none'` instead of `'intraday'`.

- [ ] **Step 3: Add the intraday tier**

Replace the trailing passthrough in `confirm_sweep_flow` (the `# intraday + passthrough handled in Task 3` block) with:

```python
    stats = session_delta_stats(ticker, date, db_path)
    if not stats.get('note'):  # rows present for this ticker/date
        total = stats['total_delta']
        if total >= 0:
            return {'confirmed': True, 'source': 'intraday',
                    'reason': f'session delta {total:+d} >= 0', 'score': float(total)}
        return {'confirmed': False, 'source': 'intraday',
                'reason': f'session delta {total:+d} < 0', 'score': float(total)}

    return {'confirmed': True, 'source': 'none',
            'reason': 'no flow data (passthrough)', 'score': None}
```

Note: `session_delta_stats` returns a `note` key only when no rows exist; otherwise it returns `total_delta`. The `db_path` is threaded through so the test fixture DB is used.

- [ ] **Step 4: Run to verify all pass**

Run: `./venv/bin/python -m pytest tests/engine/test_smc_flow.py -v`
Expected: all tests pass (golden + daily + intraday + passthrough).

- [ ] **Step 5: Commit**

```bash
git add engine/smc_flow.py tests/engine/test_smc_flow.py
git commit -m "feat(smc-flow): intraday-delta tier + missing-data passthrough"
```

---

### Task 4: Strategy `strategy_liquidity_sweep_flow`

`ticker=None` → flow passthrough (price-only), so the existing WF runner backtests it on full history automatically.

**Files:**
- Modify: `engine/strategies.py` (append at end of file)
- Test: `tests/engine/test_strategy_sweep_flow.py`

- [ ] **Step 1: Write the failing test**

```python
import sqlite3
import pandas as pd
import numpy as np
from engine.strategies import strategy_liquidity_sweep_flow


def _trending_df_with_sweep(n=80):
    """Build a long uptrending series with a clean bullish PDL sweep near the end."""
    dates = pd.date_range('2026-02-01', periods=n, freq='B').strftime('%Y-%m-%d')
    base = np.linspace(1000, 1400, n)
    o = base.copy(); h = base + 15; l = base - 15; c = base + 5
    vol = np.full(n, 1_000_000)
    # Inject a sweep at bar n-2: deep wick below previous low, close back up.
    l[n - 2] = base[n - 3] - 40
    h[n - 2] = base[n - 2] + 10
    c[n - 2] = base[n - 2] + 8
    vol[n - 2] = 2_000_000
    return pd.DataFrame({'date': dates, 'open': o, 'high': h, 'low': l,
                         'close': c, 'volume': vol})


def test_price_only_backtest_runs_when_ticker_none():
    df = _trending_df_with_sweep()
    result = strategy_liquidity_sweep_flow(df, ticker=None)
    assert result['strategy'] == 'Liquidity Sweep'
    assert 'trades' in result
    assert isinstance(result['final_capital'], (int, float))


def test_negative_flow_blocks_the_entry(tmp_path, monkeypatch):
    df = _trending_df_with_sweep()
    # Price-only produces at least one signal day; with negative flow it must produce fewer/zero trades.
    base_trades = len(strategy_liquidity_sweep_flow(df, ticker=None)['trades'])

    import engine.smc_flow as smc_flow
    monkeypatch.setattr(smc_flow, 'confirm_sweep_flow',
                        lambda t, d, db_path=None: {'confirmed': False, 'source': 'daily',
                                                    'reason': 'forced', 'score': -9})
    gated_trades = len(strategy_liquidity_sweep_flow(df, ticker='BBCA')['trades'])
    assert gated_trades <= base_trades
    assert gated_trades == 0
```

- [ ] **Step 2: Run to verify it fails**

Run: `./venv/bin/python -m pytest tests/engine/test_strategy_sweep_flow.py -v`
Expected: FAIL — `ImportError: cannot import name 'strategy_liquidity_sweep_flow'`

- [ ] **Step 3: Implement the strategy (append to `engine/strategies.py`)**

```python
def strategy_liquidity_sweep_flow(df: pd.DataFrame, ticker: str = None,
                                  capital: float = 50_000_000,
                                  filters: list = None) -> dict:
    """SMC liquidity-sweep entry (bullish PDL/PWL trap) confirmed by order flow.

    Long-only. ATR SL×1.0 / TP×2.5 (RR 2.5). When ticker is None the flow gate
    is skipped (price-only) so this can be walk-forward backtested on full OHLCV
    history. When a ticker is given, each candidate sweep day must pass
    confirm_sweep_flow (fail-open on missing data, fail-closed on negative flow).
    """
    from engine.smc import calc_sweep_signal
    sig = calc_sweep_signal(df)

    if ticker is not None and sig.any():
        from engine.smc_flow import confirm_sweep_flow
        dates = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d').values
        vals = sig.values.copy()
        for pos in range(len(vals)):
            if vals[pos] and not confirm_sweep_flow(ticker, dates[pos])['confirmed']:
                vals[pos] = False
        sig = pd.Series(vals, index=df.index)

    return run_strategy(df, sig, atr_sl_mult=1.0, atr_tp_mult=2.5, min_rr=2.5,
                        strategy_name='Liquidity Sweep', initial_capital=capital,
                        filters=filters)
```

- [ ] **Step 4: Run to verify it passes**

Run: `./venv/bin/python -m pytest tests/engine/test_strategy_sweep_flow.py -v`
Expected: 2 passed. (If `test_price_only_backtest_runs_when_ticker_none` produces zero signals, increase the wick depth on `l[n-2]` until `calc_sweep_signal` fires.)

- [ ] **Step 5: Commit**

```bash
git add engine/strategies.py tests/engine/test_strategy_sweep_flow.py
git commit -m "feat(strategy): flow-confirmed liquidity sweep (price-only when ticker=None)"
```

---

### Task 5: Live check `check_sweep_flow_signal`

**Files:**
- Modify: `engine/strategies.py` (append after `strategy_liquidity_sweep_flow`)
- Test: `tests/engine/test_strategy_sweep_flow.py`

- [ ] **Step 1: Write the failing test (append)**

```python
from engine.strategies import check_sweep_flow_signal


def test_live_check_fires_on_current_bar_sweep(monkeypatch):
    df = _trending_df_with_sweep()
    # Move the sweep to the LAST bar so the live check considers it current.
    n = len(df)
    df.loc[n - 1, 'low'] = df.loc[n - 2, 'low'] - 40
    df.loc[n - 1, 'close'] = df.loc[n - 2, 'low'] + 8
    df.loc[n - 1, 'high'] = df.loc[n - 1, 'close'] + 5

    import engine.smc_flow as smc_flow
    monkeypatch.setattr(smc_flow, 'confirm_sweep_flow',
                        lambda t, d, db_path=None: {'confirmed': True, 'source': 'daily',
                                                    'reason': 'cs +5', 'score': 5})
    r = check_sweep_flow_signal(df, 'BBCA')
    assert r['has_signal'] is True
    assert 'sweep' in r['reason'].lower()


def test_live_check_blocked_by_negative_flow(monkeypatch):
    df = _trending_df_with_sweep()
    n = len(df)
    df.loc[n - 1, 'low'] = df.loc[n - 2, 'low'] - 40
    df.loc[n - 1, 'close'] = df.loc[n - 2, 'low'] + 8
    df.loc[n - 1, 'high'] = df.loc[n - 1, 'close'] + 5

    import engine.smc_flow as smc_flow
    monkeypatch.setattr(smc_flow, 'confirm_sweep_flow',
                        lambda t, d, db_path=None: {'confirmed': False, 'source': 'daily',
                                                    'reason': 'cs -3', 'score': -3})
    r = check_sweep_flow_signal(df, 'BBCA')
    assert r['has_signal'] is False
    assert 'flow' in r['reason'].lower()
```

- [ ] **Step 2: Run to verify it fails**

Run: `./venv/bin/python -m pytest tests/engine/test_strategy_sweep_flow.py::test_live_check_fires_on_current_bar_sweep -v`
Expected: FAIL — `ImportError: cannot import name 'check_sweep_flow_signal'`

- [ ] **Step 3: Implement (append to `engine/strategies.py`)**

```python
def check_sweep_flow_signal(df: pd.DataFrame, ticker: str) -> dict:
    """Live last-bar check: bullish sweep on the current bar, confirmed by flow.

    Returns {'has_signal': bool, 'reason': str, 'details': dict}.
    """
    from engine.smc import detect_liquidity_sweep
    from engine.smc_flow import confirm_sweep_flow

    sweeps = detect_liquidity_sweep(df)
    if sweeps.empty:
        return {'has_signal': False, 'reason': 'No sweeps detected', 'details': {}}

    bullish = sweeps[sweeps['signal'] == 1]
    if bullish.empty:
        return {'has_signal': False, 'reason': 'No bullish sweep', 'details': {}}

    last = bullish.iloc[-1]
    last_bar_date = str(df.iloc[-1]['date'])[:10]
    if str(last['date'])[:10] != last_bar_date:
        return {'has_signal': False,
                'reason': f"Last bullish sweep {last['date']} not on current bar",
                'details': {}}

    flow = confirm_sweep_flow(ticker, last_bar_date)
    if not flow['confirmed']:
        return {'has_signal': False,
                'reason': f"{last['sweep_type'].upper()} sweep but flow rejected: {flow['reason']}",
                'details': {'flow': flow}}

    return {'has_signal': True,
            'reason': (f"{last['sweep_type'].upper()} sweep @ {last['level_price']} "
                       f"(wick {last['wick_pct']:.0%}), flow {flow['source']}: {flow['reason']}"),
            'details': {'sweep_type': last['sweep_type'],
                        'level_price': float(last['level_price']),
                        'wick_pct': float(last['wick_pct']),
                        'flow': flow}}
```

- [ ] **Step 4: Run to verify it passes**

Run: `./venv/bin/python -m pytest tests/engine/test_strategy_sweep_flow.py -v`
Expected: all 4 tests pass.

- [ ] **Step 5: Commit**

```bash
git add engine/strategies.py tests/engine/test_strategy_sweep_flow.py
git commit -m "feat(strategy): check_sweep_flow_signal live last-bar check"
```

---

### Task 6: Register in WF runner + dispatcher

**Files:**
- Modify: `engine/walkforward_multi.py:10-20` (imports) and `:171-184` (`STRATEGY_FUNCS`)
- Modify: `engine/strategies.py:1216-1218` (dispatcher route)
- Test: `tests/engine/test_strategy_sweep_flow.py`

- [ ] **Step 1: Write the failing test (append)**

```python
def test_registered_in_strategy_funcs():
    from engine.walkforward_multi import STRATEGY_FUNCS
    assert 'Liquidity Sweep' in STRATEGY_FUNCS


def test_dispatcher_routes_liquidity_sweep(monkeypatch):
    import engine.strategies as strat
    captured = {}

    def fake_check(df, ticker):
        captured['called'] = True
        return {'has_signal': False, 'reason': 'stub', 'details': {}}

    monkeypatch.setattr(strat, 'check_sweep_flow_signal', fake_check)
    df = _trending_df_with_sweep()
    strat.check_current_entry_signal('BBCA', 'Liquidity Sweep', df)
    assert captured.get('called') is True
```

- [ ] **Step 2: Run to verify it fails**

Run: `./venv/bin/python -m pytest tests/engine/test_strategy_sweep_flow.py::test_registered_in_strategy_funcs -v`
Expected: FAIL — `'Liquidity Sweep' not in STRATEGY_FUNCS`

- [ ] **Step 3a: Add import in `engine/walkforward_multi.py`**

In the `from engine.strategies import (...)` block (lines ~10-20), add:

```python
    strategy_liquidity_sweep_flow,
```

- [ ] **Step 3b: Register in `STRATEGY_FUNCS` (after the `'Panic Rebound'` line at :183)**

```python
    'Liquidity Sweep':           strategy_liquidity_sweep_flow,
```

(Called as `func(df, capital=, filters=)` → `ticker` defaults to `None` → price-only WF backtest on full history. This is the structural-edge validation path.)

- [ ] **Step 3c: Add dispatcher route in `engine/strategies.py`**

After the `Panic Rebound` branch (`:1216-1218`), before the `else:`:

```python
    elif strategy == 'Liquidity Sweep':
        # Reversal/bottom-fishing — bypass the weekly-trend gate (the setup IS a dip)
        return check_sweep_flow_signal(df, ticker)
```

- [ ] **Step 4: Run to verify it passes**

Run: `./venv/bin/python -m pytest tests/engine/test_strategy_sweep_flow.py -v`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add engine/walkforward_multi.py engine/strategies.py tests/engine/test_strategy_sweep_flow.py
git commit -m "feat(strategy): register Liquidity Sweep in WF runner + dispatcher (weekly-gate bypass)"
```

---

### Task 7: Scanner surfacing of the sweep+flow candidate

**Files:**
- Modify: `scheduler/scanner.py` (the multi-strategy scan path that calls `check_current_entry_signal`)

- [ ] **Step 1: Locate the call site**

Run: `grep -n "check_current_entry_signal\|STRATEGY_FUNCS\|disabled_strategies" scheduler/scanner.py`
Expected: at least one call to `check_current_entry_signal(ticker, strategy, df)` inside the multi-strategy scan, and a `disabled_strategies` config read.

- [ ] **Step 2: Verify `'Liquidity Sweep'` is not disabled by default**

`disabled_strategies` is currently `"Swing Trend"` only (per `docs/update.md`). No change needed — `'Liquidity Sweep'` will be picked up by the adaptive selector once it has a `wf_scores` row (populated in Task 9). No code change required if the scanner iterates `STRATEGY_FUNCS` keys or WF-scored strategies; confirm by reading the loop.

- [ ] **Step 3: If the scanner uses a hardcoded strategy list (not `STRATEGY_FUNCS`), add `'Liquidity Sweep'` to it**

Read the loop found in Step 1. If strategies are iterated from a literal list rather than `STRATEGY_FUNCS` or the `wf_scores` table, append `'Liquidity Sweep'` to that list. If it iterates `STRATEGY_FUNCS` or WF-scored tickers, no edit is needed.

- [ ] **Step 4: Smoke-test the scanner import**

Run: `./venv/bin/python -c "from scheduler import scanner; print('scanner imports OK')"`
Expected: `scanner imports OK`

- [ ] **Step 5: Commit (only if a code edit was made)**

```bash
git add scheduler/scanner.py
git commit -m "feat(scanner): surface Liquidity Sweep candidate in multi-strategy scan"
```

---

### Task 8: Deprecation note on `calc_fvg_signal`

The FVG signal is direction-agnostic (fires on bullish AND bearish unfilled FVGs) but the staged `strategy_fvg_fill` is long-only — buying a bearish-FVG fill is overhead supply. We are NOT building the FVG strategy; mark the hazard.

**Files:**
- Modify: `engine/smc.py:209` (`calc_fvg_signal` docstring)

- [ ] **Step 1: Add the note**

Edit the `calc_fvg_signal` docstring to begin with:

```python
    """
    DEPRECATED / DO NOT USE FOR LONG-ONLY ENTRIES: this returns True when price
    is inside ANY unfilled FVG (bullish OR bearish) with no direction filter. A
    long-only strategy would buy bearish-FVG fills (overhead supply). Use
    calc_sweep_signal + confirm_sweep_flow instead. Kept for analysis only.

    Generate a daily signal: True when price is INSIDE an unfilled FVG zone.
    ...
```

(Keep the rest of the existing docstring.)

- [ ] **Step 2: Verify import still works**

Run: `./venv/bin/python -c "from engine.smc import calc_fvg_signal; print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add engine/smc.py
git commit -m "docs(smc): flag calc_fvg_signal as direction-agnostic / not for long-only"
```

---

### Task 9: Validation harness — structural backtest + flow A/B

Produces the evidence: structural edge on full history, flow uplift on the recent window. Output is a report, not committed runtime code.

**Files:**
- Create: `scratchpad/sweep_validation.py` (do NOT commit — scratchpad only)
- Output: `data/reports/sweep_validation_2026-06-24.md`

- [ ] **Step 1: Write the harness**

```python
"""Validation for the flow-confirmed liquidity sweep.
(a) Structural: price-only sweep across LQ45 full history (WF metrics).
(b) Flow A/B: same signals over the flow window (2026-04-10+), with vs without flow.
Run: ./venv/bin/python scratchpad/sweep_validation.py
"""
import pandas as pd
from engine.strategies import strategy_liquidity_sweep_flow
from engine.walkforward_multi import compute_metrics
from scheduler.utils import _load_ohlcv_bulk

LQ45 = ['BBCA', 'BBRI', 'BMRI', 'TLKM', 'ASII', 'BBNI', 'UNVR', 'ICBP',
        'ADRO', 'ANTM', 'GOTO', 'MDKA', 'AMRT', 'KLBF', 'INDF']  # representative subset

def structural():
    rows = []
    for t in LQ45:
        df = _load_ohlcv_bulk(t)
        if df is None or len(df) < 120:
            continue
        res = strategy_liquidity_sweep_flow(df, ticker=None)  # price-only
        m = compute_metrics(res)
        m['ticker'] = t
        rows.append(m)
    return pd.DataFrame(rows)

def flow_ab():
    rows = []
    for t in LQ45:
        df = _load_ohlcv_bulk(t)
        if df is None or len(df) < 120:
            continue
        recent = df[pd.to_datetime(df['date']) >= '2026-04-10'].reset_index(drop=True)
        if len(recent) < 20:
            continue
        no_flow = compute_metrics(strategy_liquidity_sweep_flow(recent, ticker=None))
        with_flow = compute_metrics(strategy_liquidity_sweep_flow(recent, ticker=t))
        rows.append({'ticker': t,
                     'trades_no_flow': no_flow.get('total_trades', 0),
                     'wr_no_flow': no_flow.get('win_rate', 0),
                     'trades_flow': with_flow.get('total_trades', 0),
                     'wr_flow': with_flow.get('win_rate', 0)})
    return pd.DataFrame(rows)

if __name__ == '__main__':
    s = structural()
    ab = flow_ab()
    out = ['# Liquidity Sweep Validation — 2026-06-24', '',
           '## (a) Structural (price-only, full history)', '',
           s.to_markdown(index=False) if not s.empty else '_no data_', '',
           '## (b) Flow A/B (window from 2026-04-10, SMALL SAMPLE)', '',
           ab.to_markdown(index=False) if not ab.empty else '_no data_', '',
           '> Flow window is ~30-41 trading days. (b) is a shadow/forward indication, NOT a walk-forward claim.']
    import os
    os.makedirs('data/reports', exist_ok=True)
    with open('data/reports/sweep_validation_2026-06-24.md', 'w') as f:
        f.write('\n'.join(out))
    print('wrote data/reports/sweep_validation_2026-06-24.md')
    print(s.to_string(index=False) if not s.empty else 'structural: no data')
```

- [ ] **Step 2: Confirm `compute_metrics` and `_load_ohlcv_bulk` signatures**

Run: `grep -n "def compute_metrics" engine/walkforward_multi.py; grep -n "def _load_ohlcv_bulk" scheduler/utils.py`
Expected: both found. If `compute_metrics` returns different key names than `total_trades`/`win_rate`, adjust the report dict keys to match the actual keys (print one `compute_metrics(...)` dict to inspect).

- [ ] **Step 3: Run the harness**

Run: `./venv/bin/python scratchpad/sweep_validation.py`
Expected: prints `wrote data/reports/...` and a structural metrics table. If a metric key errors, fix per Step 2.

- [ ] **Step 4: Read the report and assess**

Read `data/reports/sweep_validation_2026-06-24.md`. The structural table establishes whether the price-only sweep has a positive expectancy/Sharpe across LQ45. The A/B table indicates whether the flow gate improved win-rate on the recent window. Summarize findings for the user — do NOT commit the scratchpad script or auto-promote the strategy.

---

### Task 10: Full suite green + golden freeze

**Files:** none (verification)

- [ ] **Step 1: Run the two new test files**

Run: `./venv/bin/python -m pytest tests/engine/test_smc_flow.py tests/engine/test_strategy_sweep_flow.py -v`
Expected: all pass.

- [ ] **Step 2: Run the full suite to check for regressions**

Run: `./venv/bin/python -m pytest -q`
Expected: same pass/fail baseline as before this work (760 collected, 0 collection errors). No NEW failures introduced by these changes. Known pre-existing failures (if any) are unchanged.

- [ ] **Step 3: Final commit**

```bash
git add -A
git commit -m "test(smc-flow): full suite green for flow-confirmed liquidity sweep"
```

---

## Self-Review

**Spec coverage:**
- `confirm_sweep_flow` daily + intraday + passthrough → Tasks 2, 3. ✅
- Fail-open / fail-closed semantics → Tasks 2 (negative rejects), 3 (passthrough), 4 (gate applied). ✅
- `strategy_liquidity_sweep_flow` + `check_sweep_flow_signal` → Tasks 4, 5. ✅
- WF runner registration (structural backtest path) + dispatcher (weekly-gate bypass) → Task 6. ✅
- Scanner surfacing → Task 7. ✅
- FVG deprecation note → Task 8. ✅
- Validation: structural (full history) + flow A/B (recent window, small-sample caveat) → Task 9. ✅
- Golden freeze on `detect_liquidity_sweep` → Task 1. ✅
- Interpreter rule → top of plan + every test command. ✅
- Out of scope (FVG strategy, discount, op fixes) → respected. ✅

**Placeholder scan:** No TBD/TODO. Tasks 7 and 9 contain conditional verification steps (locate call site / confirm metric keys) because those depend on code not fully read at plan-time; each gives an exact grep command and the concrete edit to make based on the result — not a vague instruction.

**Type consistency:** `confirm_sweep_flow` returns `{confirmed, source, reason, score}` consistently across Tasks 2–5. `strategy_liquidity_sweep_flow(df, ticker=None, capital, filters)` signature matches the WF runner call convention in Task 6. `check_sweep_flow_signal(df, ticker)` matches the dispatcher call in Task 6. `run_strategy` params (`atr_sl_mult`, `atr_tp_mult`, `min_rr`) match the existing signature.
