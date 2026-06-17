# Multi-Pane Chart Viewer with Order-Flow Delta — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Workspace-embedded multi-pane `lightweight-charts` viewer with custom indicators (Volume Profile, FVG, S&R, patterns; VWAP/VWMA reused from `engine/indicators.py`), an ATAS-style CVD / delta-by-price module from Stockbit 1-min flow, and one-click TradingView Desktop symbol sync via CDP.

**Architecture:** Three new pure-Python compute modules (`chart_indicators`, `delta_flow`, `tv_bridge`), one new Flask blueprint (`routes/chart.py`) that bundles their output as JSON, and a frontend panel (`static/charts.js` + `charts.css`) wired into the existing `workspace.html`. Candle OHLCV reuses existing `/api/ticker/...` routes. VWAP/VWMA reuse existing `engine/indicators.py`.

**Tech Stack:** Python 3 / Flask / pandas / sqlite3 / pytest; `lightweight-charts@4.2.0` (already loaded); Chrome DevTools Protocol over websocket (`websocket-client` or stdlib).

**Branch:** `feat/multi-pane-chart-viewer` (already created; spec committed).

---

## Conventions (read once)

- OHLCV DataFrames use **lowercase** columns: `open, high, low, close, volume`, DatetimeIndex or `date` column.
- DB path: `from config import DB_PATH`.
- Flow bars table `stockbit_flow_bars`: columns `ticker, trade_date, bar_time, buy_lot, sell_lot, buy_freq, sell_freq, net_value, price, delta`. `delta = buy_lot - sell_lot`. `trade_date` = `YYYY-MM-DD`, `bar_time` = `HH:MM`.
- Delta history window: rolling, earliest `2026-04-20`. Out-of-window dates return empty + a `note`.
- Run tests with: `cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && python3 -m pytest <path> -v`.
- Commit after each task. Use `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.

---

## Phase 1 — Indicator Engine (`engine/chart_indicators.py`)

### Task 1: Volume Profile

**Files:**
- Create: `engine/chart_indicators.py`
- Test: `tests/test_chart_indicators.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_chart_indicators.py
import pandas as pd
import numpy as np
from engine.chart_indicators import volume_profile


def _df(rows):
    """rows: list of (date, o, h, l, c, v)"""
    idx = pd.to_datetime([r[0] for r in rows])
    return pd.DataFrame(
        {'open':[r[1] for r in rows], 'high':[r[2] for r in rows],
         'low':[r[3] for r in rows], 'close':[r[4] for r in rows],
         'volume':[r[5] for r in rows]}, index=idx)


def test_volume_profile_poc_at_highest_volume_band():
    # Two bars hug price 100 with big volume, one bar at 110 with tiny volume.
    df = _df([
        ('2026-01-01', 99, 101, 99, 100, 1000),
        ('2026-01-02', 99, 101, 99, 100, 1000),
        ('2026-01-03', 109, 111, 109, 110, 10),
    ])
    vp = volume_profile(df, bins=12)
    assert set(vp.keys()) == {'poc', 'vah', 'val', 'rows'}
    assert abs(vp['poc'] - 100) < 2          # POC near 100
    assert vp['val'] <= vp['poc'] <= vp['vah']
    assert len(vp['rows']) == 12
    assert all('price' in r and 'volume' in r for r in vp['rows'])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_chart_indicators.py::test_volume_profile_poc_at_highest_volume_band -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'engine.chart_indicators'`

- [ ] **Step 3: Write minimal implementation**

```python
# engine/chart_indicators.py
"""Custom chart overlays computed from an OHLCV DataFrame.

Pure functions, no I/O. Columns expected (lowercase): open, high, low,
close, volume, with a DatetimeIndex or 'date' column. VWAP/VWMA are NOT
here — reuse engine.indicators.calc_vwap / calc_vwma (DRY).
"""
import numpy as np
import pandas as pd


def volume_profile(df: pd.DataFrame, bins: int = 24) -> dict:
    """Volume-by-price histogram. Spreads each bar's volume across the
    [low, high] range it traded, then buckets into `bins` price bands.

    Returns: {poc, vah, val, rows:[{price, volume}]} where rows are
    ordered low→high price. POC = band with max volume. VAH/VAL bound the
    70% value area around POC.
    """
    if df is None or df.empty:
        return {'poc': None, 'vah': None, 'val': None, 'rows': []}

    lo = float(df['low'].min())
    hi = float(df['high'].max())
    if hi <= lo:
        hi = lo + 1.0
    edges = np.linspace(lo, hi, bins + 1)
    centers = (edges[:-1] + edges[1:]) / 2
    vol = np.zeros(bins)

    for _, r in df.iterrows():
        b_lo, b_hi, v = float(r['low']), float(r['high']), float(r['volume'])
        if b_hi <= b_lo:
            # flat bar — dump all volume in its band
            i = min(int(np.searchsorted(edges, b_lo, side='right')) - 1, bins - 1)
            vol[max(i, 0)] += v
            continue
        # overlap fraction of this bar's range with each band
        ov_lo = np.maximum(edges[:-1], b_lo)
        ov_hi = np.minimum(edges[1:], b_hi)
        ov = np.clip(ov_hi - ov_lo, 0, None)
        frac = ov / (b_hi - b_lo)
        vol += frac * v

    poc_i = int(np.argmax(vol))
    poc = float(centers[poc_i])

    # 70% value area expanding from POC
    target = vol.sum() * 0.70
    lo_i = hi_i = poc_i
    acc = vol[poc_i]
    while acc < target and (lo_i > 0 or hi_i < bins - 1):
        down = vol[lo_i - 1] if lo_i > 0 else -1
        up = vol[hi_i + 1] if hi_i < bins - 1 else -1
        if up >= down:
            hi_i += 1
            acc += vol[hi_i]
        else:
            lo_i -= 1
            acc += vol[lo_i]

    rows = [{'price': round(float(centers[i]), 2), 'volume': round(float(vol[i]), 2)}
            for i in range(bins)]
    return {'poc': round(poc, 2),
            'vah': round(float(centers[hi_i]), 2),
            'val': round(float(centers[lo_i]), 2),
            'rows': rows}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_chart_indicators.py::test_volume_profile_poc_at_highest_volume_band -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add engine/chart_indicators.py tests/test_chart_indicators.py
git commit -m "feat(charts): volume_profile indicator

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Fair Value Gaps

**Files:**
- Modify: `engine/chart_indicators.py`
- Test: `tests/test_chart_indicators.py`

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_chart_indicators.py
from engine.chart_indicators import fair_value_gaps


