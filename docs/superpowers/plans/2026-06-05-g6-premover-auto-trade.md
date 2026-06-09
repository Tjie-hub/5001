# G6: Premover → Paper Trade Auto-Execution Toggle — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a three-mode toggle (off/shadow/enforce) to auto-execute paper trades from premover alerts, with gate evaluation and Telegram shadow logging so the user can see what would have been traded and why it was blocked.

**Architecture:** New helpers in `paper_trade.py` (`get/set_premover_mode`, `evaluate_premover_trade`, `_log_premover_auto`) plus a `premover_auto_log` DB table. `run_premover_eod()` in `scheduler/jobs.py` calls evaluation+logging after each scan run. A `GET/POST /api/paper/premover_mode` endpoint exposes the toggle. `get_config()` gets a one-line defensive fix to handle string config values without breaking existing float callers.

**Tech Stack:** Python, SQLite, Flask, APScheduler, pytest.

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `paper_trade.py` | **Modify** | Mode helpers, gate evaluator, log writer, table init, `get_config` fix |
| `scheduler/jobs.py` | **Modify** | Update `run_premover_eod()`, add `_send_premover_auto_summary()` |
| `routes/backtest.py` | **Modify** | Add 2 Flask endpoints |
| `tests/test_premover_auto_trade.py` | **Create** | 6 tests |

---

## Task 1: Mode Helpers + DB Table + `get_config` Fix

**Files:**
- Modify: `paper_trade.py`
- Create: `tests/test_premover_auto_trade.py`

**Important:** `get_config()` at line 133 does `float(r["value"])` for ALL `paper_config` rows. Adding a string value like `"off"` would cause `ValueError`. We fix it defensively before adding any string keys.

- [x] **Step 1: Write failing tests**

Create `tests/test_premover_auto_trade.py`:

```python
"""Tests for premover auto-execution toggle (G6)."""
import sqlite3
import pytest
import pandas as pd


@pytest.fixture()
def pt_db(tmp_path, monkeypatch):
    """Isolated paper_trade DB with schema initialized."""
    import paper_trade as pt
    db = str(tmp_path / "pt.db")
    monkeypatch.setattr(pt, "DB_PATH", db)
    pt.init_paper_table()
    return db


def test_default_premover_mode_is_off(pt_db):
    """Default mode is 'off' when config key is absent."""
    from paper_trade import get_premover_mode
    assert get_premover_mode() == "off"


def test_set_and_get_premover_mode(pt_db):
    """set_premover_mode persists and get_premover_mode retrieves it."""
    from paper_trade import get_premover_mode, set_premover_mode
    set_premover_mode("shadow")
    assert get_premover_mode() == "shadow"
    set_premover_mode("enforce")
    assert get_premover_mode() == "enforce"
    set_premover_mode("off")
    assert get_premover_mode() == "off"


def test_set_premover_mode_invalid_raises(pt_db):
    """set_premover_mode raises ValueError for unknown mode."""
    from paper_trade import set_premover_mode
    with pytest.raises(ValueError):
        set_premover_mode("invalid_mode")


def test_get_config_survives_string_values(pt_db):
    """get_config() must not crash when paper_config has non-numeric values."""
    from paper_trade import get_config, set_premover_mode
    set_premover_mode("shadow")     # inserts "off" string
    cfg = get_config()              # must not raise
    assert "capital" in cfg         # existing numeric keys still work
    assert cfg["capital"] == 50_000_000.0
```

- [x] **Step 2: Run tests — expect FAIL**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && "/home/tjiesar/10 Projects/idx-walkforward-5001/venv/bin/python3" -m pytest tests/test_premover_auto_trade.py -v 2>&1 | tail -10
```

Expected: `ImportError: cannot import name 'get_premover_mode'`

- [x] **Step 3: Fix `get_config()` to handle non-numeric values**

In `paper_trade.py`, find `get_config()` at line 133. Change:

```python
def get_config():
    conn = get_db()
    rows = conn.execute("SELECT key, value FROM paper_config").fetchall()
    conn.close()
    return {r["key"]: float(r["value"]) for r in rows}
