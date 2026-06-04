# G4: VR Spike Context Classifier — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `classify_volume_context()` to `engine/indicators.py` that tags volume spikes as `crash_absorption`, `breakout_accumulation`, `exhaustion_distribution`, or `normal`; surface this tag in scoring, DB storage, and Telegram alerts.

**Architecture:** Pure function `classify_volume_context(df)` in `engine/indicators.py` uses last-bar indicators (VR, price-vs-20d-high, MA20, close-vs-open). Called from both `score_ticker()` and `score_ticker_reversal()` in `premover_detector.py`, whose return dicts gain a `vol_context` key. `_init_table()` migration adds the DB column; `_upsert_setup()` stores it; alert formatter shows a tag when non-normal.

**Tech Stack:** Python, pandas, SQLite, pytest.

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `engine/indicators.py` | **Modify** | Add `classify_volume_context()` at end of file |
| `engine/premover_detector.py` | **Modify** | Import + call in scorers, migration, upsert, alert format |
| `tests/test_volume_context.py` | **Create** | 5 tests |

---

## Task 1: `classify_volume_context()` + Tests

**Files:**
- Modify: `engine/indicators.py`
- Create: `tests/test_volume_context.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_volume_context.py`:

```python
"""Tests for classify_volume_context() in engine/indicators.py."""
import pandas as pd
import numpy as np
import pytest


def _make_df(n: int = 25, close: float = 1000.0, volume: float = 1_000_000.0,
             last_close: float = None, last_open: float = None,
             last_volume: float = None, high_20d: float = None) -> pd.DataFrame:
    """
    Synthetic OHLCV. All bars identical except optionally the last bar.
    high_20d: if set, sets the first 20 bars' high to this value so the
              rolling 20d-high = high_20d (making pct_from_high calculable).
    """
    closes  = [close] * n
    opens_  = [close * 0.99] * n
    highs   = [close * 1.01] * n
    lows    = [close * 0.98] * n
    volumes = [volume] * n

    if high_20d is not None:
        # First 20 bars have high=high_20d so rolling max = high_20d
        for i in range(min(20, n)):
            highs[i] = high_20d

    if last_close is not None:
        closes[-1] = last_close
    if last_open is not None:
        opens_[-1] = last_open
    if last_volume is not None:
        volumes[-1] = last_volume

    dates = pd.bdate_range("2025-01-02", periods=n)
    return pd.DataFrame({
        "date":   [d.strftime("%Y-%m-%d") for d in dates],
        "open":   opens_,
        "high":   highs,
        "low":    lows,
        "close":  closes,
        "volume": volumes,
    })


def test_normal_context():
    """Flat price and normal volume → 'normal'."""
    from engine.indicators import classify_volume_context
    df = _make_df(25)
    assert classify_volume_context(df) == "normal"


def test_crash_absorption():
    """VR≥2x and close ≥20% below 20d high → 'crash_absorption'."""
    from engine.indicators import classify_volume_context
    # 20d high = 2000, last close = 1500 → pct_from_high = -25%
    # last volume = 5x avg → VR ≈ 4.2x
    df = _make_df(25, close=2000.0, volume=1_000_000.0,
                  last_close=1500.0, last_open=1520.0,
                  last_volume=5_000_000.0, high_20d=2000.0)
    assert classify_volume_context(df) == "crash_absorption"


def test_exhaustion_distribution():
    """VR≥2x + bearish close + near 20d high → 'exhaustion_distribution'."""
    from engine.indicators import classify_volume_context
    # last close = 1960 (within 2% of high 2000), bearish close < open
    # high volume
    df = _make_df(25, close=2000.0, volume=1_000_000.0,
                  last_close=1960.0, last_open=1990.0,   # bearish: close < open
                  last_volume=5_000_000.0, high_20d=2000.0)
    assert classify_volume_context(df) == "exhaustion_distribution"


def test_breakout_accumulation():
    """VR≥1.5x + close near 20d high + above MA20 + bullish → 'breakout_accumulation'."""
    from engine.indicators import classify_volume_context
    # last close = 2010 slightly above high 2000 (0.5% from high, close > open)
    # moderate volume: 2x avg
    df = _make_df(25, close=2000.0, volume=1_000_000.0,
                  last_close=2010.0, last_open=1990.0,   # bullish: close > open
                  last_volume=2_500_000.0, high_20d=2000.0)
    assert classify_volume_context(df) == "breakout_accumulation"


def test_short_df_returns_normal():
    """DataFrame with fewer than 20 bars → 'normal' (insufficient data)."""
    from engine.indicators import classify_volume_context
    df = _make_df(5)
    assert classify_volume_context(df) == "normal"
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && "/home/tjiesar/10 Projects/idx-walkforward-5001/venv/bin/python3" -m pytest tests/test_volume_context.py -v 2>&1 | tail -10
```