def test_fair_value_gaps_detects_bull_and_bear():
    # Bull FVG: bar3.low (106) > bar1.high (102)  -> gap 102..106 at bar2/3
    # Bear FVG: bar3.high (94) < bar1.low (98)    -> gap 94..98
    bull = _df([
        ('2026-01-01', 100, 102, 99, 101, 100),
        ('2026-01-02', 103, 109, 103, 108, 100),
        ('2026-01-03', 107, 110, 106, 109, 100),
    ])
    gaps = fair_value_gaps(bull)
    assert any(g['type'] == 'bull' and g['bottom'] == 102 and g['top'] == 106 for g in gaps)

    bear = _df([
        ('2026-01-01', 100, 101, 98, 99, 100),
        ('2026-01-02', 95, 96, 90, 91, 100),
        ('2026-01-03', 93, 94, 90, 92, 100),
    ])
    gaps2 = fair_value_gaps(bear)
    assert any(g['type'] == 'bear' and g['bottom'] == 94 and g['top'] == 98 for g in gaps2)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_chart_indicators.py::test_fair_value_gaps_detects_bull_and_bear -v`
Expected: FAIL — `ImportError: cannot import name 'fair_value_gaps'`

- [ ] **Step 3: Write minimal implementation**

```python
# append to engine/chart_indicators.py
def fair_value_gaps(df: pd.DataFrame) -> list:
    """3-candle imbalance. Bullish gap when low[i] > high[i-2]; bearish
    when high[i] < low[i-2]. Zone = the gap between those two extremes,
    stamped at candle i's date.

    Returns: [{type:'bull'|'bear', top, bottom, date}] (most recent last).
    """
    if df is None or len(df) < 3:
        return []
    out = []
    highs = df['high'].values
    lows = df['low'].values
    if isinstance(df.index, pd.DatetimeIndex):
        dates = [d.strftime('%Y-%m-%d') for d in df.index]
    else:
        dates = [str(d) for d in df.get('date', range(len(df)))]
    for i in range(2, len(df)):
        if lows[i] > highs[i - 2]:
            out.append({'type': 'bull',
                        'bottom': round(float(highs[i - 2]), 2),
                        'top': round(float(lows[i]), 2),
                        'date': dates[i]})
        elif highs[i] < lows[i - 2]:
            out.append({'type': 'bear',
                        'bottom': round(float(highs[i]), 2),
                        'top': round(float(lows[i - 2]), 2),
                        'date': dates[i]})
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_chart_indicators.py::test_fair_value_gaps_detects_bull_and_bear -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add engine/chart_indicators.py tests/test_chart_indicators.py
git commit -m "feat(charts): fair_value_gaps indicator

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Support / Resistance

**Files:**
- Modify: `engine/chart_indicators.py`
- Test: `tests/test_chart_indicators.py`

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_chart_indicators.py
from engine.chart_indicators import support_resistance


def test_support_resistance_finds_pivots():
    # Build a zig-zag: clear swing high at 120, clear swing low at 80.
    rows = []
    prices = [100, 105, 120, 108, 95, 80, 92, 110, 100, 90]
    for i, p in enumerate(prices, 1):
        d = f'2026-01-{i:02d}'
        rows.append((d, p, p + 2, p - 2, p, 100))
    df = _df(rows)
    sr = support_resistance(df, lookback=1, max_levels=6)
    assert set(sr.keys()) == {'support', 'resistance'}
    # swing high 120 -> resistance near 122 (high = p+2); swing low 80 -> support near 78
    assert any(abs(r - 122) < 3 for r in sr['resistance'])
    assert any(abs(s - 78) < 3 for s in sr['support'])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_chart_indicators.py::test_support_resistance_finds_pivots -v`
Expected: FAIL — `ImportError: cannot import name 'support_resistance'`

- [ ] **Step 3: Write minimal implementation**

```python
# append to engine/chart_indicators.py
def support_resistance(df: pd.DataFrame, lookback: int = 5, max_levels: int = 6) -> dict:
    """Swing-pivot S/R. A pivot-high is a bar whose high is the max within
    +/- lookback bars; pivot-low symmetrically on lows. Returns the most
    recent `max_levels` of each, sorted by price.

    Returns: {support:[...], resistance:[...]}.
    """
    if df is None or len(df) < (2 * lookback + 1):
        return {'support': [], 'resistance': []}
    highs = df['high'].values
    lows = df['low'].values
    res, sup = [], []
    n = len(df)
    for i in range(lookback, n - lookback):
        win_h = highs[i - lookback:i + lookback + 1]
        win_l = lows[i - lookback:i + lookback + 1]
        if highs[i] == win_h.max():
            res.append((i, round(float(highs[i]), 2)))
        if lows[i] == win_l.min():
            sup.append((i, round(float(lows[i]), 2)))
    # most recent first, take max_levels, then sort by price
    res_levels = sorted({p for _, p in sorted(res, reverse=True)[:max_levels]})
    sup_levels = sorted({p for _, p in sorted(sup, reverse=True)[:max_levels]})
    return {'support': sup_levels, 'resistance': res_levels}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_chart_indicators.py::test_support_resistance_finds_pivots -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add engine/chart_indicators.py tests/test_chart_indicators.py
git commit -m "feat(charts): support_resistance indicator

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Candlestick Pattern Detection

**Files:**
- Modify: `engine/chart_indicators.py`
- Test: `tests/test_chart_indicators.py`

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_chart_indicators.py
from engine.chart_indicators import detect_patterns