```

to:

```python
def get_config():
    conn = get_db()
    rows = conn.execute("SELECT key, value FROM paper_config").fetchall()
    conn.close()
    result = {}
    for r in rows:
        try:
            result[r["key"]] = float(r["value"])
        except (ValueError, TypeError):
            result[r["key"]] = r["value"]
    return result
```

- [x] **Step 4: Add `premover_auto_log` table to `init_paper_table()`**

In `paper_trade.py`, find `init_paper_table()` (line 73). After the last `ADD COLUMN` migration block (around line 128), add:

```python
    # premover_auto_log: records shadow/enforce evaluation per setup
    conn.execute("""
        CREATE TABLE IF NOT EXISTS premover_auto_log (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker       TEXT NOT NULL,
            detected_at  TEXT NOT NULL,
            pattern_type TEXT,
            score        INTEGER,
            mode         TEXT,
            would_trade  INTEGER,
            skip_reason  TEXT,
            logged_at    TEXT
        )
    """)
```

Also add the default config key to the `configs` list in `init_paper_table()`. Find the `configs` list (around line 99) and add after the last entry before the closing bracket:

```python
        ("auto_trade_from_premover", "off"),
```

- [x] **Step 5: Add `get_premover_mode()` and `set_premover_mode()`**

Append to `paper_trade.py` after `_set_config()` (around line 480):

```python

def get_premover_mode() -> str:
    """Read auto_trade_from_premover from paper_config. Returns 'off' if not set."""
    conn = get_db()
    row = conn.execute(
        "SELECT value FROM paper_config WHERE key='auto_trade_from_premover'"
    ).fetchone()
    conn.close()
    return str(row[0]) if row else "off"


def set_premover_mode(mode: str) -> None:
    """Set auto_trade_from_premover mode. Must be 'off', 'shadow', or 'enforce'."""
    if mode not in ("off", "shadow", "enforce"):
        raise ValueError(f"Invalid mode '{mode}'. Must be: off, shadow, enforce.")
    _set_config("auto_trade_from_premover", mode)
```

- [x] **Step 6: Run the 4 tests — expect PASS**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && "/home/tjiesar/10 Projects/idx-walkforward-5001/venv/bin/python3" -m pytest tests/test_premover_auto_trade.py::test_default_premover_mode_is_off tests/test_premover_auto_trade.py::test_set_and_get_premover_mode tests/test_premover_auto_trade.py::test_set_premover_mode_invalid_raises tests/test_premover_auto_trade.py::test_get_config_survives_string_values -v 2>&1 | tail -10
```

Expected: 4 `PASSED`

- [x] **Step 7: Commit**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && git add paper_trade.py tests/test_premover_auto_trade.py && git commit -m "feat(g6): add premover mode helpers, premover_auto_log table, fix get_config for strings"
```

---

## Task 2: `evaluate_premover_trade` + `_log_premover_auto`

**Files:**
- Modify: `paper_trade.py`
- Modify: `tests/test_premover_auto_trade.py`

- [x] **Step 1: Write failing tests**

Append to `tests/test_premover_auto_trade.py`:

```python
def test_evaluate_premover_trade_passes_all_gates(pt_db):
    """Clean state: no open trades, no DD block, BULL regime → would_trade=True."""
    from paper_trade import evaluate_premover_trade
    import sqlite3
    # Insert BULL regime in backtest_cache
    conn = sqlite3.connect(pt_db)
    conn.execute("""CREATE TABLE IF NOT EXISTS backtest_cache (
        ticker TEXT, computed_date TEXT, best_strategy TEXT, best_return REAL,
        win_rate REAL, sharpe REAL, total_trades INTEGER, profitable INTEGER,
        regime TEXT, updated_at TEXT, PRIMARY KEY (ticker, computed_date))""")
    conn.execute("INSERT INTO backtest_cache VALUES ('BRPT','2026-06-05','Crash Recovery',22.0,100.0,2.0,1,1,'BULL','2026-06-05')")
    conn.commit()
    conn.close()
    result = evaluate_premover_trade("BRPT", 55, "REVERSAL_BREAKOUT")
    assert result["would_trade"] is True
    assert result["skip_reason"] is None


