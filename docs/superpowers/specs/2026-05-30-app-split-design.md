# R5b — app.py Split Design

**Date:** 2026-05-30  
**Scope:** Convert `app.py` (2185 lines, 44 direct routes) into Flask Blueprints across 5 focused route files. Zero logic changes — pure structural refactor.

---

## Problem

`app.py` has grown to 2185 lines covering six distinct domains: backtest/signal scanning, paper trading, flow data, Telegram integration, ticker detail, and app setup. All route handlers live in one file alongside module-level state, making navigation and maintenance difficult.

Two Blueprints already exist (`backtest_multi_bp`, `screener_bp`). This refactor extracts the remaining 44 routes into the same pattern.

---

## Architecture

### New files

```
routes/
  __init__.py       — empty package marker
  backtest.py       — backtest_bp
  paper.py          — paper_bp
  flow.py           — flow_bp
  telegram.py       — telegram_bp
  ticker.py         — ticker_bp
```

### Route assignments

**`routes/backtest.py` — `backtest_bp`** (no URL prefix)

| Route | Method | app.py line |
|-------|--------|-------------|
| `/api/backtest/scan_all` | POST | 128 |
| `/api/backtest/quick_scan` | POST | 274 |
| `/signal-scanner` | GET | 425 |
| `/api/backtest/precompute` | POST | 453 |
| `/api/backtest/multi_quick_scan` | POST | 535 |
| `/api/signals/today` | GET | 803 |
| `/api/signals/scheduled` | GET | 809 |
| `/api/agent/status` | GET | 840 |
| `/api/agent/config` | POST | 874 |
| `/api/agent/audit` | GET | 892 |
| `/api/scheduler/run` | POST | 912 |

**`routes/paper.py` — `paper_bp`** (no URL prefix)

| Route | Method | app.py line |
|-------|--------|-------------|
| `/api/paper/config` | GET | 509 |
| `/api/paper/config` | POST | 517 |
| `/api/paper/open` | POST | 995 |
| `/api/paper/close` | POST | 1009 |
| `/api/paper/clear_history` | POST | 1021 |
| `/api/paper/summary` | GET | 1027 |
| `/api/paper/report-telegram` | POST | 1034 |

**`routes/flow.py` — `flow_bp`** (no URL prefix)

| Route | Method | app.py line |
|-------|--------|-------------|
| `/api/flow/monitor` | GET | 1046 |
| `/api/signals/custom` | POST | 1081 |
| `/api/flow/check` | POST | 1243 |
| `/api/broker-flow/<ticker>` | GET | 1301 |
| `/api/broker-flow/dates/<ticker>` | GET | 1364 |

**`routes/telegram.py` — `telegram_bp`** (no URL prefix)

| Route | Method | app.py line |
|-------|--------|-------------|
| `/telegram/updates` | POST | 1494 |
| `/telegram/setup` | GET | 1517 |
| `/telegram/start-polling` | GET | 1602 |
| `/telegram/stop-polling` | GET | 1616 |
| `/telegram/poll-updates` | GET | 1628 |
| `/telegram/status` | GET | 1685 |

Module-level state that moves here:
- `telegram_polling_active: bool = False` (app.py line 1554)
- `telegram_last_update_id: int = 0` (app.py line 1555)

**`routes/ticker.py` — `ticker_bp`** (no URL prefix)

| Route | Method | app.py line |
|-------|--------|-------------|
| `/dive/<ticker>` | GET | 1763 |
| `/api/ticker/<ticker>/full` | GET | 1792 |
| `/api/ticker/<ticker>/broker` | GET | 1978 |
| `/api/strategy/list` | GET | 2018 |
| `/api/strategy/markers/<path:strategy>/<ticker>` | GET | 2028 |
| `/api/ticker/<ticker>/ohlcv` | GET | 2088 |
| `/api/premover/watchlist` | GET | 2151 |
| `/api/premover/run` | POST | 2162 |

Module-level state that moves here:
- `STRATEGY_MARKER_META: dict` (app.py line 2004)

**`screener/routes.py` — existing `screener_bp` (addition)**

| Route | Method | app.py line |
|-------|--------|-------------|
| `/api/screener/swing_onset` | POST | 918 |

Note: this route shares the `/api/screener/` URL prefix with the existing screener blueprint. It is moved (not extracted to a new file).

### `app.py` after split (~80 lines)

Keeps:
- Flask app creation + config (`load_dotenv`, `DB_PATH`, Telegram env vars)
- Blueprint registrations (7 total: `backtest_bp`, `paper_bp`, `flow_bp`, `telegram_bp`, `ticker_bp`, `backtest_multi_bp`, `screener_bp`)
- Page-render routes: `GET /health`, `GET /`, `GET /backtest/multi`, `GET /screener`
- Utility API routes (not worth a dedicated file): `GET /api/sector/rotation` (line 1722), `GET /api/calendar/status` (1737), `GET /api/calendar/events` (1750), `GET /api/fastmover/summary` (1768), `POST /api/fastmover/run` (1774)
- `start_scheduler()` call + `if __name__ == '__main__'` block

---

## State Migration

| Variable | Current location | New location | Reason |
|----------|-----------------|--------------|--------|
| `telegram_polling_active` | `app.py:1554` | `routes/telegram.py` | Only used by telegram routes |
| `telegram_last_update_id` | `app.py:1555` | `routes/telegram.py` | Only used by telegram routes |
| `STRATEGY_MARKER_META` | `app.py:2004` | `routes/ticker.py` | Only used by ticker/strategy routes |

---

## Migration Strategy

1. Create `routes/__init__.py` (empty)
2. Extract Blueprints one file at a time, in dependency order:
   - `routes/backtest.py` first (no cross-Blueprint dependencies)
   - `routes/paper.py`
   - `routes/flow.py`
   - `routes/telegram.py` (carries module-level state)
   - `routes/ticker.py` (carries `STRATEGY_MARKER_META`)
   - Move `/api/screener/swing_onset` into `screener/routes.py`
3. Shrink `app.py` to entry-point-only
4. Run full test suite after each Blueprint extraction

Each Blueprint file follows the same header pattern established in R5a:
```python
import os
import sqlite3
import logging
from dotenv import load_dotenv
from flask import Blueprint, request, jsonify, render_template
import pytz

load_dotenv()
DB_PATH = os.getenv("DB_PATH", "/home/tjiesar/10 Projects/idx-walkforward-5001/data/walkforward.db")
```

**Callers unchanged:** All routes remain at the same URLs. Blueprint registration in `app.py` uses no `url_prefix` for the new blueprints (same as `backtest_multi_bp`), so no URL changes.

---

## Testing

- No new tests required — pure structural refactor with zero logic changes.
- Full test suite (`venv/bin/pytest`) must be green after each Blueprint extraction.
- Final gate: all tests pass, Flask app starts cleanly, all 44 extracted routes respond.

---

## Out of Scope

- `app.py` → application factory pattern (`create_app()`) — deferred
- Moving `routes_backtest_multi.py` into `routes/` — separate cleanup task
- Any logic changes to route handlers
- `GET /api/fastmover/*` and `GET /api/sector/*` and `GET /api/calendar/*` — remain in `app.py` (utility routes, ~30 lines total, not worth a dedicated file)