def test_detect_patterns_bullish_engulfing_and_doji():
    df = _df([
        ('2026-01-01', 100, 100.5, 95, 96, 100),    # down candle
        ('2026-01-02', 95, 103, 94.5, 102, 100),    # bullish engulfing of prev body
        ('2026-01-03', 100, 101, 99, 100.05, 100),  # doji (open~close)
    ])
    pats = detect_patterns(df)
    kinds = {(p['date'], p['pattern']) for p in pats}
    assert ('2026-01-02', 'bullish_engulfing') in kinds
    assert ('2026-01-03', 'doji') in kinds
    assert all(p['dir'] in ('bull', 'bear', 'neutral') for p in pats)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_chart_indicators.py::test_detect_patterns_bullish_engulfing_and_doji -v`
Expected: FAIL — `ImportError: cannot import name 'detect_patterns'`

- [ ] **Step 3: Write minimal implementation**

```python
# append to engine/chart_indicators.py
def detect_patterns(df: pd.DataFrame) -> list:
    """Classic single/two-candle patterns: doji, hammer, shooting_star,
    bullish_engulfing, bearish_engulfing.

    Returns: [{date, pattern, dir}] where dir in bull|bear|neutral.
    """
    if df is None or df.empty:
        return []
    o = df['open'].values; h = df['high'].values
    l = df['low'].values; c = df['close'].values
    if isinstance(df.index, pd.DatetimeIndex):
        dates = [d.strftime('%Y-%m-%d') for d in df.index]
    else:
        dates = [str(d) for d in df.get('date', range(len(df)))]
    out = []
    for i in range(len(df)):
        rng = h[i] - l[i]
        if rng <= 0:
            continue
        body = abs(c[i] - o[i])
        upper = h[i] - max(o[i], c[i])
        lower = min(o[i], c[i]) - l[i]
        if body <= rng * 0.1:
            out.append({'date': dates[i], 'pattern': 'doji', 'dir': 'neutral'})
        elif lower >= body * 2 and upper <= body:
            out.append({'date': dates[i], 'pattern': 'hammer', 'dir': 'bull'})
        elif upper >= body * 2 and lower <= body:
            out.append({'date': dates[i], 'pattern': 'shooting_star', 'dir': 'bear'})
        if i > 0:
            # engulfing vs previous body
            prev_bull = c[i - 1] >= o[i - 1]
            cur_bull = c[i] >= o[i]
            if cur_bull and not prev_bull and c[i] >= o[i - 1] and o[i] <= c[i - 1]:
                out.append({'date': dates[i], 'pattern': 'bullish_engulfing', 'dir': 'bull'})
            elif not cur_bull and prev_bull and o[i] >= c[i - 1] and c[i] <= o[i - 1]:
                out.append({'date': dates[i], 'pattern': 'bearish_engulfing', 'dir': 'bear'})
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_chart_indicators.py -v`
Expected: PASS (all 4 indicator tests)

- [ ] **Step 5: Commit**

```bash
git add engine/chart_indicators.py tests/test_chart_indicators.py
git commit -m "feat(charts): detect_patterns indicator

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Phase 2 — Delta / Order-Flow Engine (`engine/delta_flow.py`)

### Task 5: Flow-bar loader + CVD

**Files:**
- Create: `engine/delta_flow.py`
- Test: `tests/test_delta_flow.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_delta_flow.py
import sqlite3
import pandas as pd
import pytest
from engine import delta_flow


@pytest.fixture
def flow_db(tmp_path):
    db = tmp_path / "wf.db"
    conn = sqlite3.connect(db)
    conn.execute("""CREATE TABLE stockbit_flow_bars (
        ticker TEXT, trade_date TEXT, bar_time TEXT,
        buy_lot INTEGER, sell_lot INTEGER, buy_freq INTEGER, sell_freq INTEGER,
        net_value INTEGER, price INTEGER, delta INTEGER,
        PRIMARY KEY (ticker, trade_date, bar_time))""")
    rows = [
        ('BBCA', '2026-06-15', '09:00', 100, 40, 5, 3, 1000, 100, 60),
        ('BBCA', '2026-06-15', '09:01', 50, 90, 4, 6, -800, 101, -40),
        ('BBCA', '2026-06-15', '09:02', 70, 70, 4, 4, 0, 100, 0),
    ]
    conn.executemany("INSERT INTO stockbit_flow_bars VALUES (?,?,?,?,?,?,?,?,?,?)", rows)
    conn.commit(); conn.close()
    return str(db)


def test_load_bars_returns_session(flow_db):
    df = delta_flow.load_bars('BBCA', '2026-06-15', db_path=flow_db)
    assert len(df) == 3
    assert list(df['delta']) == [60, -40, 0]


def test_cvd_is_cumulative(flow_db):
    series = delta_flow.cvd('BBCA', '2026-06-15', db_path=flow_db)
    assert [p['cvd'] for p in series] == [60, 20, 20]
    assert series[0]['time'] == '09:00'
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_delta_flow.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'engine.delta_flow'`

- [ ] **Step 3: Write minimal implementation**

```python
# engine/delta_flow.py
"""ATAS-style order-flow delta from Stockbit 1-minute bars.

Reads stockbit_flow_bars (1-min granularity, ~28-day rolling history from
2026-04-20). delta = buy_lot - sell_lot. Granularity is 1-minute, NOT
tick-level — delta_by_price is a 1-min approximation of a footprint.
"""
import sqlite3
import pandas as pd
from config import DB_PATH

EARLIEST_DATE = '2026-04-20'


def load_bars(ticker: str, date: str, db_path: str = DB_PATH) -> pd.DataFrame:
    """Return the session's 1-min bars for ticker/date, ordered by bar_time.
    Empty DataFrame if none."""
    conn = sqlite3.connect(db_path)
    try:
        df = pd.read_sql_query(
            "SELECT bar_time, buy_lot, sell_lot, buy_freq, sell_freq, "
            "net_value, price, delta FROM stockbit_flow_bars "
            "WHERE ticker=? AND trade_date=? ORDER BY bar_time ASC",
            conn, params=(ticker.upper(), date))
    finally:
        conn.close()
    return df


def cvd(ticker: str, date: str, db_path: str = DB_PATH) -> list:
    """Cumulative Volume Delta series: [{time, cvd}]."""
    df = load_bars(ticker, date, db_path)
    if df.empty:
        return []
    cum = df['delta'].cumsum()
    return [{'time': t, 'cvd': int(v)} for t, v in zip(df['bar_time'], cum)]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_delta_flow.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add engine/delta_flow.py tests/test_delta_flow.py
git commit -m "feat(charts): delta_flow loader + cvd

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: delta_bars, delta_by_price, session stats, imbalances, EMA

**Files:**
- Modify: `engine/delta_flow.py`
- Test: `tests/test_delta_flow.py`

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_delta_flow.py
def test_delta_by_price_buckets(flow_db):
    prof = delta_flow.delta_by_price('BBCA', '2026-06-15', bins=2, db_path=flow_db)
    # prices 100,101,100 -> deltas 60,-40,0 ; volumes (buy+sell) 140,140,140
    assert all(set(r.keys()) == {'price', 'volume', 'delta'} for r in prof)
    assert sum(r['delta'] for r in prof) == 20      # net delta conserved
    assert sum(r['volume'] for r in prof) == 420    # total lots conserved


def test_session_delta_stats(flow_db):
    s = delta_flow.session_delta_stats('BBCA', '2026-06-15', db_path=flow_db)
    assert s['total_delta'] == 20
    assert s['buy_lot'] == 220 and s['sell_lot'] == 200
    assert s['net_value'] == 200


def test_out_of_window_returns_note(flow_db):
    s = delta_flow.session_delta_stats('BBCA', '2026-01-01', db_path=flow_db)
    assert s['total_delta'] == 0 and 'note' in s


def test_cvd_ema_length():
    series = [{'time': f'09:{i:02d}', 'cvd': i} for i in range(10)]
    ema = delta_flow.cvd_ema(series, length=3)
    assert len(ema) == len(series)
    assert ema[-1]['ema'] is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_delta_flow.py -v`
Expected: FAIL — `AttributeError: module 'engine.delta_flow' has no attribute 'delta_by_price'`