Expected: `ImportError: cannot import name 'classify_volume_context'`

- [ ] **Step 3: Implement `classify_volume_context()` at the end of `engine/indicators.py`**

Append after the last line of `engine/indicators.py` (after `IndicatorCache.clear()`):

```python


def classify_volume_context(df: pd.DataFrame) -> str:
    """
    Classify the volume spike context of the last bar.
    Returns one of: 'crash_absorption', 'exhaustion_distribution',
                    'breakout_accumulation', 'normal'.

    Priority:
      crash_absorption:        VR >= 2.0x AND close >= 20% below 20d high
      exhaustion_distribution: VR >= 2.0x AND bearish close AND within 5% of 20d high
      breakout_accumulation:   VR >= 1.5x AND within 5% of 20d high AND above MA20
      normal:                  everything else
    """
    if len(df) < 20:
        return "normal"

    close_s  = df["close"].astype(float)
    high_20d = df["high"].astype(float).rolling(20).max().iloc[-1]
    ma20     = close_s.rolling(20).mean().iloc[-1]
    last     = df.iloc[-1]
    cl       = float(last["close"])
    op       = float(last["open"])
    vr       = calc_vol_ratio(df, 20).iloc[-1]

    if pd.isna(vr) or pd.isna(high_20d) or high_20d <= 0:
        return "normal"

    pct_from_high = (cl - high_20d) / high_20d  # negative = below high

    if vr >= 2.0 and pct_from_high <= -0.20:
        return "crash_absorption"
    if vr >= 2.0 and cl < op and pct_from_high >= -0.05:
        return "exhaustion_distribution"
    if vr >= 1.5 and pct_from_high >= -0.05 and not pd.isna(ma20) and cl > ma20:
        return "breakout_accumulation"
    return "normal"
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && "/home/tjiesar/10 Projects/idx-walkforward-5001/venv/bin/python3" -m pytest tests/test_volume_context.py -v 2>&1 | tail -10
```

Expected: 5 `PASSED`

- [ ] **Step 5: Commit**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && git add engine/indicators.py tests/test_volume_context.py && git commit -m "feat(g4): add classify_volume_context() to engine/indicators.py"
```

---

## Task 2: Surface `vol_context` in Scorers

**Files:**
- Modify: `engine/premover_detector.py` (scorers at lines ~218–229 and ~325–334)
- Modify: `tests/test_volume_context.py` (add 1 integration test)

- [ ] **Step 1: Write failing integration test**

Append to `tests/test_volume_context.py`:

```python
def test_score_ticker_reversal_includes_vol_context():
    """score_ticker_reversal() return dict must have 'vol_context' key."""
    from engine.premover_detector import score_ticker_reversal
    # Need 50+ bars (MIN_BARS in score_ticker_reversal)
    df = _make_df(60, close=2000.0, volume=1_000_000.0)
    result = score_ticker_reversal(df)
    assert "vol_context" in result, (
        f"score_ticker_reversal missing 'vol_context' key. Keys: {list(result.keys())}"
    )
    assert result["vol_context"] in (
        "crash_absorption", "exhaustion_distribution",
        "breakout_accumulation", "normal"
    )
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && "/home/tjiesar/10 Projects/idx-walkforward-5001/venv/bin/python3" -m pytest tests/test_volume_context.py::test_score_ticker_reversal_includes_vol_context -v 2>&1 | tail -8
```

Expected: `AssertionError: score_ticker_reversal missing 'vol_context' key`

- [ ] **Step 3: Add import + `vol_context` to `score_ticker_reversal()`**

In `engine/premover_detector.py`, find the import block at the top. Add:

```python
from engine.indicators import (
    calc_vol_ratio,
    classify_volume_context,
)
```

(Note: check if `calc_vol_ratio` is already imported; if there's an existing import block from `engine.indicators`, just add `classify_volume_context` to it.)

Then find `score_ticker_reversal()` return dict (around line 325). Change:

```python
    return {
        'score':     min(score, 100),
        'reasons':   reasons,
        'vol_ratio': round(vol_ratio, 1) if not pd.isna(vol_ratio) else None,
        'near_low':  near_low,
        'above_3ma': above_3ma,
        'green_day': green_day,
        'atr_ratio': round(atr_ratio, 3) if not pd.isna(atr_ratio) else None,
        'close':     cl_j,
    }
```

to:

```python
    return {
        'score':       min(score, 100),
        'reasons':     reasons,
        'vol_ratio':   round(vol_ratio, 1) if not pd.isna(vol_ratio) else None,
        'near_low':    near_low,
        'above_3ma':   above_3ma,
        'green_day':   green_day,
        'atr_ratio':   round(atr_ratio, 3) if not pd.isna(atr_ratio) else None,
        'close':       cl_j,
        'vol_context': classify_volume_context(df),
    }