def test_evaluate_blocks_on_dd_circuit_breaker(pt_db):
    """entries_blocked=1 in paper_config → would_trade=False, skip_reason='dd_circuit_breaker'."""
    from paper_trade import evaluate_premover_trade
    import sqlite3
    conn = sqlite3.connect(pt_db)
    conn.execute("INSERT OR REPLACE INTO paper_config VALUES ('entries_blocked','1')")
    conn.commit()
    conn.close()
    result = evaluate_premover_trade("BRPT", 55, "REVERSAL_BREAKOUT")
    assert result["would_trade"] is False
    assert result["skip_reason"] == "dd_circuit_breaker"


def test_evaluate_blocks_on_bear_regime(pt_db):
    """backtest_cache has regime=BEAR → would_trade=False, skip_reason starts with 'regime'."""
    from paper_trade import evaluate_premover_trade
    import sqlite3
    conn = sqlite3.connect(pt_db)
    conn.execute("""CREATE TABLE IF NOT EXISTS backtest_cache (
        ticker TEXT, computed_date TEXT, best_strategy TEXT, best_return REAL,
        win_rate REAL, sharpe REAL, total_trades INTEGER, profitable INTEGER,
        regime TEXT, updated_at TEXT, PRIMARY KEY (ticker, computed_date))""")
    conn.execute("INSERT INTO backtest_cache VALUES ('BEAR_TICKER','2026-06-05','momentum',5.0,60.0,1.0,1,1,'BEAR','2026-06-05')")
    conn.commit()
    conn.close()
    result = evaluate_premover_trade("BEAR_TICKER", 52, "REVERSAL_BREAKOUT")
    assert result["would_trade"] is False
    assert result["skip_reason"] is not None
    assert "regime" in result["skip_reason"]
```

- [x] **Step 2: Run tests — expect FAIL**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && "/home/tjiesar/10 Projects/idx-walkforward-5001/venv/bin/python3" -m pytest tests/test_premover_auto_trade.py::test_evaluate_premover_trade_passes_all_gates tests/test_premover_auto_trade.py::test_evaluate_blocks_on_dd_circuit_breaker tests/test_premover_auto_trade.py::test_evaluate_blocks_on_bear_regime -v 2>&1 | tail -10
```

Expected: `ImportError: cannot import name 'evaluate_premover_trade'`

- [x] **Step 3: Implement `evaluate_premover_trade` and `_log_premover_auto`**

Append to `paper_trade.py` after `set_premover_mode()`:

```python

def evaluate_premover_trade(ticker: str, score: int, pattern_type: str) -> dict:
    """
    Dry-run all open_trade() gates without side effects.
    Returns {'would_trade': bool, 'skip_reason': str|None, 'gates': dict}.
    Gates checked: DD circuit breaker → max positions → duplicate → regime.
    """
    gates: dict = {}

    # Gate 1: DD circuit breaker
    if is_entries_blocked():
        return {'would_trade': False, 'skip_reason': 'dd_circuit_breaker',
                'gates': {'entries_blocked': True}}
    gates['entries_blocked'] = False

    cfg        = get_config()
    open_trades = get_open_trades()
    max_open   = int(cfg.get('max_open', 5))

    # Gate 2: position limit
    if len(open_trades) >= max_open:
        return {'would_trade': False, 'skip_reason': f'max_open_{max_open}',
                'gates': {**gates, 'max_open': True}}
    gates['max_open'] = False

    # Gate 3: duplicate position
    if any(t['ticker'] == ticker for t in open_trades):
        return {'would_trade': False, 'skip_reason': 'already_open',
                'gates': {**gates, 'duplicate': True}}
    gates['duplicate'] = False

    # Gate 4: regime filter (uses backtest_cache, no OHLCV load needed)
    if int(cfg.get('filter_regime', 1)):
        conn = get_db()
        row = conn.execute(
            "SELECT regime FROM backtest_cache WHERE ticker=? "
            "ORDER BY computed_date DESC LIMIT 1",
            (ticker,)
        ).fetchone()
        conn.close()
        regime = str(row['regime']) if row and row['regime'] else 'UNKNOWN'
        if regime == 'BEAR':
            return {'would_trade': False, 'skip_reason': f'regime_bear',
                    'gates': {**gates, 'regime': regime}}
        gates['regime'] = regime

    return {'would_trade': True, 'skip_reason': None, 'gates': gates}


def _log_premover_auto(ticker: str, detected_at: str, pattern_type: str,
                       score: int, mode: str, eval_result: dict) -> None:
    """Insert one row into premover_auto_log."""
    conn = get_db()
    now_str = datetime.now(WIB).strftime('%Y-%m-%d %H:%M')
    conn.execute("""
        INSERT INTO premover_auto_log
        (ticker, detected_at, pattern_type, score, mode, would_trade, skip_reason, logged_at)
        VALUES (?,?,?,?,?,?,?,?)
    """, (ticker, detected_at, pattern_type, score, mode,
          int(eval_result.get('would_trade', False)),
          eval_result.get('skip_reason'), now_str))
    conn.commit()
    conn.close()
```