- [ ] **Step 3: Write minimal implementation**

```python
# append to engine/delta_flow.py
import numpy as np


def delta_bars(ticker: str, date: str, db_path: str = DB_PATH) -> list:
    """Per-minute delta histogram: [{time, delta, buy, sell}]."""
    df = load_bars(ticker, date, db_path)
    if df.empty:
        return []
    return [{'time': t, 'delta': int(d), 'buy': int(b), 'sell': int(s)}
            for t, d, b, s in zip(df['bar_time'], df['delta'],
                                  df['buy_lot'], df['sell_lot'])]


def delta_by_price(ticker: str, date: str, bins: int = 24, db_path: str = DB_PATH) -> list:
    """Footprint-lite: bucket 1-min bars by price, summing volume (buy+sell)
    and net delta per band. Returns [{price, volume, delta}] low->high.
    1-MINUTE APPROXIMATION of a tick footprint."""
    df = load_bars(ticker, date, db_path)
    if df.empty:
        return []
    prices = df['price'].astype(float).values
    vols = (df['buy_lot'] + df['sell_lot']).astype(float).values
    deltas = df['delta'].astype(float).values
    lo, hi = prices.min(), prices.max()
    if hi <= lo:
        return [{'price': round(float(lo), 2),
                 'volume': int(vols.sum()), 'delta': int(deltas.sum())}]
    edges = np.linspace(lo, hi, bins + 1)
    centers = (edges[:-1] + edges[1:]) / 2
    idx = np.clip(np.searchsorted(edges, prices, side='right') - 1, 0, bins - 1)
    out = []
    for b in range(bins):
        m = idx == b
        if not m.any():
            continue
        out.append({'price': round(float(centers[b]), 2),
                    'volume': int(vols[m].sum()),
                    'delta': int(deltas[m].sum())})
    return out


def session_delta_stats(ticker: str, date: str, db_path: str = DB_PATH) -> dict:
    """Aggregate session stats. Out-of-window dates return zeros + a note."""
    df = load_bars(ticker, date, db_path)
    if df.empty:
        note = ('no order-flow data before %s' % EARLIEST_DATE
                if date < EARLIEST_DATE else 'no order-flow data for this date')
        return {'total_delta': 0, 'buy_lot': 0, 'sell_lot': 0,
                'net_value': 0, 'note': note}
    return {'total_delta': int(df['delta'].sum()),
            'buy_lot': int(df['buy_lot'].sum()),
            'sell_lot': int(df['sell_lot'].sum()),
            'net_value': int(df['net_value'].sum())}


def stacked_imbalances(ticker: str, date: str, z: float = 2.0, db_path: str = DB_PATH) -> list:
    """Minutes whose |delta| spikes >= z standard deviations above the mean
    absolute delta. Returns [{time, price, delta}]."""
    df = load_bars(ticker, date, db_path)
    if df.empty:
        return []
    ad = df['delta'].abs()
    thresh = ad.mean() + z * ad.std(ddof=0)
    hot = df[ad >= thresh]
    return [{'time': t, 'price': int(p), 'delta': int(d)}
            for t, p, d in zip(hot['bar_time'], hot['price'], hot['delta'])]


def cvd_ema(series: list, length: int = 9) -> list:
    """EMA overlay for a cvd() series. Returns [{time, ema}]."""
    if not series:
        return []
    vals = pd.Series([p['cvd'] for p in series], dtype=float)
    ema = vals.ewm(span=length, adjust=False).mean()
    return [{'time': p['time'], 'ema': round(float(e), 2)}
            for p, e in zip(series, ema)]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_delta_flow.py -v`
Expected: PASS (all 6 delta tests)

- [ ] **Step 5: Commit**

```bash
git add engine/delta_flow.py tests/test_delta_flow.py
git commit -m "feat(charts): delta_by_price, session stats, imbalances, cvd_ema

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Phase 3 — TradingView CDP Bridge (`engine/tv_bridge.py`)

### Task 7: CDP symbol-sync bridge (fail-open)

**Files:**
- Create: `engine/tv_bridge.py`
- Test: `tests/test_tv_bridge.py`

Note: uses stdlib only — `urllib.request` for `/json`, and a tiny websocket frame writer is avoided by using the `websocket-client` package **if present**, else falls back to reporting unavailable. Check availability: `python3 -c "import websocket"`. If missing: `pip install websocket-client`. The test mocks both paths, so it passes without the package.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_tv_bridge.py
from unittest import mock
from engine import tv_bridge


def test_set_symbol_builds_expression_and_calls_cdp():
    captured = {}

    def fake_eval(ws_url, expression):
        captured['ws_url'] = ws_url
        captured['expr'] = expression
        return {'result': {'type': 'undefined'}}

    with mock.patch.object(tv_bridge, '_active_ws_url', return_value='ws://x/devtools/page/1'), \
         mock.patch.object(tv_bridge, '_cdp_evaluate', side_effect=fake_eval):
        res = tv_bridge.set_symbol('BBCA')
    assert res['ok'] is True
    assert 'setSymbol("BBCA"' in captured['expr']
    assert '_activeChartWidgetWV' in captured['expr']


def test_set_symbol_fail_open_when_cdp_down():
    with mock.patch.object(tv_bridge, '_active_ws_url',
                           side_effect=ConnectionError('refused')):
        res = tv_bridge.set_symbol('BBRI')
    assert res['ok'] is False
    assert 'reason' in res


def test_set_symbol_sanitizes_input():
    with mock.patch.object(tv_bridge, '_active_ws_url', return_value='ws://x/1'), \
         mock.patch.object(tv_bridge, '_cdp_evaluate', return_value={}) as ev:
        tv_bridge.set_symbol('BB"CA')  # quote must be stripped/escaped
    expr = ev.call_args[0][1]
    assert 'BB"CA' not in expr  # raw unescaped quote not injected
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_tv_bridge.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'engine.tv_bridge'`

- [ ] **Step 3: Write minimal implementation**