```

Then find `score_ticker()` return dict (around line 218). Change:

```python
    return {
        'score':      min(score, 100),
        'reasons':    reasons,
        'above_ma50': above_ma50,
        'adx':        round(adx_j, 1)   if not pd.isna(adx_j)   else None,
        'near_52w':   near_52w,
        'atr_ratio':  round(atr_ratio, 3) if not pd.isna(atr_ratio) else None,
        'vol_dryup':  round(vol_dryup, 3) if not pd.isna(vol_dryup) else None,
```

to include `'vol_context': classify_volume_context(df),` — add it after `'close': ...` (wherever the return dict ends). Read the full return dict to confirm all keys, then add `vol_context` as the last entry.

- [ ] **Step 4: Run integration test + full test file**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && "/home/tjiesar/10 Projects/idx-walkforward-5001/venv/bin/python3" -m pytest tests/test_volume_context.py -v 2>&1 | tail -12
```

Expected: all 6 tests `PASSED`

- [ ] **Step 5: Commit**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && git add engine/premover_detector.py tests/test_volume_context.py && git commit -m "feat(g4): add vol_context to score_ticker_reversal and score_ticker return dicts"
```

---

## Task 3: DB Migration + Upsert + Alert Format + Mark Done

**Files:**
- Modify: `engine/premover_detector.py` (`_init_table`, `_upsert_setup`, alert block)
- Modify: `TODO.md`

- [ ] **Step 1: Add `vol_context` column to `_init_table()` migration block**

In `engine/premover_detector.py`, find `_init_table()` around line 56. The migration block currently ends at line ~70:

```python
    for col, col_def in [
        ('pattern_type', "TEXT NOT NULL DEFAULT 'CONTINUATION'"),
        ('near_low', 'INTEGER'),
        ('above_3ma', 'INTEGER'),
        ('green_day', 'INTEGER'),
        ('vol_ratio', 'REAL'),
    ]:
```

Add `('vol_context', 'TEXT')` to this list:

```python
    for col, col_def in [
        ('pattern_type', "TEXT NOT NULL DEFAULT 'CONTINUATION'"),
        ('near_low', 'INTEGER'),
        ('above_3ma', 'INTEGER'),
        ('green_day', 'INTEGER'),
        ('vol_ratio', 'REAL'),
        ('vol_context', 'TEXT'),
    ]:
```

- [ ] **Step 2: Add `vol_context` to REVERSAL_BREAKOUT INSERT in `_upsert_setup()`**

Find the REVERSAL_BREAKOUT INSERT block (around line 372):

```python
    elif pattern_type == 'REVERSAL_BREAKOUT':
        conn.execute("""
            INSERT OR IGNORE INTO watchlist_premover
            (ticker, detected_at, pattern_type, score, reasons_json,
             near_low, above_3ma, green_day, atr_ratio, vol_ratio, close_price)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (
            ticker, detected_at, pattern_type, result['score'],
            json.dumps(result.get('reasons', [])),
            result.get('near_low'), result.get('above_3ma'),
            result.get('green_day'), result.get('atr_ratio'),
            result.get('vol_ratio'), result.get('close'),
        ))
```

Change to:

```python
    elif pattern_type == 'REVERSAL_BREAKOUT':
        conn.execute("""
            INSERT OR IGNORE INTO watchlist_premover
            (ticker, detected_at, pattern_type, score, reasons_json,
             near_low, above_3ma, green_day, atr_ratio, vol_ratio, close_price,
             vol_context)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            ticker, detected_at, pattern_type, result['score'],
            json.dumps(result.get('reasons', [])),
            result.get('near_low'), result.get('above_3ma'),
            result.get('green_day'), result.get('atr_ratio'),
            result.get('vol_ratio'), result.get('close'),
            result.get('vol_context'),
        ))
