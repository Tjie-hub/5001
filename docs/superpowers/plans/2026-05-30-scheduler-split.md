# R5a — scheduler.py Split Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert `scheduler.py` (1887 lines) into a Python package `scheduler/` with five focused sub-modules, zero logic changes.

**Architecture:** Five sub-modules (state, utils, jobs, scanner, reports) plus `__init__.py` that re-exports every symbol that callers already import. `scheduler/__init__.py` replaces `start_scheduler()` from the old module. Old `scheduler.py` is deleted last, after the package is verified.

**Tech Stack:** Python 3, APScheduler 3.x, pytz, sqlite3, python-dotenv.

---

## File Map

| File | Role | Key symbols |
|------|------|-------------|
| `scheduler/state.py` | Module-level cache dicts | `_regime_clf_cache`, `_sector_scores_cache`, `_last_trades_state` |
| `scheduler/utils.py` | Shared fetch helpers | `get_all_tickers`, `fetch_latest`, `_load_ohlcv_bulk`, `send_suspension_resume_alerts` |
| `scheduler/jobs.py` | Scheduled data-ingestion jobs | `refresh_wf_scores`, `_refresh_backtest_cache`, `run_flow_fetch`, `run_broker_flow_fetch`, `run_foreign_snapshot`, `run_news_fetch`, `run_premover_eod`, `_run_open_trade_monitor`, `_run_screener_intraday`, `_run_screener_eod` |
| `scheduler/scanner.py` | Signal scanning | `calc_votes`, `check_fundamental`, `_detect_price_shock`, `_load_stockbit_token`, `check_keystats_freshness`, `_get_sector_scores_cached`, `_sector_verdict`, `scan_momentum_signals`, `daily_signal_scan`, `get_ticker_best_strategies`, `scheduled_multi_strategy_scan` |
| `scheduler/reports.py` | Monitoring reports | `daily_fetch_report`, `open_trades_status_report`, `flow_broker_report`, `auto_trade_status_report` |
| `scheduler/__init__.py` | Package entry point | `start_scheduler()` + re-exports of all symbols above |
| `scheduler.py` | **DELETED** after package verified | — |

**Dependency graph (no cycles):**
```
scheduler/__init__.py
  ├── scheduler/jobs.py      → scheduler/utils.py
  ├── scheduler/scanner.py   → scheduler/utils.py, scheduler/state.py
  └── scheduler/reports.py  → scheduler/state.py
scheduler/utils.py   → (no internal imports)
scheduler/state.py   → (no imports)
```

---

### Task 1: Create `scheduler/state.py`

**Files:**
- Create: `scheduler/state.py`

This module holds only the three module-level cache dicts that are currently defined at lines 308, 311, and 362 of `scheduler.py`. No logic — just the variables.

- [x] **Step 1: Create `scheduler/` directory and `state.py`**

```python
# scheduler/state.py

_regime_clf_cache: dict = {}
_sector_scores_cache: tuple = (None, 0.0)
_last_trades_state: dict = {}
```

- [x] **Step 2: Verify syntax**

```bash
python -c "from scheduler.state import _regime_clf_cache, _sector_scores_cache, _last_trades_state; print('state ok')"
```

Expected: `state ok`

Note: This works because Python 3.3+ supports namespace packages — the `scheduler/` directory is importable even without `__init__.py`, as long as `scheduler.py` and `scheduler/__init__.py` are NOT both present yet. At this point only `scheduler.py` exists as the module. The `scheduler.state` sub-module is accessible regardless.

- [x] **Step 3: Commit**

```bash
git add scheduler/state.py
git commit -m "refactor(r5a): add scheduler/state.py — cache dicts"
```

---

### Task 2: Create `scheduler/utils.py`

**Files:**
- Create: `scheduler/utils.py`
- Reference: `scheduler.py` lines 13–116 (imports + `get_all_tickers`, `send_suspension_resume_alerts`, `fetch_latest`, `_load_ohlcv_bulk`)

These four functions are used by both `scanner.py` and `jobs.py`. Copy them verbatim — no logic changes.

- [x] **Step 1: Read source lines to copy**