```python
# engine/tv_bridge.py
"""Drive the TradingView Desktop chart over Chrome DevTools Protocol.

TV Desktop runs with remote debugging on port 9222. One job: set the
active chart symbol. Every public method is FAIL-OPEN — connection errors
return {'ok': False, 'reason': ...} and never raise into a Flask request.
"""
import json
import re
import urllib.request

CDP_HOST = 'localhost'
CDP_PORT = 9222
CHART_API = 'window.TradingViewApi._activeChartWidgetWV.value()'
_TIMEOUT = 4


def _http_json(path: str):
    url = f'http://{CDP_HOST}:{CDP_PORT}{path}'
    with urllib.request.urlopen(url, timeout=_TIMEOUT) as r:
        return json.loads(r.read().decode())


def is_available() -> bool:
    try:
        _http_json('/json/version')
        return True
    except Exception:
        return False


def _active_ws_url() -> str:
    """Pick the TradingView chart page's debugger websocket URL."""
    pages = _http_json('/json')
    for p in pages:
        if p.get('type') == 'page' and 'tradingview' in (p.get('url') or '').lower():
            return p['webSocketDebuggerUrl']
    # fall back to first page with a ws url
    for p in pages:
        if p.get('webSocketDebuggerUrl'):
            return p['webSocketDebuggerUrl']
    raise ConnectionError('no debuggable TradingView page found')


def _cdp_evaluate(ws_url: str, expression: str) -> dict:
    """Send Runtime.evaluate over the CDP websocket. Requires websocket-client."""
    import websocket  # lazy import; optional dependency
    ws = websocket.create_connection(ws_url, timeout=_TIMEOUT)
    try:
        ws.send(json.dumps({'id': 1, 'method': 'Runtime.evaluate',
                            'params': {'expression': expression,
                                       'returnByValue': True}}))
        while True:
            msg = json.loads(ws.recv())
            if msg.get('id') == 1:
                return msg.get('result', {})
    finally:
        ws.close()


def _safe_symbol(symbol: str) -> str:
    """Allow only ticker-safe chars (letters, digits, :, ., -)."""
    return re.sub(r'[^A-Za-z0-9:.\-]', '', symbol or '').upper()


def set_symbol(symbol: str) -> dict:
    """Set the active TV Desktop chart symbol. Fail-open."""
    sym = _safe_symbol(symbol)
    if not sym:
        return {'ok': False, 'reason': 'empty/invalid symbol'}
    try:
        ws_url = _active_ws_url()
        expr = f'{CHART_API}.setSymbol("{sym}", {{}})'
        _cdp_evaluate(ws_url, expr)
        return {'ok': True, 'symbol': sym}
    except Exception as e:
        return {'ok': False, 'reason': str(e)}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_tv_bridge.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add engine/tv_bridge.py tests/test_tv_bridge.py
git commit -m "feat(charts): tv_bridge CDP symbol sync (fail-open)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Phase 4 — Routes (`routes/chart.py`)

### Task 8: Chart blueprint — indicators, delta, TV sync/status

**Files:**
- Create: `routes/chart.py`
- Modify: `app.py:18` (import) and `app.py:34` (register)
- Test: `tests/test_chart_routes.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_chart_routes.py
import sqlite3
import pytest
from unittest import mock


@pytest.fixture
def client(tmp_path, monkeypatch):
    db = tmp_path / "wf.db"
    conn = sqlite3.connect(db)
    conn.execute("""CREATE TABLE ohlcv (ticker TEXT, date TEXT, open REAL,
        high REAL, low REAL, close REAL, volume REAL, UNIQUE(ticker,date))""")
    conn.execute("""CREATE TABLE stockbit_flow_bars (ticker TEXT, trade_date TEXT,
        bar_time TEXT, buy_lot INT, sell_lot INT, buy_freq INT, sell_freq INT,
        net_value INT, price INT, delta INT,
        PRIMARY KEY(ticker,trade_date,bar_time))""")
    for i in range(1, 40):
        conn.execute("INSERT INTO ohlcv VALUES (?,?,?,?,?,?,?)",
                     ('BBCA', f'2026-05-{i:02d}', 100, 105, 95, 100 + i % 5, 1000))
    conn.execute("INSERT INTO stockbit_flow_bars VALUES (?,?,?,?,?,?,?,?,?,?)",
                 ('BBCA', '2026-06-15', '09:00', 100, 40, 5, 3, 1000, 100, 60))
    conn.commit(); conn.close()

    monkeypatch.setenv('DB_PATH', str(db))
    import importlib, config
    importlib.reload(config)
    from routes import chart as chart_mod
    importlib.reload(chart_mod)

    from flask import Flask
    app = Flask(__name__)
    app.register_blueprint(chart_mod.chart_bp)
    return app.test_client(), chart_mod


def test_indicators_bundle_shape(client):
    c, _ = client
    r = c.get('/api/chart/BBCA/indicators?tf=D&inds=vp,fvg,sr,vwap,vwma,patterns')
    assert r.status_code == 200
    j = r.get_json()
    assert 'vp' in j and 'fvg' in j and 'sr' in j
    assert 'vwap' in j and 'vwma' in j and 'patterns' in j


def test_delta_bundle_shape(client):
    c, _ = client
    r = c.get('/api/chart/BBCA/delta?date=2026-06-15&parts=cvd,bars,profile,stats')
    assert r.status_code == 200
    j = r.get_json()
    assert j['cvd'][0]['cvd'] == 60
    assert j['stats']['total_delta'] == 60


def test_tv_sync_calls_bridge(client):
    c, mod = client
    with mock.patch.object(mod.tv_bridge, 'set_symbol',
                           return_value={'ok': True, 'symbol': 'BBCA'}) as m:
        r = c.post('/api/chart/tv/sync', json={'symbol': 'BBCA'})
    assert r.status_code == 200 and r.get_json()['ok'] is True
    m.assert_called_once_with('BBCA')


def test_tv_status(client):
    c, mod = client
    with mock.patch.object(mod.tv_bridge, 'is_available', return_value=False):
        r = c.get('/api/chart/tv/status')
    assert r.get_json()['available'] is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_chart_routes.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'routes.chart'`

- [ ] **Step 3: Write minimal implementation**

```python
# routes/chart.py
"""Chart overlays, order-flow delta, and TradingView sync endpoints.

Candle OHLCV itself is served by the existing /api/ticker/... routes; this
blueprint only adds computed overlays (engine.chart_indicators), delta
(engine.delta_flow), and the TV CDP bridge (engine.tv_bridge).
"""
import sqlite3
import pandas as pd
from flask import Blueprint, jsonify, request

from config import DB_PATH
from engine import chart_indicators as ci
from engine import delta_flow
from engine import tv_bridge
from engine.indicators import calc_vwap, calc_vwma
from engine.timeframe import aggregate_ohlcv

chart_bp = Blueprint('chart', __name__)


def _load_ohlcv(ticker: str, freq: str) -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH)
    try:
        df = pd.read_sql_query(
            "SELECT date, open, high, low, close, volume FROM ohlcv "
            "WHERE ticker=? ORDER BY date ASC", conn, params=(ticker.upper(),))
    finally:
        conn.close()
    if df.empty:
        return df
    df['date'] = pd.to_datetime(df['date'])
    df = df.set_index('date')
    f = (freq or 'D').upper()
    if f in ('W', 'M', 'ME'):
        df = aggregate_ohlcv(df, f)
    return df