- [x] **Step 4: Run the 3 new tests + all 4 prior tests**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && "/home/tjiesar/10 Projects/idx-walkforward-5001/venv/bin/python3" -m pytest tests/test_premover_auto_trade.py -v 2>&1 | tail -15
```

Expected: all 7 tests `PASSED`

- [x] **Step 5: Commit**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && git add paper_trade.py tests/test_premover_auto_trade.py && git commit -m "feat(g6): add evaluate_premover_trade and _log_premover_auto"
```

---

## Task 3: Update `run_premover_eod()` + Telegram Summary

**Files:**
- Modify: `scheduler/jobs.py`

- [x] **Step 1: Add `_send_premover_auto_summary()` helper to `scheduler/jobs.py`**

In `scheduler/jobs.py`, before `run_premover_eod()` (around line 275), insert:

```python
def _send_premover_auto_summary(rows: list, mode: str, send_fn) -> None:
    """Send Telegram summary of shadow/enforce evaluation results."""
    _LABEL = {'off': 'OFF', 'shadow': 'SHADOW', 'enforce': 'ENFORCE'}
    mode_label = _LABEL.get(mode, mode.upper())
    passed = [r for r in rows if r.get('would_trade')]
    blocked = [r for r in rows if not r.get('would_trade')]
    msg = f"\U0001f916 <b>Premover {mode_label} — {len(rows)} setups</b>\n\n"
    for r in passed:
        msg += f"✅ <b>{r['ticker']}</b> score={r['score']} → PASS\n"
    for r in blocked:
        reason = r.get('skip_reason', 'unknown')
        msg += f"❌ <b>{r['ticker']}</b> score={r['score']} → {reason}\n"
    if not rows:
        msg += "No new setups to evaluate.\n"
    try:
        send_fn(msg)
    except Exception as e:
        print(f"[premover auto] Telegram summary error: {e}")

```

- [x] **Step 2: Update `run_premover_eod()` to run evaluation after scan**

Find `run_premover_eod()` (around line 275 in `scheduler/jobs.py`). Replace:

```python
def run_premover_eod():
    """EOD pre-breakout scan — runs at 16:30 after data fetch."""
    from engine.premover_detector import run_scan
    now_str = datetime.now(WIB).strftime('%H:%M')
    print(f"[{now_str}] Pre-mover EOD scan dimulai...")
    try:
        new_setups = run_scan(DB_PATH, send_alert_fn=send_telegram)
        print(f"[{datetime.now(WIB).strftime('%H:%M')}] Pre-mover scan selesai. "
              f"{len(new_setups)} new setups.")
    except Exception as e:
        print(f"[{datetime.now(WIB).strftime('%H:%M')}] Pre-mover scan error: {e}")
        send_telegram(f"🔴 <b>Pre-mover Scan Error</b>\n<code>{str(e)[:200]}</code>")
```

with:

```python
def run_premover_eod():
    """EOD pre-breakout scan — runs at 16:30 after data fetch."""
    from engine.premover_detector import run_scan
    from paper_trade import (get_premover_mode, evaluate_premover_trade,
                              open_trade, _log_premover_auto, init_paper_table)
    now_str = datetime.now(WIB).strftime('%H:%M')
    print(f"[{now_str}] Pre-mover EOD scan dimulai...")
    try:
        new_setups = run_scan(DB_PATH, send_alert_fn=send_telegram)
        print(f"[{datetime.now(WIB).strftime('%H:%M')}] Pre-mover scan selesai. "
              f"{len(new_setups)} new setups.")
    except Exception as e:
        print(f"[{datetime.now(WIB).strftime('%H:%M')}] Pre-mover scan error: {e}")
        send_telegram(f"🔴 <b>Pre-mover Scan Error</b>\n<code>{str(e)[:200]}</code>")
        return

    mode = get_premover_mode()
    if mode not in ('shadow', 'enforce') or not new_setups:
        return

    init_paper_table()
    today = datetime.now(WIB).strftime('%Y-%m-%d')
    summary_rows = []
    for s in new_setups:
        ticker = s['ticker']
        score  = s.get('score', 0)
        pattern = s.get('pattern', 'UNKNOWN')
        try:
            ev = evaluate_premover_trade(ticker, score, pattern)
            _log_premover_auto(ticker, today, pattern, score, mode, ev)
            if mode == 'enforce' and ev['would_trade']:
                close_price = float(s.get('close', 0))
                if close_price > 0:
                    open_trade(ticker, close_price, strategy=None, notify=True)
            summary_rows.append({'ticker': ticker, 'score': score,
                                  'pattern': pattern, **ev})
        except Exception as exc:
            print(f"[premover auto] {ticker} error: {exc}")
            summary_rows.append({'ticker': ticker, 'score': score,
                                  'pattern': pattern,
                                  'would_trade': False, 'skip_reason': f'error:{exc}'})

    _send_premover_auto_summary(summary_rows, mode, send_telegram)
```

- [x] **Step 3: Verify import works**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && "/home/tjiesar/10 Projects/idx-walkforward-5001/venv/bin/python3" -c "from scheduler.jobs import run_premover_eod; print('OK')"
```

Expected: `OK`

- [x] **Step 4: Run full test suite**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && "/home/tjiesar/10 Projects/idx-walkforward-5001/venv/bin/python3" -m pytest tests/ -q --ignore=tests/agent_firm --ignore=tests/test_scheduler_firm_hook.py 2>&1 | tail -5
```

Expected: all tests pass.

- [x] **Step 5: Commit**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && git add scheduler/jobs.py && git commit -m "feat(g6): update run_premover_eod with shadow/enforce auto-trade evaluation"
```

---

## Task 4: Flask Endpoints + Mark G6 Done

**Files:**
- Modify: `routes/backtest.py`
- Modify: `tests/test_premover_auto_trade.py`
- Modify: `TODO.md`

- [x] **Step 1: Write failing API test**

Append to `tests/test_premover_auto_trade.py`:

```python
def test_api_premover_mode_get_and_post(pt_db, monkeypatch):
    """GET returns default 'off'; POST sets mode and GET returns new mode."""
    import paper_trade as pt
    monkeypatch.setattr(pt, "DB_PATH", pt_db)

    # Import app after monkeypatching so routes use tmp db
    from app import app
    app.config['TESTING'] = True
    client = app.test_client()

    resp = client.get('/api/paper/premover_mode')
    assert resp.status_code == 200
    assert resp.get_json()['mode'] == 'off'

    resp = client.post('/api/paper/premover_mode',
                       json={'mode': 'shadow'},
                       content_type='application/json')
    assert resp.status_code == 200
    assert resp.get_json()['mode'] == 'shadow'

    # Verify GET now returns 'shadow'
    resp = client.get('/api/paper/premover_mode')
    assert resp.get_json()['mode'] == 'shadow'

    # Invalid mode returns 400
    resp = client.post('/api/paper/premover_mode',
                       json={'mode': 'unknown'},
                       content_type='application/json')
    assert resp.status_code == 400
```

- [x] **Step 2: Run test — expect FAIL**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && "/home/tjiesar/10 Projects/idx-walkforward-5001/venv/bin/python3" -m pytest tests/test_premover_auto_trade.py::test_api_premover_mode_get_and_post -v 2>&1 | tail -10
```