Read `scheduler.py` lines 1–116 to get the exact function bodies.

- [x] **Step 2: Create `scheduler/utils.py`**

```python
# scheduler/utils.py
import os
import sqlite3
import logging
import pandas as pd
from dotenv import load_dotenv
from datetime import datetime
import pytz

load_dotenv()

WIB = pytz.timezone("Asia/Jakarta")
DB_PATH = os.getenv("DB_PATH", "/home/tjiesar/10 Projects/idx-walkforward-5001/data/walkforward.db")
TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

from utils.telegram import send_telegram  # noqa: E402
```

Then append, verbatim from `scheduler.py`:
- `get_all_tickers()` (lines 24–40)
- `send_suspension_resume_alerts(...)` (lines 42–80)
- `fetch_latest()` (lines 83–107)
- `_load_ohlcv_bulk()` (lines 109–116)

- [x] **Step 3: Verify import**

```bash
python -c "from scheduler.utils import get_all_tickers, fetch_latest, _load_ohlcv_bulk, send_suspension_resume_alerts; print('utils ok')"
```

Expected: `utils ok`

- [x] **Step 4: Commit**

```bash
git add scheduler/utils.py
git commit -m "refactor(r5a): add scheduler/utils.py — shared fetch helpers"
```

---

### Task 3: Create `scheduler/jobs.py`

**Files:**
- Create: `scheduler/jobs.py`
- Reference: `scheduler.py` lines 119–158 (`refresh_wf_scores`), 691–826 (flow/broker/foreign/news jobs), 1194–1221 (APScheduler wrappers), 1698–1757 (`_refresh_backtest_cache`, `run_premover_eod`)

These are all functions registered as APScheduler CronTrigger jobs in `start_scheduler()` that are NOT signal scanning or reporting.

- [x] **Step 1: Read source lines**

Read `scheduler.py` to get exact bodies for: `refresh_wf_scores` (119–158), `run_flow_fetch` (691–729), `run_broker_flow_fetch` (732–765), `run_foreign_snapshot` (768–807), `run_news_fetch` (809–826), `_run_open_trade_monitor` (1194–1205), `_run_screener_intraday` (1208–1213), `_run_screener_eod` (1216–1221), `_refresh_backtest_cache` (1698–1743), `run_premover_eod` (1746–1757).

- [x] **Step 2: Create `scheduler/jobs.py`**

```python
# scheduler/jobs.py
import os
import sqlite3
import logging
from dotenv import load_dotenv
from datetime import datetime
import pytz

load_dotenv()

WIB = pytz.timezone("Asia/Jakarta")
DB_PATH = os.getenv("DB_PATH", "/home/tjiesar/10 Projects/idx-walkforward-5001/data/walkforward.db")

from utils.telegram import send_telegram  # noqa: E402
from scheduler.utils import get_all_tickers, _load_ohlcv_bulk  # noqa: E402
```

Then append verbatim from `scheduler.py` (in order):
- `refresh_wf_scores()` (lines 119–158)
- `run_flow_fetch()` (lines 691–729)
- `run_broker_flow_fetch()` (lines 732–765)
- `run_foreign_snapshot()` (lines 768–807)
- `run_news_fetch()` (lines 809–826)
- `_run_open_trade_monitor()` (lines 1194–1205)
- `_run_screener_intraday()` (lines 1208–1213)
- `_run_screener_eod()` (lines 1216–1221)
- `_refresh_backtest_cache()` (lines 1698–1743)
- `run_premover_eod()` (lines 1746–1757)

- [x] **Step 3: Verify import**

```bash
python -c "from scheduler.jobs import refresh_wf_scores, run_flow_fetch, run_broker_flow_fetch, run_foreign_snapshot, run_news_fetch, run_premover_eod; print('jobs ok')"
```

Expected: `jobs ok`

- [x] **Step 4: Commit**

```bash
git add scheduler/jobs.py
git commit -m "refactor(r5a): add scheduler/jobs.py — data ingestion job functions"
```

---

### Task 4: Create `scheduler/scanner.py`

**Files:**
- Create: `scheduler/scanner.py`
- Reference: `scheduler.py` lines 161–688 (scanner helpers + scan functions), 829–852 (`get_ticker_best_strategies`), 855–1192 (`scheduled_multi_strategy_scan`)