def _series_tail(s: pd.Series, n: int = 250) -> list:
    s = s.dropna().tail(n)
    return [{'date': d.strftime('%Y-%m-%d'), 'value': round(float(v), 2)}
            for d, v in s.items()]


@chart_bp.route('/api/chart/<ticker>/indicators', methods=['GET'])
def indicators(ticker):
    tf = request.args.get('tf', 'D')
    inds = set((request.args.get('inds', '') or '').split(','))
    df = _load_ohlcv(ticker, tf)
    if df.empty:
        return jsonify({'error': f'no data for {ticker}'}), 404
    out = {}
    if 'vp' in inds:
        out['vp'] = ci.volume_profile(df)
    if 'fvg' in inds:
        out['fvg'] = ci.fair_value_gaps(df)
    if 'sr' in inds:
        out['sr'] = ci.support_resistance(df)
    if 'patterns' in inds:
        out['patterns'] = ci.detect_patterns(df)
    if 'vwap' in inds:
        out['vwap'] = _series_tail(calc_vwap(df, window=min(60, len(df))))
    if 'vwma' in inds:
        out['vwma'] = _series_tail(calc_vwma(df, period=min(20, len(df))))
    return jsonify(out)


@chart_bp.route('/api/chart/<ticker>/delta', methods=['GET'])
def delta(ticker):
    date = request.args.get('date')
    if not date:
        return jsonify({'error': 'date required (YYYY-MM-DD)'}), 400
    parts = set((request.args.get('parts', 'cvd,bars,profile,stats') or '').split(','))
    out = {}
    if 'cvd' in parts:
        series = delta_flow.cvd(ticker, date)
        out['cvd'] = series
        out['cvd_ema'] = delta_flow.cvd_ema(series)
    if 'bars' in parts:
        out['bars'] = delta_flow.delta_bars(ticker, date)
    if 'profile' in parts:
        out['profile'] = delta_flow.delta_by_price(ticker, date)
    if 'stats' in parts:
        out['stats'] = delta_flow.session_delta_stats(ticker, date)
    if 'imbalance' in parts:
        out['imbalance'] = delta_flow.stacked_imbalances(ticker, date)
    return jsonify(out)


@chart_bp.route('/api/chart/tv/sync', methods=['POST'])
def tv_sync():
    body = request.get_json(silent=True) or {}
    symbol = body.get('symbol', '')
    return jsonify(tv_bridge.set_symbol(symbol))


@chart_bp.route('/api/chart/tv/status', methods=['GET'])
def tv_status():
    return jsonify({'available': tv_bridge.is_available()})
```

Then wire into `app.py`:

```python
# app.py — add with the other route imports (near line 18)
from routes.chart import chart_bp
# app.py — add with the other register_blueprint calls (near line 34)
app.register_blueprint(chart_bp)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_chart_routes.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Verify app still imports**

Run: `python3 -c "import app; print('ok')"`
Expected: `ok`

- [ ] **Step 6: Commit**

```bash
git add routes/chart.py app.py tests/test_chart_routes.py
git commit -m "feat(charts): chart blueprint — indicators, delta, TV sync

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Phase 5 — Frontend (Workspace panel)

### Task 9: charts.css + charts.js (pane grid, render, controls)

**Files:**
- Create: `static/charts.css`
- Create: `static/charts.js`
- Test: manual (browser) — steps below

- [ ] **Step 1: Write `static/charts.css`**

```css
/* static/charts.css — multi-pane chart viewer */
.cv-wrap { display:flex; flex-direction:column; gap:8px; height:100%; }
.cv-toolbar { display:flex; align-items:center; gap:8px; flex-wrap:wrap; }
.cv-toolbar .cv-layout-btn,
.cv-toolbar .cv-ind-chip {
  background:var(--surface-2); border:1px solid var(--border-hi);
  color:var(--text-dim); border-radius:8px; padding:4px 10px; font-size:12px;
}
.cv-toolbar .cv-layout-btn.active { background:var(--indigo-dim); color:var(--indigo-2); }
.cv-ind-chip.on { background:var(--green-dim); color:var(--green); border-color:var(--green); }
.cv-tv-dot { width:8px; height:8px; border-radius:50%; background:var(--text-mute); }
.cv-tv-dot.live { background:var(--green); }

.cv-grid { display:grid; gap:8px; flex:1; min-height:480px; }
.cv-grid[data-panes="1"] { grid-template-columns:1fr; }
.cv-grid[data-panes="2"] { grid-template-columns:1fr 1fr; }
.cv-grid[data-panes="4"] { grid-template-columns:1fr 1fr; grid-template-rows:1fr 1fr; }
.cv-grid[data-panes="6"] { grid-template-columns:repeat(3,1fr); grid-template-rows:1fr 1fr; }

.cv-pane { display:flex; flex-direction:column; background:var(--surface);
  border:1px solid var(--border); border-radius:var(--radius); overflow:hidden; }
.cv-pane.focused { border-color:var(--indigo); }
.cv-pane-head { display:flex; align-items:center; gap:6px; padding:6px 8px;
  border-bottom:1px solid var(--border-soft); }
.cv-pane-head input { width:84px; background:var(--bg-elev); border:1px solid var(--border-hi);
  border-radius:6px; padding:3px 6px; font-size:12px; text-transform:uppercase; }
.cv-pane-head select { background:var(--bg-elev); border:1px solid var(--border-hi);
  border-radius:6px; padding:3px 6px; font-size:12px; }
.cv-pane-head .cv-stat { margin-left:auto; font-family:var(--mono); font-size:11px; color:var(--text-dim); }
.cv-chart { flex:1; min-height:0; }
.cv-delta-note { font-size:11px; color:var(--amber); padding:2px 8px; }
```

- [ ] **Step 2: Write `static/charts.js`**

```javascript
/* static/charts.js — multi-pane lightweight-charts viewer
   Depends on global LightweightCharts (loaded in workspace.html). */