```

Also update the CONTINUATION INSERT (around line 358) to include `vol_context`:

```python
    if pattern_type == 'CONTINUATION':
        conn.execute("""
            INSERT OR IGNORE INTO watchlist_premover
            (ticker, detected_at, pattern_type, score, reasons_json,
             above_ma50, adx, near_52w, atr_ratio, vol_dryup, rs, close_price,
             vol_context)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            ticker, detected_at, pattern_type, result['score'],
            json.dumps(result.get('reasons', [])),
            result.get('above_ma50'), result.get('adx'),
            result.get('near_52w'),   result.get('atr_ratio'),
            result.get('vol_dryup'),  result.get('rs'),
            result.get('close'),      result.get('vol_context'),
        ))
```

- [ ] **Step 3: Add `vol_context` tag to Telegram alert (REVERSAL section)**

Find the REVERSAL alert loop (around line 450):

```python
        if reversal:
            msg += f"── REVERSAL_BREAKOUT ({len(reversal)}) ──\n"
            for s in sorted(reversal, key=lambda x: x['score'], reverse=True)[:5]:
                msg += f"<b>{s['ticker']}</b> — Score {s['score']}/100\n"
                msg += f"  {' · '.join(s.get('reasons', []))}\n"
                msg += f"  Close: {s.get('close', 0):,.0f}\n\n"
```

Change to:

```python
        _VOL_CTX_LABELS = {
            'crash_absorption':       'CRASH_ABSORB',
            'exhaustion_distribution': 'EXHAUST_DIST',
            'breakout_accumulation':  'BRK_ACCUM',
        }
        if reversal:
            msg += f"── REVERSAL_BREAKOUT ({len(reversal)}) ──\n"
            for s in sorted(reversal, key=lambda x: x['score'], reverse=True)[:5]:
                ctx = s.get('vol_context', 'normal')
                ctx_tag = f" [{_VOL_CTX_LABELS[ctx]}]" if ctx in _VOL_CTX_LABELS else ''
                msg += f"<b>{s['ticker']}</b> — Score {s['score']}/100{ctx_tag}\n"
                msg += f"  {' · '.join(s.get('reasons', []))}\n"
                msg += f"  Close: {s.get('close', 0):,.0f}\n\n"
```

- [ ] **Step 4: Run full test suite**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && "/home/tjiesar/10 Projects/idx-walkforward-5001/venv/bin/python3" -m pytest tests/ -q --ignore=tests/agent_firm --ignore=tests/test_scheduler_firm_hook.py 2>&1 | tail -5
```

Expected: all tests pass.

- [ ] **Step 5: Verify on BRPT data**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && "/home/tjiesar/10 Projects/idx-walkforward-5001/venv/bin/python3" -c "
import sqlite3, pandas as pd
from engine.premover_detector import score_ticker_reversal

conn = sqlite3.connect('data/walkforward.db')
df = pd.read_sql('SELECT * FROM ohlcv WHERE ticker=\"BRPT\" ORDER BY date ASC', conn)
conn.close()
for c in ['open','high','low','close','volume']:
    df[c] = df[c].astype(float)

result = score_ticker_reversal(df)
print(f'Score: {result[\"score\"]}')
print(f'Vol context: {result[\"vol_context\"]}')
print(f'Reasons: {result[\"reasons\"]}')
"
```

Expected: `vol_context: crash_absorption` (BRPT is >20% below its 20d high after the crash).

- [ ] **Step 6: Mark G4 done in `TODO.md`**

Find:
```
- [ ] **G4. VR spike context classifier**
```

Replace with:
```
- [x] **G4. VR spike context classifier** — SHIPPED 2026-06-05. `classify_volume_context(df)` in `engine/indicators.py`: tags last-bar VR spike as crash_absorption/exhaustion_distribution/breakout_accumulation/normal. Added to `score_ticker_reversal()` + `score_ticker()` return dicts. Stored in `watchlist_premover.vol_context`. REVERSAL_BREAKOUT Telegram alerts show [CRASH_ABSORB]/[BRK_ACCUM]/[EXHAUST_DIST] tags. 6 unit tests.
```

- [ ] **Step 7: Commit everything**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && git add engine/premover_detector.py TODO.md docs/superpowers/plans/2026-06-05-g4-volume-context.md && git commit -m "feat(g4): surface vol_context in DB, upsert, and Telegram alerts — G4 complete"
```

---

## Self-Review

**Spec coverage:**
- ✅ `classify_volume_context()` in `engine/indicators.py` — Task 1
- ✅ 4 classification labels — Task 1 tests (one per label + short-df)
- ✅ `score_ticker_reversal()` `vol_context` key — Task 2
- ✅ `score_ticker()` `vol_context` key — Task 2 Step 3
- ✅ `watchlist_premover` DB migration — Task 3 Step 1
- ✅ `_upsert_setup()` stores vol_context — Task 3 Step 2
- ✅ Telegram alert tag — Task 3 Step 3
- ✅ 6 tests total (5 unit + 1 integration) — Tasks 1 and 2

**Placeholder scan:** None. All steps have complete code.

**Type consistency:**
- `classify_volume_context(df: pd.DataFrame) -> str` — consistent across all usages
- `result.get('vol_context')` — correct; returns None if key missing (SQLite accepts NULL TEXT)
- `_VOL_CTX_LABELS` dict defined inline in alert block — not referenced elsewhere, so no scope issues