This is the largest sub-module. It contains all signal scanning logic plus its private helpers.

- [x] **Step 1: Read source lines**

Read `scheduler.py` to get exact bodies for:
- `calc_votes(df)` (161–188)
- `check_fundamental(ticker)` (191–212)
- `_detect_price_shock(df, ...)` (214–226)
- `_load_stockbit_token(...)` (229–238)
- `check_keystats_freshness(...)` (241–304)
- `_get_sector_scores_cached()` (313–323)
- `_sector_verdict(ticker, scored)` (330–359)
- `scan_momentum_signals()` (365–688)
- `get_ticker_best_strategies(ticker, ...)` (829–852)
- `scheduled_multi_strategy_scan()` (855–1192)
- `daily_signal_scan()` (584–688) — NOTE: this is nested inside the range above; read carefully

Wait — re-read carefully: `daily_signal_scan` starts at line 584. `scan_momentum_signals` starts at 365 and ends where `daily_signal_scan` begins. So:
- `scan_momentum_signals()` = lines 365–583
- `daily_signal_scan()` = lines 584–688

- [x] **Step 2: Create `scheduler/scanner.py`**

```python
# scheduler/scanner.py
import os
import sqlite3
import logging
from dotenv import load_dotenv
from datetime import datetime
import pytz

load_dotenv()

WIB = pytz.timezone("Asia/Jakarta")
DB_PATH = os.getenv("DB_PATH", "/home/tjiesar/10 Projects/idx-walkforward-5001/data/walkforward.db")

from utils.telegram import send_telegram  # noqa: E402
from scheduler.state import _regime_clf_cache  # noqa: E402  — dict mutation; _sector_scores_cache handled inside _get_sector_scores_cached via scheduler.state ref
from scheduler.utils import get_all_tickers, _load_ohlcv_bulk, fetch_latest  # noqa: E402
```

Then append verbatim from `scheduler.py` (in order):
- `calc_votes(df)` (161–188)
- `check_fundamental(ticker)` (191–212)
- `_detect_price_shock(df, ...)` (214–226)
- `_load_stockbit_token(...)` (229–238)
- `check_keystats_freshness(...)` (241–304)
- `_get_sector_scores_cached()` (313–323)
- `_sector_verdict(ticker, scored)` (330–359)
- `scan_momentum_signals()` (365–583)
- `daily_signal_scan()` (584–688)
- `get_ticker_best_strategies(ticker, ...)` (829–852)
- `scheduled_multi_strategy_scan()` (855–1192)

**Critical:** `_get_sector_scores_cached` uses `global _sector_scores_cache` (line 318). After the move, this `global` declaration still works because `_sector_scores_cache` is defined at module level in `scanner.py` (imported from `scheduler.state` at the top). However, `global` in Python refers to the local module's global scope. If `_sector_scores_cache` is imported as a name from `scheduler.state`, writing `global _sector_scores_cache` and then `_sector_scores_cache = (scores, time.time())` will rebind the name in `scheduler.scanner`'s namespace, NOT in `scheduler.state`. This means the cache update won't persist across calls.

**Fix for `_get_sector_scores_cached`:** Change it to use `scheduler.state` directly instead of `global`:

```python
def _get_sector_scores_cached():
    """Return score_sectors() cached for up to 1 hour."""
    import time
    import scheduler.state as _state
    from engine.sector_rotation import score_sectors
    scores, ts = _state._sector_scores_cache
    if scores is not None and (time.time() - ts) < 3600:
        return scores
    scores = score_sectors()
    _state._sector_scores_cache = (scores, time.time())
    return scores
```

Similarly, `scan_momentum_signals` uses `_regime_clf_cache` with direct dict mutation (`.get()`, `[]=`). Dict mutation works fine through the imported reference — no `global` needed since we're mutating the dict object, not rebinding the name. Leave those lines unchanged.

- [x] **Step 3: Verify import**

```bash
python -c "from scheduler.scanner import scan_momentum_signals, daily_signal_scan, scheduled_multi_strategy_scan, check_fundamental; print('scanner ok')"
```