(function () {
  const LC = window.LightweightCharts;
  const ALL_INDS = ['vp', 'fvg', 'sr', 'vwap', 'vwma', 'patterns'];
  const state = { panes: 4, focused: 0, inds: new Set(['vwap']), charts: [] };

  function el(tag, cls, html) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (html != null) e.innerHTML = html;
    return e;
  }

  async function fetchJSON(url, opts) {
    const r = await fetch(url, opts);
    if (!r.ok) throw new Error(url + ' -> ' + r.status);
    return r.json();
  }

  async function loadCandles(ticker, tf) {
    if (tf === '1h') {
      const j = await fetchJSON(`/api/ticker/${ticker}/ohlcv?tf=1h`);
      return (j.candles || []).map(c => ({
        time: c.time, open: c.open, high: c.high, low: c.low, close: c.close }));
    }
    const freq = tf === 'W' ? 'W' : tf === 'M' ? 'ME' : 'D';
    const j = await fetchJSON(`/api/ticker/${ticker}/ohlcv/${freq}?limit=300`);
    return (j.bars || []).map(b => ({
      time: b.date, open: b.open, high: b.high, low: b.low, close: b.close }));
  }

  function syncTV(symbol) {
    fetch('/api/chart/tv/sync', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ symbol })
    }).catch(() => {});
  }

  async function renderPane(paneEl, i) {
    const ticker = paneEl.querySelector('input').value.trim().toUpperCase();
    const tf = paneEl.querySelector('select').value;
    const chartHost = paneEl.querySelector('.cv-chart');
    const statEl = paneEl.querySelector('.cv-stat');
    chartHost.innerHTML = '';
    if (!ticker) return;

    const chart = LC.createChart(chartHost, {
      layout: { background: { color: '#0f162e' }, textColor: '#97a3c0' },
      grid: { vertLines: { visible: false }, horzLines: { color: '#151f3a' } },
      rightPriceScale: { borderColor: '#1b2547' },
      timeScale: { borderColor: '#1b2547' },
      autoSize: true,
    });
    const candleSeries = chart.addCandlestickSeries({
      upColor: '#10b981', downColor: '#ef4444',
      wickUpColor: '#10b981', wickDownColor: '#ef4444', borderVisible: false });
    let candles = [];
    try { candles = await loadCandles(ticker, tf); } catch (e) { statEl.textContent = 'no data'; return; }
    candleSeries.setData(candles);

    // overlays
    try {
      const inds = [...state.inds].filter(x => ALL_INDS.includes(x));
      if (inds.length) {
        const ov = await fetchJSON(`/api/chart/${ticker}/indicators?tf=${tf}&inds=${inds.join(',')}`);
        applyOverlays(chart, candleSeries, candles, ov);
      }
    } catch (e) { /* overlays are best-effort */ }

    // delta sub-pane stat
    if (tf === '1h' || tf === 'D') {
      try {
        const date = candles.length ? String(candles[candles.length - 1].time).slice(0, 10) : '';
        if (date) {
          const d = await fetchJSON(`/api/chart/${ticker}/delta?date=${date}&parts=stats`);
          if (d.stats && d.stats.note) {
            statEl.textContent = d.stats.note;
          } else if (d.stats) {
            const sign = d.stats.total_delta >= 0 ? '+' : '';
            statEl.textContent = `Δ ${sign}${d.stats.total_delta}`;
            statEl.style.color = d.stats.total_delta >= 0 ? '#10b981' : '#ef4444';
          }
        }
      } catch (e) { /* delta optional */ }
    }
    chart.timeScale().fitContent();
    state.charts[i] = chart;
  }

  function applyOverlays(chart, candleSeries, candles, ov) {
    if (ov.vwap && ov.vwap.length) {
      const s = chart.addLineSeries({ color: '#f59e0b', lineWidth: 1 });
      s.setData(ov.vwap.map(p => ({ time: p.date, value: p.value })));
    }
    if (ov.vwma && ov.vwma.length) {
      const s = chart.addLineSeries({ color: '#3b82f6', lineWidth: 1 });
      s.setData(ov.vwma.map(p => ({ time: p.date, value: p.value })));
    }
    if (ov.sr) {
      (ov.sr.resistance || []).forEach(p =>
        candleSeries.createPriceLine({ price: p, color: '#ef4444', lineStyle: 2, lineWidth: 1 }));
      (ov.sr.support || []).forEach(p =>
        candleSeries.createPriceLine({ price: p, color: '#10b981', lineStyle: 2, lineWidth: 1 }));
    }
    if (ov.vp && ov.vp.poc != null) {
      candleSeries.createPriceLine({ price: ov.vp.poc, color: '#818cf8', lineWidth: 2, title: 'POC' });
      candleSeries.createPriceLine({ price: ov.vp.vah, color: '#6366f1', lineStyle: 1, title: 'VAH' });
      candleSeries.createPriceLine({ price: ov.vp.val, color: '#6366f1', lineStyle: 1, title: 'VAL' });
    }
    if (ov.patterns && ov.patterns.length) {
      const marks = ov.patterns.map(p => ({
        time: p.date,
        position: p.dir === 'bear' ? 'aboveBar' : 'belowBar',
        color: p.dir === 'bear' ? '#ef4444' : p.dir === 'bull' ? '#10b981' : '#97a3c0',
        shape: p.dir === 'bear' ? 'arrowDown' : 'arrowUp',
        text: p.pattern.replace(/_/g, ' ')
      }));
      candleSeries.setMarkers(marks);
    }
    if (ov.fvg && ov.fvg.length) {
      ov.fvg.slice(-12).forEach(g => {
        candleSeries.createPriceLine({
          price: (g.top + g.bottom) / 2,
          color: g.type === 'bull' ? 'rgba(16,185,129,0.5)' : 'rgba(239,68,68,0.5)',
          lineStyle: 3, lineWidth: 1, title: 'FVG' });
      });
    }
  }

  function renderAll() {
    document.querySelectorAll('.cv-pane').forEach((p, i) => renderPane(p, i));
  }

  function buildPane(i) {
    const pane = el('div', 'cv-pane' + (i === state.focused ? ' focused' : ''));
    pane.dataset.idx = i;
    const head = el('div', 'cv-pane-head');
    const inp = el('input'); inp.value = i === 0 ? 'BBCA' : '';
    inp.placeholder = 'ticker';
    const sel = el('select');
    ['1h', 'D', 'W', 'M'].forEach(t => {
      const o = el('option', null, t); o.value = t; if (t === 'D') o.selected = true; sel.appendChild(o);
    });
    const stat = el('span', 'cv-stat');
    head.append(inp, sel, stat);
    const chart = el('div', 'cv-chart');
    pane.append(head, chart);
    pane.addEventListener('click', () => {
      state.focused = i;
      document.querySelectorAll('.cv-pane').forEach(x => x.classList.remove('focused'));
      pane.classList.add('focused');
    });
    const reload = () => { renderPane(pane, i); if (inp.value.trim()) syncTV(inp.value.trim().toUpperCase()); };
    inp.addEventListener('change', reload);
    sel.addEventListener('change', () => renderPane(pane, i));
    return pane;
  }

  function buildGrid() {
    const grid = document.getElementById('cv-grid');
    if (!grid) return;
    grid.innerHTML = '';
    grid.dataset.panes = state.panes;
    for (let i = 0; i < state.panes; i++) grid.appendChild(buildPane(i));
    renderAll();
  }

  function buildToolbar() {
    const tb = document.getElementById('cv-toolbar');
    if (!tb) return;
    tb.innerHTML = '';
    [1, 2, 4, 6].forEach(n => {
      const b = el('button', 'cv-layout-btn' + (n === state.panes ? ' active' : ''), n + '');
      b.addEventListener('click', () => {
        state.panes = n; localStorage.setItem('cv_panes', n);
        tb.querySelectorAll('.cv-layout-btn').forEach(x => x.classList.remove('active'));
        b.classList.add('active'); buildGrid();
      });
      tb.appendChild(b);
    });
    ALL_INDS.forEach(ind => {
      const c = el('button', 'cv-ind-chip' + (state.inds.has(ind) ? ' on' : ''), ind.toUpperCase());
      c.addEventListener('click', () => {
        if (state.inds.has(ind)) state.inds.delete(ind); else state.inds.add(ind);
        c.classList.toggle('on'); renderAll();
      });
      tb.appendChild(c);
    });
    const dot = el('span', 'cv-tv-dot'); dot.id = 'cv-tv-dot';
    const lbl = el('span', null, 'TV'); lbl.style.fontSize = '11px'; lbl.style.color = '#97a3c0';
    tb.append(dot, lbl);
    fetch('/api/chart/tv/status').then(r => r.json()).then(j => {
      if (j.available) dot.classList.add('live');
    }).catch(() => {});
  }

  window.ChartViewer = {
    init() {
      const saved = parseInt(localStorage.getItem('cv_panes') || '4', 10);
      state.panes = [1, 2, 4, 6].includes(saved) ? saved : 4;
      buildToolbar();
      buildGrid();
    },
    // called by workspace when a signal row is clicked
    loadTicker(ticker) {
      const grid = document.getElementById('cv-grid');
      if (!grid) return;
      const pane = grid.children[state.focused] || grid.children[0];
      if (!pane) return;
      pane.querySelector('input').value = ticker.toUpperCase();
      renderPane(pane, state.focused);
      syncTV(ticker.toUpperCase());
    }
  };
})();
```

- [ ] **Step 3: Commit**

```bash
git add static/charts.css static/charts.js
git commit -m "feat(charts): frontend pane grid + overlays + TV sync

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 10: Wire panel into `workspace.html`

