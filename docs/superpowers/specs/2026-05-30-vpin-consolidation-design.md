# R8 — VPIN Consolidation Design

**Date:** 2026-05-30  
**Scope:** Merge `screener/vpin.py` + `screener/vpin_multi.py` → `engine/vpin.py`, surface multi-day VPIN signal in dive.html as a dedicated card.

---

## Problem

VPIN logic lives in `screener/` despite being a pure engine concern (no screener-specific DB tables, no screener routes). Two files — `vpin.py` (294 lines) and `vpin_multi.py` (378 lines) — are tightly coupled: `vpin_multi` imports `classify_vpin` from `vpin`. The scheduler's import is a lazy one-liner deep inside a scan loop. Nothing in dive.html exposes VPIN to the user.

---

## Architecture

### 1. `engine/vpin.py` (new, combined)

Merge both files into a single module. Public surface:

| Symbol | From |
|--------|------|
| `VPIN_THRESHOLDS` | `vpin.py` |
| `classify_vpin(vpin)` | `vpin.py` |
| `calc_vpin(conn, ticker, date, ...)` | `vpin.py` |
| `calc_vpin_series(conn, ticker, date, ...)` | `vpin.py` |
| `calc_vpin_batch(conn, tickers, date, ...)` | `vpin.py` |
| `get_latest_vpin_date(conn, ticker, date)` | `vpin.py` |
| `SIGNAL_MAP` | `vpin_multi.py` |
| `SIGNAL_DESCRIPTIONS` | `vpin_multi.py` |
| `TRADE_PARAMS` | `vpin_multi.py` |
| `calc_vpin_multi(conn, ticker, date, lookback)` | `vpin_multi.py` |
| `scan_vpin_signals(conn, tickers, date, ...)` | `vpin_multi.py` |
| `format_vpin_alert(multi)` | `vpin_multi.py` |

No logic changes — copy verbatim, fix the one internal import (`from screener.vpin import classify_vpin` → no import needed, same file).

### 2. Caller updates

| File | Change |
|------|--------|
| `scheduler.py` line 472 | `from screener.vpin_multi import calc_vpin_multi` → `from engine.vpin import calc_vpin_multi` |
| `screener/vpin.py` | Replace with one-line re-export shim, then delete after confirming no other callers |
| `screener/vpin_multi.py` | Same shim, then delete |

Re-export shim (temporary, one session):
```python
# screener/vpin.py — deprecated, use engine.vpin
from engine.vpin import *  # noqa: F401,F403
```

### 3. `/api/ticker/<ticker>/full` — add `vpin` key

After the premover block, call `calc_vpin_multi` using the existing open connection:

```python
from engine.vpin import calc_vpin_multi
_vpin_conn = sqlite3.connect(DB_PATH)
try:
    vpin_data = calc_vpin_multi(_vpin_conn, ticker, latest['date'])
finally:
    _vpin_conn.close()

vpin_payload = None
if vpin_data:
    vpin_payload = {
        'signal':      vpin_data['signal'],
        'signal_desc': vpin_data['signal_desc'],
        'vpin_today':  vpin_data['vpin_today'],
        'vpin_label':  vpin_data['vpin_label'],
        'vpin_regime': vpin_data['vpin_regime'],
        'vpin_z':      vpin_data['vpin_z'],
        'pressure':    vpin_data['pressure'],
        'delta_dir':   vpin_data['delta_dir'],
        'price_move':  vpin_data['price_move'],
        'lookback_days': vpin_data['lookback_days'],
    }
```

Response shape: `{ ..., "vpin": { ... } | null }`.

`calc_vpin_multi` returns `None` if fewer than 5 days of VPIN data exist in `daily_screen`. Frontend handles `null` gracefully.

### 4. `dive.html` — VPIN card

**Anchor:** New `#sec-vpin` section, placed after `#sec-strategies` and before `#sec-flow` in the drawer nav and page body.

**Card layout (text metrics only):**

```
┌─ VPIN — Informed Flow ──────────────────────────────────────┐
│  Signal: [STRONG_BUY] [badge, color-coded]                  │
│  "Informed buyers loaded, pressure built, release imminent"  │
│                                                              │
│  VPIN Today:  0.6231  HIGH          Z-score:  2.1σ          │
│  Regime:      SPIKE                 Pressure: YES 🔴         │
│  Delta 3D:    BUY                   Price 3D: FLAT           │
│                                                              │
│  Based on 10 days of data                                    │
└──────────────────────────────────────────────────────────────┘
```

If `vpin === null`: show "No VPIN data — need 5+ days of tick history."

**Signal badge colors** (matches existing regime badge pattern):

| Signal | Color |
|--------|-------|
| STRONG_BUY | `#22c55e` (green) |
| BUY | `#86efac` (light green) |
| ACCUMULATION | `#eab308` (yellow) |
| WATCH_LONG / WATCH_SHORT | `#94a3b8` (slate) |
| AVOID / DANGER | `#ef4444` (red) |
| NO_SIGNAL | `#64748b` (muted) |

**Regime badge colors:**

| Regime | Color |
|--------|-------|
| SPIKE | `#f97316` (orange) |
| RISING | `#22c55e` (green) |
| FALLING | `#ef4444` (red) |
| NORMAL | `#94a3b8` (slate) |

Card uses the same `.card`, `.card-title` CSS classes as existing sections. No new CSS classes needed except the signal/regime badge variants.

---

## Data Flow

```
Page load → loadFull() → GET /api/ticker/<ticker>/full
    └─ backend: calc_vpin_multi(conn, ticker, latest_date)
        └─ reads daily_screen WHERE vpin IS NOT NULL
    └─ returns { ..., vpin: { signal, vpin_today, ... } | null }
→ renderVpin(d.vpin) in dive.html
```

No additional network requests. VPIN data is pre-computed by the scheduler's EOD job and stored in `daily_screen.vpin`.

---

## Testing

- `engine/vpin.py` imports cleanly (`from engine.vpin import calc_vpin_multi`)
- Scheduler lazy import resolves without error (can be checked by starting the app)
- `/api/ticker/BBRI/full` response includes `vpin` key (not null for tickers with history)
- dive.html shows card for BBRI, shows "No VPIN data" for a ticker with no tick history
- Existing tests pass (no logic changes, pure move + re-export)

---

## Out of Scope

- Enabling/disabling `filter_vpin` from the UI — the toggle exists in scheduler config and works; no UI change needed
- VPIN time-series chart — deferred, metrics card is sufficient for now
- Deleting `screener/vpin.py` and `screener/vpin_multi.py` before confirming no external callers