Expected: `scanner ok`

- [x] **Step 4: Commit**

```bash
git add scheduler/scanner.py
git commit -m "refactor(r5a): add scheduler/scanner.py — signal scanning functions"
```

---

### Task 5: Create `scheduler/reports.py`

**Files:**
- Create: `scheduler/reports.py`
- Reference: `scheduler.py` lines 1224–1695 (`daily_fetch_report`, `open_trades_status_report`, `flow_broker_report`, `auto_trade_status_report`)

- [x] **Step 1: Read source lines**

Read `scheduler.py` lines 1224–1695 to get exact bodies for all four report functions.

- [x] **Step 2: Create `scheduler/reports.py`**

```python
# scheduler/reports.py
import os
import sqlite3
import logging
from dotenv import load_dotenv
from datetime import datetime
import pytz

load_dotenv()

WIB = pytz.timezone("Asia/Jakarta")
DB_PATH = os.getenv("DB_PATH", "/home/tjiesar/10 Projects/idx-walkforward-5001/data/walkforward.db")

from utils.telegram import send_telegram  # noqa: E402
from scheduler.state import _last_trades_state  # noqa: E402
```

Then append verbatim from `scheduler.py`:
- `daily_fetch_report()` (1224–1319)
- `open_trades_status_report()` (1321–1488)
- `flow_broker_report()` (1490–1649)
- `auto_trade_status_report()` (1651–1695)

**Critical:** `open_trades_status_report` uses `global _last_trades_state` (line 1323) and later rebinds `_last_trades_state = {}` (line 1344) and `_last_trades_state.update(...)` (line 1482). The rebind (`= {}`) won't update `scheduler.state` if `_last_trades_state` was imported as a name.

**Fix for `open_trades_status_report`:** Use `scheduler.state` directly for rebinding, same pattern as `_get_sector_scores_cached`:

Find the two lines in `open_trades_status_report` that rebind `_last_trades_state`:
1. `global _last_trades_state` — remove this line
2. `_last_trades_state = {}` — replace with `import scheduler.state as _state; _state._last_trades_state = {}`
3. `prev_ids = set(_last_trades_state.keys())` — replace with `prev_ids = set(_state._last_trades_state.keys())` (use `_state` ref)
4. `prev = _last_trades_state.get(tid)` — replace with `prev = _state._last_trades_state.get(tid)`
5. `_last_trades_state.update(current_state)` — replace with `_state._last_trades_state.update(current_state)`

The cleaner approach: replace all references to `_last_trades_state` inside `open_trades_status_report` with `_state._last_trades_state` (and do `import scheduler.state as _state` inside the function, removing the module-level import of `_last_trades_state`).

Revised `scheduler/reports.py` header:

```python
# scheduler/reports.py
import os
import sqlite3
import logging
from dotenv import load_dotenv
from datetime import datetime
import pytz

load_dotenv()

WIB = pytz.timezone("Asia/Jakarta")
DB_PATH = os.getenv("DB_PATH", "/home/tjiesar/10 Projects/idx-walkforward-5001/data/walkforward.db")

from utils.telegram import send_telegram  # noqa: E402
```

Inside `open_trades_status_report`, replace:
```python
# BEFORE (original scheduler.py):
global _last_trades_state
...
prev_ids = set(_last_trades_state.keys())
...
_last_trades_state = {}
...
prev = _last_trades_state.get(tid)
...
_last_trades_state.update(current_state)
```
```python
# AFTER (in reports.py):
import scheduler.state as _state
...
prev_ids = set(_state._last_trades_state.keys())
...
_state._last_trades_state = {}
...
prev = _state._last_trades_state.get(tid)
...
_state._last_trades_state.update(current_state)
```

Remove the `global _last_trades_state` line.

- [x] **Step 3: Verify import**

```bash
python -c "from scheduler.reports import daily_fetch_report, open_trades_status_report, flow_broker_report, auto_trade_status_report; print('reports ok')"
```

Expected: `reports ok`

- [x] **Step 4: Commit**

```bash
git add scheduler/reports.py
git commit -m "refactor(r5a): add scheduler/reports.py — monitoring report functions"
```