**Files:**
- Modify: `templates/workspace.html`

- [ ] **Step 1: Add the CSS/JS includes**

In `templates/workspace.html`, inside `{% block head %}` (after the existing `lightweight-charts` script on line 5), add:

```html
<link rel="stylesheet" href="{{ url_for('static', filename='charts.css') }}">
```

At the very end of the file (after the last existing script block), add:

```html
<script src="{{ url_for('static', filename='charts.js') }}"></script>
```

- [ ] **Step 2: Add the panel markup**

Find the Workspace main content container (the panel/section area). Add a new collapsible panel block:

```html
<section class="cv-wrap" id="chart-viewer">
  <div class="cv-toolbar" id="cv-toolbar"></div>
  <div class="cv-grid" id="cv-grid" data-panes="4"></div>
</section>
```

- [ ] **Step 3: Initialize on load + hook signal clicks**

Add an init call where the page wires up its other panels (inside the existing DOMContentLoaded / init flow):

```html
<script>
  document.addEventListener('DOMContentLoaded', function () {
    if (window.ChartViewer) window.ChartViewer.init();
  });
</script>
```

For the signal → chart hook: locate where signal rows are rendered in the existing Workspace JS. On a row's click handler, add:

```javascript
// inside the existing signal-row click handler, `ticker` already in scope
if (window.ChartViewer) window.ChartViewer.loadTicker(ticker);
```

If the signals list is rendered as a table where each row exposes the ticker (e.g. `data-ticker`), a delegated listener also works:

```javascript
document.addEventListener('click', function (e) {
  const row = e.target.closest('[data-ticker]');
  if (row && window.ChartViewer) window.ChartViewer.loadTicker(row.dataset.ticker);
});
```

- [ ] **Step 4: Manual verification**

Run the app (existing run command — Flask on port 5001), open the Workspace, and confirm:
1. Toolbar shows layout buttons 1/2/4/6 and indicator chips.
2. Default 4-pane grid renders; BBCA pane shows daily candles.
3. Toggling VWAP/VP/SR/Patterns chips redraws overlays.
4. Switching a pane timeframe to `D` shows a delta stat (Δ) in the pane header; an out-of-window date shows the "no order-flow data" note.
5. Clicking a signal row loads that ticker into the focused pane.
6. TV dot is green when TradingView Desktop is open; clicking a ticker changes the Desktop symbol.

Run smoke: `python3 -c "import app; print('app import ok')"`
Expected: `app import ok`

- [ ] **Step 5: Commit**

```bash
git add templates/workspace.html
git commit -m "feat(charts): mount chart viewer panel in Workspace + signal hook

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Phase 6 — Full Suite & Wrap

### Task 11: Run full test suite + dependency check

- [ ] **Step 1: Ensure `websocket-client` is available** (used by tv_bridge at runtime, optional)

Run: `python3 -c "import websocket; print('ws ok')"` — if it fails: `pip install websocket-client`
Note: tests pass without it (they mock `_cdp_evaluate`); it's only needed for live TV sync.

- [ ] **Step 2: Run the new tests**

Run: `python3 -m pytest tests/test_chart_indicators.py tests/test_delta_flow.py tests/test_tv_bridge.py tests/test_chart_routes.py -v`
Expected: all PASS.

- [ ] **Step 3: Run the full suite for regressions**

Run: `python3 -m pytest -q`
Expected: previously-passing tests still pass (the 583 baseline plus the new ones). Investigate any new failure before proceeding.

- [ ] **Step 4: Commit any fixups, then summarize**

```bash
git add -A
git commit -m "test(charts): full suite green for multi-pane chart viewer

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Self-Review (completed by author)

**Spec coverage:** VP (T1), FVG (T2), S&R (T3), patterns (T4), VWAP/VWMA reused (T8 route), CVD+EMA (T5/T6), delta bars/profile/stats/imbalance (T6), 28-day window note (T6), TV CDP sync fail-open (T7), routes bundle (T8), flexible 1/2/4/6 panes + overlays + TV dot (T9), Workspace mount + signal hook (T10), full suite (T11). All spec sections mapped.

**Placeholder scan:** No TBD/TODO; every code step has complete code. Frontend manual-verification steps are explicit observable checks, not placeholders.

**Type consistency:** `load_bars/cvd/cvd_ema/delta_bars/delta_by_price/session_delta_stats/stacked_imbalances` names match across delta_flow tasks and routes. `volume_profile/fair_value_gaps/support_resistance/detect_patterns` names match across indicator tasks and routes. `tv_bridge.set_symbol/is_available/_active_ws_url/_cdp_evaluate` match across bridge + routes + tests. Route paths (`/api/chart/<t>/indicators`, `/delta`, `/tv/sync`, `/tv/status`) match between routes and `charts.js`.
