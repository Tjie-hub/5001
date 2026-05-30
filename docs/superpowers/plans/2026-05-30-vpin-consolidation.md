# R8 — VPIN Consolidation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Merge `screener/vpin.py` + `screener/vpin_multi.py` into `engine/vpin.py`, update all callers, add VPIN multi-day signal to `/api/ticker/<ticker>/full`, and render a VPIN card in `dive.html`.

**Architecture:** Pure move + minor call-site updates. No logic changes. `calc_vpin_multi` reads pre-computed VPIN from `daily_screen` (populated by scheduler's existing EOD job). The `/full` endpoint adds a `vpin` key (or `null` if < 5 days of data). `dive.html` renders it as a metrics card below the strategy table.

**Tech Stack:** Python 3.12, Flask, SQLite, vanilla JS, pytest (`venv/bin/pytest`)

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `engine/vpin.py` | All VPIN logic: classify, calc, multi-day, scan, alert |
| Create | `tests/test_vpin_engine.py` | Unit tests for `engine/vpin` |
| Modify | `scheduler.py:472` | Update lazy import path |
| Modify | `screener/vpin.py` | Replace with re-export shim |
| Modify | `screener/vpin_multi.py` | Replace with re-export shim |
| Modify | `app.py:1919–1950` | Add `vpin` key to `/full` response |
| Modify | `templates/dive.html` | Add `#sec-vpin` card, CSS, `renderVpin()` JS |

---

## Task 1: Create `engine/vpin.py` with tests

**Files:**
- Create: `engine/vpin.py`
- Create: `tests/test_vpin_engine.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_vpin_engine.py`:

```python
import sqlite3
import pytest
from engine.vpin import (
    classify_vpin,
    calc_vpin,
    calc_vpin_multi,
    VPIN_THRESHOLDS,
    SIGNAL_MAP,
)


def _make_conn():
    conn = sqlite3.connect(":memory:")
    conn.execute("""
        CREATE TABLE ticks (
            id INTEGER PRIMARY KEY, date TEXT, ticker TEXT,
            time TEXT, price REAL, volume INTEGER, tick_type TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE daily_screen (
            ticker TEXT, date TEXT, vpin REAL, delta INTEGER,
            cum_delta INTEGER, close REAL, volume INTEGER,
            vol_ratio REAL, vwap REAL, signal TEXT
        )
    """)
    return conn


def test_classify_vpin_bands():
    assert classify_vpin(None) == "N/A"
    assert classify_vpin(0.10) == "LOW"
    assert classify_vpin(0.30) == "MODERATE"
    assert classify_vpin(0.50) == "HIGH"
    assert classify_vpin(0.70) == "TOXIC"


def test_vpin_thresholds_present():
    assert "low" in VPIN_THRESHOLDS
    assert "moderate" in VPIN_THRESHOLDS
    assert "high" in VPIN_THRESHOLDS


def test_calc_vpin_no_ticks_returns_error():
    conn = _make_conn()
    result = calc_vpin(conn, "BBCA", "2026-05-30")
    assert result["vpin"] is None
    assert result["error"] is not None
    conn.close()


def test_calc_vpin_multi_no_rows_returns_none():
    conn = _make_conn()
    result = calc_vpin_multi(conn, "BBCA", "2026-05-30")
    assert result is None
    conn.close()


def test_calc_vpin_multi_insufficient_rows_returns_none():
    conn = _make_conn()
    for i in range(4):
        conn.execute(
            "INSERT INTO daily_screen VALUES (?,?,?,?,?,?,?,?,?,?)",
            ("BBCA", f"2026-05-{i+1:02d}", 0.3 + i * 0.01, 100, 100,
             5000.0, 1000000, 1.2, 4900.0, "BUY"),
        )
    result = calc_vpin_multi(conn, "BBCA", "2026-05-04")
    assert result is None
    conn.close()


def test_calc_vpin_multi_returns_dict_with_5_rows():
    conn = _make_conn()
    for i in range(7):
        conn.execute(
            "INSERT INTO daily_screen VALUES (?,?,?,?,?,?,?,?,?,?)",
            ("BBCA", f"2026-05-{i+1:02d}", 0.25 + i * 0.02, 100, 100,
             5000.0, 1000000, 1.3, 4900.0, "BUY"),
        )
    result = calc_vpin_multi(conn, "BBCA", "2026-05-07")
    assert result is not None
    assert "signal" in result
    assert "vpin_today" in result
    assert "vpin_regime" in result
    assert "vpin_z" in result
    assert "pressure" in result
    assert "delta_dir" in result
    assert "price_move" in result
    conn.close()


def test_signal_map_keys_are_tuples():
    for key in SIGNAL_MAP:
        assert isinstance(key, tuple)
        assert len(key) == 3
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001"
venv/bin/pytest tests/test_vpin_engine.py -v
```

Expected: `ModuleNotFoundError: No module named 'engine.vpin'`

- [ ] **Step 3: Create `engine/vpin.py`**

Content is the verbatim merge of `screener/vpin.py` (all functions) followed by `screener/vpin_multi.py` (all functions), with the one internal cross-file import removed. Create `engine/vpin.py`:

```python
"""
engine/vpin.py — Volume-Synchronized Probability of Informed Trading
=====================================================================
Consolidated from screener/vpin.py + screener/vpin_multi.py.

Provides:
  calc_vpin          — single-day VPIN from tick data
  calc_vpin_series   — intraday rolling VPIN for charting
  calc_vpin_batch    — EOD batch across all tickers
  classify_vpin      — score → LOW/MODERATE/HIGH/TOXIC label
  calc_vpin_multi    — multi-day VPIN strategy signal
  scan_vpin_signals  — scan all tickers for actionable signals
  format_vpin_alert  — Telegram message formatter
"""

import sqlite3
import logging
from typing import Optional

logger = logging.getLogger(__name__)


# ── Thresholds ────────────────────────────────────────────────────────────────

VPIN_THRESHOLDS = {
    'low':      0.20,
    'moderate': 0.40,
    'high':     0.60,
}


def classify_vpin(vpin: float) -> str:
    """Return human-readable VPIN label."""
    if vpin is None:
        return 'N/A'
    if vpin < VPIN_THRESHOLDS['low']:
        return 'LOW'
    elif vpin < VPIN_THRESHOLDS['moderate']:
        return 'MODERATE'
    elif vpin < VPIN_THRESHOLDS['high']:
        return 'HIGH'
    else:
        return 'TOXIC'


# ── Core VPIN Calculation ─────────────────────────────────────────────────────

def calc_vpin(
    conn: sqlite3.Connection,
    ticker: str,
    date: str,
    n_buckets: int = 50,
    bucket_size: Optional[int] = None,
    avg_vol_lookback: int = 30,
    min_buckets: int = 5,
) -> dict:
    """
    Calculate VPIN for a single ticker on a single date.
    Returns dict with keys: vpin, vpin_label, bucket_count, bucket_size,
    buckets, total_volume, error.
    """
    result_base = {
        'ticker': ticker, 'date': date,
        'vpin': None, 'vpin_label': 'N/A',
        'bucket_count': 0, 'bucket_size': None,
        'buckets': [], 'total_volume': 0, 'error': None,
    }

    if bucket_size is None:
        row = conn.execute("""
            SELECT AVG(volume) as avg_vol
            FROM daily_screen
            WHERE ticker = ?
              AND date >= date(?, '-' || ? || ' days')
              AND date < ?
              AND volume > 0
        """, (ticker, date, str(avg_vol_lookback), date)).fetchone()
        avg_vol = row[0] if row and row[0] else None
        if avg_vol is None or avg_vol < 1000:
            result_base['error'] = 'insufficient volume history'
            return result_base
        bucket_size = max(int(avg_vol / n_buckets), 1)

    result_base['bucket_size'] = bucket_size

    ticks = conn.execute("""
        SELECT price, volume, tick_type
        FROM ticks
        WHERE date = ? AND ticker = ?
        ORDER BY time ASC, id ASC
    """, (date, ticker)).fetchall()

    if not ticks or len(ticks) < 10:
        result_base['error'] = f'insufficient ticks ({len(ticks) if ticks else 0})'
        return result_base

    buckets = []
    cur_buy = 0
    cur_sell = 0
    cur_vol = 0
    total_vol = 0

    for row in ticks:
        price = row[0]
        vol = row[1]
        ttype = row[2]
        if vol is None or vol <= 0:
            continue
        total_vol += vol
        if ttype == 'up':
            cur_buy += vol
        elif ttype == 'down':
            cur_sell += vol
        else:
            half = vol // 2
            cur_buy += half
            cur_sell += vol - half
        cur_vol += vol

        while cur_vol >= bucket_size:
            if cur_vol > 0:
                fill_ratio = bucket_size / cur_vol
                b_buy = int(cur_buy * fill_ratio)
                b_sell = bucket_size - b_buy
            else:
                b_buy = b_sell = 0
            imbalance = abs(b_buy - b_sell) / bucket_size
            buckets.append({
                'bucket_id': len(buckets) + 1,
                'v_buy': b_buy, 'v_sell': b_sell,
                'imbalance': round(imbalance, 4),
                'direction': 'BUY' if b_buy > b_sell else 'SELL',
            })
            overflow_buy = cur_buy - b_buy
            overflow_sell = cur_sell - b_sell
            overflow_vol = cur_vol - bucket_size
            cur_buy = max(overflow_buy, 0)
            cur_sell = max(overflow_sell, 0)
            cur_vol = max(overflow_vol, 0)

    result_base['total_volume'] = total_vol
    result_base['bucket_count'] = len(buckets)

    if len(buckets) < min_buckets:
        result_base['error'] = f'insufficient buckets ({len(buckets)}/{min_buckets})'
        result_base['buckets'] = buckets
        return result_base

    window = buckets[-n_buckets:]
    vpin = sum(b['imbalance'] for b in window) / len(window)
    result_base['vpin'] = round(vpin, 4)
    result_base['vpin_label'] = classify_vpin(vpin)
    result_base['buckets'] = buckets
    return result_base


def calc_vpin_series(
    conn: sqlite3.Connection,
    ticker: str,
    date: str,
    n_buckets: int = 50,
    bucket_size: Optional[int] = None,
    rolling_window: int = 20,
) -> dict:
    """Rolling VPIN over the trading day for charting."""
    full = calc_vpin(conn, ticker, date, n_buckets, bucket_size)
    if full['vpin'] is None:
        return {'series': [], 'vpin': None, 'label': 'N/A', 'error': full.get('error')}
    buckets = full['buckets']
    series = []
    for i in range(rolling_window - 1, len(buckets)):
        window = buckets[max(0, i - rolling_window + 1):i + 1]
        rolling_vpin = sum(b['imbalance'] for b in window) / len(window)
        series.append([i + 1, round(rolling_vpin, 4)])
    return {
        'series': series, 'vpin': full['vpin'], 'label': full['vpin_label'],
        'bucket_count': full['bucket_count'], 'bucket_size': full['bucket_size'],
    }


def calc_vpin_batch(
    conn: sqlite3.Connection,
    tickers: list,
    date: str,
    n_buckets: int = 50,
) -> dict:
    """Calculate VPIN for all tickers. Used by scheduler at EOD."""
    results = {}
    for ticker in tickers:
        try:
            r = calc_vpin(conn, ticker, date, n_buckets)
            results[ticker] = r
        except Exception as e:
            logger.error(f"[vpin] Error calculating {ticker}: {e}")
            results[ticker] = {'vpin': None, 'vpin_label': 'N/A', 'error': str(e)}
    return results


def get_latest_vpin_date(conn, ticker, date):
    """Find the most recent date with VPIN data, on or before given date."""
    row = conn.execute("""
        SELECT date FROM daily_screen
        WHERE ticker = ? AND date <= ? AND vpin IS NOT NULL
        ORDER BY date DESC LIMIT 1
    """, (ticker, date)).fetchone()
    return row[0] if row else None


# ── Multi-Day VPIN Strategy ───────────────────────────────────────────────────

SIGNAL_MAP = {
    ('SPIKE',  'BUY',  'FLAT'):  'STRONG_BUY',
    ('SPIKE',  'BUY',  'UP'):    'WATCH_LONG',
    ('SPIKE',  'BUY',  'DOWN'):  'ACCUMULATION',
    ('SPIKE',  'SELL', 'FLAT'):  'AVOID',
    ('SPIKE',  'SELL', 'UP'):    'DANGER',
    ('SPIKE',  'SELL', 'DOWN'):  'WATCH_SHORT',
    ('RISING', 'BUY',  'FLAT'):  'BUY',
    ('RISING', 'BUY',  'UP'):    'WATCH_LONG',
    ('RISING', 'BUY',  'DOWN'):  'ACCUMULATION',
    ('RISING', 'SELL', 'FLAT'):  'AVOID',
    ('RISING', 'SELL', 'UP'):    'DANGER',
    ('RISING', 'SELL', 'DOWN'):  'WATCH_SHORT',
}

SIGNAL_DESCRIPTIONS = {
    'STRONG_BUY':   'Informed buyers loaded, pressure built, release imminent',
    'BUY':          'Informed buying building, direction confirmed',
    'ACCUMULATION': 'Smart money accumulating on dip — watch for reversal',
    'WATCH_LONG':   'Move already started — late entry risk, trail if in',
    'WATCH_SHORT':  'Informed selling into weakness — could accelerate',
    'AVOID':        'Informed sellers loading — drop coming',
    'DANGER':       'Distribution — smart money selling into rally',
    'NO_SIGNAL':    'No significant informed activity detected',
}

TRADE_PARAMS = {
    'STRONG_BUY': {'action': 'BUY', 'tp_pct': 2.5, 'sl_pct': 1.5, 'time_stop_days': 5, 'max_position_pct': 30, 'confidence': 'HIGH'},
    'BUY':        {'action': 'BUY', 'tp_pct': 2.0, 'sl_pct': 1.5, 'time_stop_days': 5, 'max_position_pct': 30, 'confidence': 'MEDIUM'},
    'ACCUMULATION': {'action': 'BUY', 'tp_pct': 2.5, 'sl_pct': 2.0, 'time_stop_days': 7, 'max_position_pct': 20, 'confidence': 'MEDIUM'},
}


def calc_vpin_multi(
    conn: sqlite3.Connection,
    ticker: str,
    date: str,
    lookback: int = 10,
) -> Optional[dict]:
    """
    Multi-day VPIN signal. Returns None if < 5 days of VPIN data.
    Reads daily_screen.vpin (pre-computed by scheduler EOD job).
    """
    rows = conn.execute("""
        SELECT date, vpin, delta, cum_delta, close, volume, vol_ratio, vwap, signal
        FROM daily_screen
        WHERE ticker = ? AND date <= ? AND vpin IS NOT NULL
        ORDER BY date DESC LIMIT ?
    """, (ticker, date, lookback)).fetchall()

    if len(rows) < 5:
        return None

    rows = list(reversed(rows))
    dates   = [r[0] for r in rows]
    vpins   = [r[1] for r in rows]
    deltas  = [r[2] or 0 for r in rows]
    closes  = [r[4] for r in rows]
    vols_r  = [r[6] for r in rows]

    today_row = rows[-1]
    today_vpin = today_row[1]
    yesterday_vpin = rows[-2][1] if len(rows) >= 2 else None

    v3 = vpins[-3:]
    vpin_3d_avg = sum(v3) / len(v3)
    vpin_3d_slope = (v3[-1] - v3[0]) / 2 if len(v3) >= 3 else 0

    n = len(vpins)
    mean_vpin = sum(vpins) / n
    variance = sum((v - mean_vpin) ** 2 for v in vpins) / n
    std_vpin = variance ** 0.5
    vpin_z = (today_vpin - mean_vpin) / std_vpin if std_vpin > 0.001 else 0.0

    if vpin_z >= 2.0:
        vpin_regime = 'SPIKE'
    elif vpin_3d_slope > 0.03:
        vpin_regime = 'RISING'
    elif vpin_3d_slope < -0.03:
        vpin_regime = 'FALLING'
    else:
        vpin_regime = 'NORMAL'

    delta_3d = sum(deltas[-3:])
    delta_dir = 'BUY' if delta_3d > 0 else 'SELL'

    price_start = closes[-3] if len(closes) >= 3 else closes[0]
    price_end = closes[-1]
    price_chg_3d = (price_end - price_start) / price_start if price_start and price_start > 0 else 0.0
    if abs(price_chg_3d) < 0.015:
        price_move = 'FLAT'
    elif price_chg_3d > 0:
        price_move = 'UP'
    else:
        price_move = 'DOWN'

    pressure = vpin_regime in ('RISING', 'SPIKE') and price_move == 'FLAT'

    signal_key = (vpin_regime, delta_dir, price_move)
    signal = SIGNAL_MAP.get(signal_key, 'NO_SIGNAL')

    today_vol_ratio = vols_r[-1]
    if signal in ('STRONG_BUY', 'BUY', 'ACCUMULATION'):
        if today_vol_ratio is not None and today_vol_ratio < 1.0:
            signal = 'NO_SIGNAL'

    vpin_collapse = False
    if len(vpins) >= 3:
        v_2d_ago = vpins[-3]
        if std_vpin > 0.001:
            z_2d_ago = (v_2d_ago - mean_vpin) / std_vpin
            if z_2d_ago >= 1.5 and vpin_z < 0.5:
                vpin_collapse = True

    trade_params = TRADE_PARAMS.get(signal)
    if trade_params and vpin_z > 2.5:
        trade_params = dict(trade_params)
        trade_params['max_position_pct'] = 20
        trade_params['note'] = 'Reduced position: extreme VPIN'

    days_data = [
        {'date': r[0], 'vpin': r[1], 'delta': r[2], 'close': r[4],
         'volume': r[5], 'vol_ratio': r[6]}
        for r in rows
    ]

    return {
        'ticker': ticker, 'date': date,
        'vpin_today': round(today_vpin, 4),
        'vpin_yesterday': round(yesterday_vpin, 4) if yesterday_vpin else None,
        'vpin_3d_avg': round(vpin_3d_avg, 4),
        'vpin_3d_slope': round(vpin_3d_slope, 4),
        'vpin_z': round(vpin_z, 2),
        'vpin_regime': vpin_regime,
        'vpin_label': classify_vpin(today_vpin),
        'delta_3d': delta_3d,
        'delta_dir': delta_dir,
        'price_chg_3d': round(price_chg_3d, 4),
        'price_move': price_move,
        'pressure': pressure,
        'vpin_collapse': vpin_collapse,
        'signal': signal,
        'signal_desc': SIGNAL_DESCRIPTIONS.get(signal, ''),
        'trade_params': trade_params,
        'lookback_days': len(rows),
        'days_data': days_data,
    }


def scan_vpin_signals(
    conn: sqlite3.Connection,
    tickers: list,
    date: str,
    min_signal_level: str = 'BUY',
) -> list:
    """Scan all tickers for multi-day VPIN signals, sorted by strength."""
    actionable = ('STRONG_BUY', 'BUY', 'ACCUMULATION', 'DANGER', 'AVOID')
    if min_signal_level == 'ALL':
        actionable = tuple(SIGNAL_MAP.values())

    results = []
    for ticker in tickers:
        try:
            multi = calc_vpin_multi(conn, ticker, date)
            if multi and multi['signal'] in actionable:
                results.append(multi)
        except Exception as e:
            logger.error(f"[vpin] Error scanning {ticker}: {e}")

    signal_priority = {
        'STRONG_BUY': 0, 'BUY': 1, 'ACCUMULATION': 2,
        'DANGER': 3, 'AVOID': 4,
        'WATCH_LONG': 5, 'WATCH_SHORT': 6, 'NO_SIGNAL': 9,
    }
    results.sort(key=lambda x: (signal_priority.get(x['signal'], 9), -abs(x['vpin_z'])))
    return results


def format_vpin_alert(multi: dict) -> str:
    """Format a multi-day VPIN result into a Telegram message."""
    emoji = {
        'STRONG_BUY': '🔥🔥', 'BUY': '🔥', 'ACCUMULATION': '🟡',
        'DANGER': '🔴', 'AVOID': '⛔', 'WATCH_LONG': '👀', 'WATCH_SHORT': '👀',
    }
    regime_emoji = {'SPIKE': '⚡', 'RISING': '📈', 'FALLING': '📉', 'NORMAL': '➖'}

    sig = multi['signal']
    e = emoji.get(sig, '📊')
    re = regime_emoji.get(multi['vpin_regime'], '')

    lines = [
        f"{e} VPIN ALERT: {multi['ticker']}",
        f"",
        f"Signal: {sig}",
        f"  → {multi['signal_desc']}",
        f"",
        f"VPIN: {multi['vpin_today']:.4f} ({multi['vpin_label']})",
        f"Regime: {re} {multi['vpin_regime']}",
        f"Z-score: {multi['vpin_z']:.1f}σ",
        f"3D slope: {multi['vpin_3d_slope']:+.4f}",
        f"",
        f"Delta 3D: {multi['delta_dir']} ({multi['delta_3d']:+,})",
        f"Price 3D: {multi['price_move']} ({multi['price_chg_3d']:+.2%})",
        f"Pressure: {'YES 🔴' if multi['pressure'] else 'NO'}",
    ]
    if multi.get('trade_params'):
        tp = multi['trade_params']
        lines.extend([
            f"", f"── Trade Plan ──",
            f"TP: {tp['tp_pct']}% | SL: {tp['sl_pct']}%",
            f"Time stop: {tp['time_stop_days']}d",
            f"Max pos: {tp['max_position_pct']}%",
        ])
        if tp.get('note'):
            lines.append(f"⚠️ {tp['note']}")
    if multi.get('vpin_collapse'):
        lines.extend([f"", f"⚠️ VPIN COLLAPSE detected — trail SL to breakeven"])

    return '\n'.join(lines)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001"
venv/bin/pytest tests/test_vpin_engine.py -v
```

Expected: 7 tests PASS

- [ ] **Step 5: Commit**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001"
git add engine/vpin.py tests/test_vpin_engine.py
git commit -m "feat(r8): add engine/vpin.py — merged vpin + vpin_multi with tests"
```

---

## Task 2: Update `scheduler.py` import

**Files:**
- Modify: `scheduler.py:472`

- [ ] **Step 1: Update the lazy import**

In `scheduler.py`, find this line (around line 472):
```python
from screener.vpin_multi import calc_vpin_multi as _calc_vpin_multi
```
Replace with:
```python
from engine.vpin import calc_vpin_multi as _calc_vpin_multi
```

- [ ] **Step 2: Verify the import resolves**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001"
venv/bin/python3 -c "from engine.vpin import calc_vpin_multi; print('OK')"
```

Expected output: `OK`

- [ ] **Step 3: Run full test suite**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001"
venv/bin/pytest tests/ -q
```

Expected: all tests pass (same count as before this task)

- [ ] **Step 4: Commit**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001"
git add scheduler.py
git commit -m "fix(r8): update scheduler lazy import to engine.vpin"
```

---

## Task 3: Add backward-compat shims to `screener/vpin.py` and `screener/vpin_multi.py`

**Files:**
- Modify: `screener/vpin.py`
- Modify: `screener/vpin_multi.py`

These shims let any external script that imports from `screener.vpin` keep working without changes. They are transitional — delete both files once no external callers remain.

- [ ] **Step 1: Replace `screener/vpin.py` with shim**

Replace the entire contents of `screener/vpin.py` with:

```python
# Deprecated: use engine.vpin
from engine.vpin import *  # noqa: F401,F403
```

- [ ] **Step 2: Replace `screener/vpin_multi.py` with shim**

Replace the entire contents of `screener/vpin_multi.py` with:

```python
# Deprecated: use engine.vpin
from engine.vpin import *  # noqa: F401,F403
```

- [ ] **Step 3: Verify old import paths still work**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001"
venv/bin/python3 -c "
from screener.vpin import classify_vpin, calc_vpin
from screener.vpin_multi import calc_vpin_multi, scan_vpin_signals
print('shims OK')
"
```

Expected output: `shims OK`

- [ ] **Step 4: Commit**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001"
git add screener/vpin.py screener/vpin_multi.py
git commit -m "feat(r8): replace screener/vpin*.py with re-export shims"
```

---

## Task 4: Add `vpin` key to `/api/ticker/<ticker>/full`

**Files:**
- Modify: `app.py:1919–1950`

- [ ] **Step 1: Insert VPIN call before the `return jsonify` block**

In `app.py`, find the block starting at the line with `_ohlcv = df[...]` (just before `return jsonify`). Insert the following block **before** `_ohlcv = df[...]`:

```python
    # ── VPIN multi-day signal ──────────────────────────────────────────────
    from engine.vpin import calc_vpin_multi as _calc_vpin_multi_full
    _vpin_conn = _sq3.connect(DB_PATH)
    try:
        _vpin_raw = _calc_vpin_multi_full(_vpin_conn, ticker, str(latest['date'])[:10])
    except Exception:
        _vpin_raw = None
    finally:
        _vpin_conn.close()
    _vpin = None
    if _vpin_raw:
        _vpin = {
            'signal':        _vpin_raw['signal'],
            'signal_desc':   _vpin_raw['signal_desc'],
            'vpin_today':    _vpin_raw['vpin_today'],
            'vpin_label':    _vpin_raw['vpin_label'],
            'vpin_regime':   _vpin_raw['vpin_regime'],
            'vpin_z':        _vpin_raw['vpin_z'],
            'pressure':      _vpin_raw['pressure'],
            'delta_dir':     _vpin_raw['delta_dir'],
            'price_move':    _vpin_raw['price_move'],
            'lookback_days': _vpin_raw['lookback_days'],
        }
```

- [ ] **Step 2: Add `vpin` to the `return jsonify(...)` dict**

In the `return jsonify({...})` block, add `'vpin': _vpin,` after `'premover_reversal': {...},`:

```python
    return jsonify({
        'ticker':             ticker,
        'price':              price,
        'ohlcv':              _ohlcv.to_dict('records'),
        'regime':             regime,
        'strategies':         strategies,
        'flow':               {'latest': flow_latest, 'cum_delta_20d': cum_delta_20d},
        'broker':             top_brokers,
        'premover':           { ... },       # existing, unchanged
        'premover_reversal':  { ... },       # existing, unchanged
        'vpin':               _vpin,         # NEW — None if < 5 days data
    })
```

- [ ] **Step 3: Verify endpoint response includes `vpin` key**

```bash
curl -s http://localhost:5001/api/ticker/BBRI/full | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('vpin key present:', 'vpin' in d)
print('vpin value:', d.get('vpin'))
"
```

Expected: `vpin key present: True` and either a dict with `signal`, `vpin_today`, etc. or `None`.

- [ ] **Step 4: Run full test suite**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001"
venv/bin/pytest tests/ -q
```

Expected: all tests pass

- [ ] **Step 5: Commit**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001"
git add app.py
git commit -m "feat(r8): add vpin key to /api/ticker/<ticker>/full response"
```

---

## Task 5: Add VPIN card to `dive.html`

**Files:**
- Modify: `templates/dive.html`

Three sub-changes: CSS, HTML, JS.

- [ ] **Step 1: Add CSS for VPIN signal and regime badges**

In `dive.html`, find the `<style>` block. After the last existing badge or `.regime` CSS rule (search for `.regime-badge` or similar), insert:

```css
/* ── VPIN card ───────────────────────────────────────── */
.vpin-signal-badge {
  display: inline-block; padding: 3px 10px; border-radius: 5px;
  font-size: 12px; font-weight: 700; letter-spacing: .04em;
  margin-bottom: 6px;
}
.vpin-sig-STRONG_BUY  { background: rgba(34,197,94,.18);  color: #22c55e; }
.vpin-sig-BUY         { background: rgba(134,239,172,.15); color: #86efac; }
.vpin-sig-ACCUMULATION{ background: rgba(234,179,8,.15);   color: #eab308; }
.vpin-sig-AVOID       { background: rgba(239,68,68,.18);   color: #ef4444; }
.vpin-sig-DANGER      { background: rgba(239,68,68,.18);   color: #ef4444; }
.vpin-sig-WATCH_LONG,
.vpin-sig-WATCH_SHORT { background: rgba(148,163,184,.12); color: #94a3b8; }
.vpin-sig-NO_SIGNAL   { background: rgba(100,116,139,.10); color: #64748b; }

.vpin-regime-badge {
  display: inline-block; padding: 2px 8px; border-radius: 4px;
  font-size: 11px; font-weight: 600; letter-spacing: .03em;
}
.vpin-reg-SPIKE   { background: rgba(249,115,22,.18); color: #f97316; }
.vpin-reg-RISING  { background: rgba(34,197,94,.15);  color: #22c55e; }
.vpin-reg-FALLING { background: rgba(239,68,68,.15);  color: #ef4444; }
.vpin-reg-NORMAL  { background: rgba(148,163,184,.12);color: #94a3b8; }

.vpin-grid {
  display: grid; grid-template-columns: 1fr 1fr;
  gap: 6px 16px; margin-top: 8px; font-size: 12px;
}
.vpin-grid-label { color: var(--mute); }
.vpin-grid-value { color: var(--text); font-weight: 600; font-family: var(--mono); }
.vpin-desc { font-size: 11px; color: var(--mute); margin-bottom: 8px; }
.vpin-pressure-yes { color: #ef4444; font-weight: 700; }
```

- [ ] **Step 2: Add drawer nav link**

In `dive.html`, find:
```html
<a class="drawer-link" href="#sec-strategies" onclick="toggleDrawer()">Strategy Signals</a>
```

Add the VPIN link after it:
```html
<a class="drawer-link" href="#sec-vpin"       onclick="toggleDrawer()">VPIN Flow</a>
```

- [ ] **Step 3: Add VPIN HTML section**

In `dive.html`, find the closing `</div>` that ends the `#sec-strategies` wrapper `<div>` (the anonymous `<div>` containing `#sec-strategies`). It looks like:

```html
    </div>
  </div>

  <div class="side">
```

Insert the VPIN section between those two divs:

```html
    </div>

    <div class="section" id="sec-vpin">
      <div class="sec-title">VPIN — Informed Flow</div>
      <div id="vpin-loading" class="loading-msg">Loading…</div>
      <div id="vpin-content" style="display:none">
        <div id="vpin-signal-badge" class="vpin-signal-badge">—</div>
        <div id="vpin-desc" class="vpin-desc">—</div>
        <div class="vpin-grid">
          <span class="vpin-grid-label">VPIN Today</span>
          <span class="vpin-grid-value" id="vpin-today">—</span>
          <span class="vpin-grid-label">Label</span>
          <span class="vpin-grid-value" id="vpin-label">—</span>
          <span class="vpin-grid-label">Regime</span>
          <span class="vpin-grid-value" id="vpin-regime">—</span>
          <span class="vpin-grid-label">Z-score</span>
          <span class="vpin-grid-value" id="vpin-z">—</span>
          <span class="vpin-grid-label">Pressure</span>
          <span class="vpin-grid-value" id="vpin-pressure">—</span>
          <span class="vpin-grid-label">Delta 3D</span>
          <span class="vpin-grid-value" id="vpin-delta">—</span>
          <span class="vpin-grid-label">Price 3D</span>
          <span class="vpin-grid-value" id="vpin-price">—</span>
          <span class="vpin-grid-label">Based on</span>
          <span class="vpin-grid-value" id="vpin-days">—</span>
        </div>
      </div>
    </div>
  </div>

  <div class="side">
```

- [ ] **Step 4: Add `renderVpin()` JavaScript function**

In `dive.html`, find the `loadFull()` function. After the line `renderStrategies(d.strategies, d.price.close);` (inside `loadFull`), add:

```javascript
    renderVpin(d.vpin);
```

Then add the `renderVpin` function definition **before** `loadFull` (or anywhere in the script block before it's called):

```javascript
  function renderVpin(vpin) {
    const loading = document.getElementById('vpin-loading');
    const content = document.getElementById('vpin-content');
    if (!vpin) {
      if (loading) loading.textContent = 'No VPIN data — need 5+ days of tick history.';
      return;
    }
    if (loading) loading.style.display = 'none';
    if (content) content.style.display = 'block';

    const badge = document.getElementById('vpin-signal-badge');
    badge.textContent = vpin.signal;
    badge.className = 'vpin-signal-badge vpin-sig-' + vpin.signal;

    document.getElementById('vpin-desc').textContent = vpin.signal_desc || '';

    const regEl = document.getElementById('vpin-regime');
    regEl.innerHTML = `<span class="vpin-regime-badge vpin-reg-${vpin.vpin_regime}">${vpin.vpin_regime}</span>`;

    document.getElementById('vpin-today').textContent =
      vpin.vpin_today != null ? vpin.vpin_today.toFixed(4) : '—';
    document.getElementById('vpin-label').textContent = vpin.vpin_label || '—';
    document.getElementById('vpin-z').textContent =
      vpin.vpin_z != null ? vpin.vpin_z.toFixed(1) + 'σ' : '—';

    const pressEl = document.getElementById('vpin-pressure');
    pressEl.innerHTML = vpin.pressure
      ? '<span class="vpin-pressure-yes">YES 🔴</span>'
      : 'NO';

    document.getElementById('vpin-delta').textContent = vpin.delta_dir || '—';
    document.getElementById('vpin-price').textContent = vpin.price_move || '—';
    document.getElementById('vpin-days').textContent =
      vpin.lookback_days ? vpin.lookback_days + ' days' : '—';
  }
```

- [ ] **Step 5: Verify in browser**

```bash
curl -s http://localhost:5001/dive/BBRI | grep -c "sec-vpin"
```

Expected: `1` (the section exists in the HTML)

Then open `http://localhost:5001/dive/BBRI` in a browser. Verify:
- VPIN card appears below the strategy table
- If BBRI has 5+ days of tick data in `daily_screen.vpin`, the card shows signal badge, metrics
- If no data, shows "No VPIN data — need 5+ days of tick history."
- Drawer nav has "VPIN Flow" link that scrolls to the card

- [ ] **Step 6: Run full test suite**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001"
venv/bin/pytest tests/ -q
```

Expected: all tests pass

- [ ] **Step 7: Update TODO.md — mark R8 done**

In `TODO.md`, find:
```
- [ ] **R8. Standardize VPIN**
```
Replace with:
```
- [x] **R8. Standardize VPIN** — Merged screener/vpin.py + screener/vpin_multi.py → engine/vpin.py. Shims left for backward compat. vpin key added to /api/ticker/<ticker>/full. VPIN card added to dive.html. SHIPPED 2026-05-30.
```

- [ ] **Step 8: Commit**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001"
git add templates/dive.html TODO.md
git commit -m "feat(r8): add VPIN card to dive.html; mark R8 complete"
```