---

### Task 6: Create `scheduler/__init__.py` and delete `scheduler.py`

**Files:**
- Create: `scheduler/__init__.py`
- Delete: `scheduler.py`
- Reference: `scheduler.py` lines 1760–1888 (`start_scheduler()` + `__main__` block)

This is the atomic switchover. When `scheduler/__init__.py` exists, Python's import system will use the package (`scheduler/`) instead of the module (`scheduler.py`). All callers that do `from scheduler import X` will now get `X` from `__init__.py`'s exports.

**Callers that import from `scheduler` (must all keep working):**
- `app.py:7` — `start_scheduler, scan_momentum_signals, daily_signal_scan, send_telegram`
- `app.py:1038` — `open_trades_status_report`
- `app.py:1117` — `check_fundamental`
- `paper_trade.py` (×4) — `send_telegram`
- `tests/test_suspension_alert.py` — `send_suspension_resume_alerts`
- `tests/test_fundamental_refresh.py` — `_detect_price_shock, _load_stockbit_token, check_keystats_freshness`

- [x] **Step 1: Read `start_scheduler()` source**

Read `scheduler.py` lines 1760–1888 to get the exact function body and `__main__` block.

- [x] **Step 2: Create `scheduler/__init__.py`**

```python
# scheduler/__init__.py
import os
from dotenv import load_dotenv
import sqlite3
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

load_dotenv()

WIB = pytz.timezone("Asia/Jakarta")
DB_PATH = os.getenv("DB_PATH", "/home/tjiesar/10 Projects/idx-walkforward-5001/data/walkforward.db")

# Re-export send_telegram so callers doing `from scheduler import send_telegram` keep working
from utils.telegram import send_telegram  # noqa: F401

# Re-export utils
from scheduler.utils import (  # noqa: F401
    get_all_tickers,
    fetch_latest,
    _load_ohlcv_bulk,
    send_suspension_resume_alerts,
)

# Re-export scanner
from scheduler.scanner import (  # noqa: F401
    calc_votes,
    check_fundamental,
    _detect_price_shock,
    _load_stockbit_token,
    check_keystats_freshness,
    scan_momentum_signals,
    daily_signal_scan,
    scheduled_multi_strategy_scan,
    get_ticker_best_strategies,
)

# Re-export jobs
from scheduler.jobs import (  # noqa: F401
    refresh_wf_scores,
    run_flow_fetch,
    run_broker_flow_fetch,
    run_foreign_snapshot,
    run_news_fetch,
    run_premover_eod,
    _refresh_backtest_cache,
    _run_open_trade_monitor,
    _run_screener_intraday,
    _run_screener_eod,
)

# Re-export reports
from scheduler.reports import (  # noqa: F401
    daily_fetch_report,
    open_trades_status_report,
    flow_broker_report,
    auto_trade_status_report,
)
```

Then append `start_scheduler()` verbatim from `scheduler.py` lines 1760–1871 (including all `scheduler.add_job(...)` calls).

Then append the `__main__` block verbatim from lines 1873–1887.

- [x] **Step 3: Delete `scheduler.py`**

```bash
git rm scheduler.py
```

- [x] **Step 4: Verify full test suite passes**

```bash
venv/bin/pytest -x -q 2>&1 | tail -20
```

Expected: all tests pass (same count as before this refactor, currently 173).

- [x] **Step 5: Verify the app starts**

```bash
python -c "from scheduler import start_scheduler; print('start_scheduler importable')"
```

Expected: `start_scheduler importable`

- [x] **Step 6: Verify re-exports work for callers**

```bash
python -c "
from scheduler import (
    start_scheduler, scan_momentum_signals, daily_signal_scan,
    send_telegram, open_trades_status_report, check_fundamental,
    send_suspension_resume_alerts, _detect_price_shock,
    _load_stockbit_token, check_keystats_freshness,
)
print('all re-exports ok')
"
```

Expected: `all re-exports ok`

- [x] **Step 7: Commit**

```bash
git add scheduler/__init__.py
git commit -m "refactor(r5a): complete scheduler package split — delete scheduler.py, add __init__.py"
```