Expected: 404 or `AttributeError` — endpoint doesn't exist yet.

- [x] **Step 3: Add endpoints to `routes/backtest.py`**

At the end of `routes/backtest.py`, append:

```python

@backtest_bp.route('/api/paper/premover_mode', methods=['GET'])
def api_premover_mode_get():
    """GET current auto_trade_from_premover mode."""
    from paper_trade import get_premover_mode, init_paper_table
    init_paper_table()
    return jsonify({'mode': get_premover_mode()})


@backtest_bp.route('/api/paper/premover_mode', methods=['POST'])
def api_premover_mode_set():
    """POST {'mode': 'off|shadow|enforce'} to update auto_trade_from_premover."""
    from paper_trade import set_premover_mode, get_premover_mode, init_paper_table
    init_paper_table()
    body = request.get_json(force=True) or {}
    mode = body.get('mode', 'off')
    try:
        set_premover_mode(mode)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    return jsonify({'mode': get_premover_mode()})
```

- [x] **Step 4: Run all 8 tests**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && "/home/tjiesar/10 Projects/idx-walkforward-5001/venv/bin/python3" -m pytest tests/test_premover_auto_trade.py -v 2>&1 | tail -15
```

Expected: all 8 tests `PASSED`

- [x] **Step 5: Run full test suite**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && "/home/tjiesar/10 Projects/idx-walkforward-5001/venv/bin/python3" -m pytest tests/ -q --ignore=tests/agent_firm --ignore=tests/test_scheduler_firm_hook.py 2>&1 | tail -5
```

Expected: all tests pass.

- [x] **Step 6: Mark G6 done in `TODO.md`**

Find:
```
- [x] **G6. Premover → paper trade auto-execution**
```

Replace with:
```
- [x] **G6. Premover → paper trade auto-execution** — SHIPPED 2026-06-05. `get/set_premover_mode()`, `evaluate_premover_trade()`, `_log_premover_auto()` in `paper_trade.py`. `premover_auto_log` DB table. `run_premover_eod()` updated to evaluate + log + execute in shadow/enforce mode. Telegram shadow summary shows PASS/BLOCK+reason per setup. `GET/POST /api/paper/premover_mode`. Fixed `get_config()` to handle string values. 8 unit tests.
```

- [x] **Step 7: Commit everything**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && git add routes/backtest.py tests/test_premover_auto_trade.py TODO.md docs/superpowers/plans/2026-06-05-g6-premover-auto-trade.md && git commit -m "feat(g6): add /api/paper/premover_mode endpoints — G6 complete"
```

---

## Self-Review

**Spec coverage:**
- ✅ `get_premover_mode()` / `set_premover_mode()` — Task 1
- ✅ `premover_auto_log` DB table — Task 1
- ✅ Default config `auto_trade_from_premover = "off"` — Task 1
- ✅ `get_config()` fix for string values — Task 1
- ✅ `evaluate_premover_trade()` with 4 gates — Task 2
- ✅ `_log_premover_auto()` — Task 2
- ✅ Shadow mode: evaluate + log + Telegram summary without opening trades — Task 3
- ✅ Enforce mode: evaluate + log + `open_trade()` if gates pass — Task 3
- ✅ `GET/POST /api/paper/premover_mode` — Task 4
- ✅ 8 tests — Tasks 1+2+4

**Placeholder scan:** None. All steps have complete code.

**Type consistency:**
- `evaluate_premover_trade(ticker: str, score: int, pattern_type: str) -> dict` — used in Task 3 as `ev = evaluate_premover_trade(ticker, score, pattern)` ✓
- `_log_premover_auto(ticker, today, pattern, score, mode, ev)` — matches definition signature ✓
- `get_premover_mode() -> str` and `set_premover_mode(mode: str)` — used correctly in endpoints ✓
- `_send_premover_auto_summary(summary_rows, mode, send_telegram)` — `rows` is `list[dict]` with `ticker`, `score`, `would_trade`, `skip_reason` keys — all populated in Task 3 ✓
