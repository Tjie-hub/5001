# Phase 3C — DB Centralization (item 3.3) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One hardened `data.db.connect()` (timeout=30 + `busy_timeout=30000` + WAL) used by every hot production module, so "database is locked" can't recur site-by-site.

**Architecture:** History lesson driving this: commit b7431db (2026-06-19) did exactly this centralization but was **never merged** (orphan branch `fix/news-fetch-premarket-overnight`) — so locks kept recurring and got spot-fixed one at a time (WF refresh, paper summary, premover). This plan re-implements it fresh on current master: (1) `data/db.py` gains `connect(path=None, timeout=30)` — a **drop-in** for `sqlite3.connect(...)` (no row_factory, same return type, works in `with ... as conn:` transaction form) that adds timeout + pragmas; `get_db()` delegates to it and keeps its `sqlite3.Row` contract. (2) A grep-based hygiene test pins the invariant: zero raw `sqlite3.connect(` in the named hot modules — written first, failing with ~77 hits, driven to green by mechanical migration. Deferred out of scope (separate risk profile, noted for later): vpin-batch chunked commits and connection-per-loop elimination inside scans.

**Tech Stack:** Python 3 stdlib `sqlite3`, pytest. No new dependencies.

---

## File Structure

- **Modify** `data/db.py` — add `connect()`; harden `get_db()` via delegation.
- **Create** `tests/test_db_connect.py` — behavior tests for the helper.
- **Create** `tests/test_db_centralization.py` — hygiene test (source scan of hot modules).
- **Modify (mechanical migration)** hot modules, 77 sites total:
  - `scheduler/scanner.py` (20), `scheduler/jobs.py` (17), `scheduler/reports.py` (5), `scheduler/utils.py` (3)
  - `monitor.py` (9), `news_filter.py` (6), `flow_filter.py` (5), `paper_trade.py` (2), `app.py` (2)
  - `engine/premover_detector.py` (4), `stockbit_fetcher.py` (2), `screener/idx_scraper.py` (2)

**Migration pattern (identical everywhere):**

```python
# module top, with the other imports:
from data.db import connect as db_connect

# then each site:
sqlite3.connect(DB_PATH)                  → db_connect(DB_PATH)
sqlite3.connect(db_path, timeout=30)      → db_connect(db_path)          # timeout now default
with sqlite3.connect(db) as conn:         → with db_connect(db) as conn: # same txn semantics
```

Where a site was previously spot-fixed with inline pragmas (e.g. `engine/premover_detector.py:402-405` sets WAL + busy_timeout after connecting), **delete the now-redundant inline pragma lines** — the helper owns them. Do NOT remove `import sqlite3` from modules that still use `sqlite3.Row`, `sqlite3.OperationalError`, etc.

---

### Task 1: Hardened `connect()` in data/db.py

**Files:**
- Modify: `data/db.py:1-18`
- Test: `tests/test_db_connect.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_db_connect.py
"""Tests for data.db.connect() — the one hardened SQLite entry point."""
import sqlite3

import pytest

import data.db as ddb


def test_connect_sets_busy_timeout_and_wal(tmp_path):
    db = str(tmp_path / "t.db")
    conn = ddb.connect(db)
    try:
        assert conn.execute("PRAGMA busy_timeout").fetchone()[0] == 30000
        assert conn.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
    finally:
        conn.close()


def test_connect_is_dropin_no_row_factory(tmp_path):
    """Drop-in for sqlite3.connect: plain tuples, usable as txn context manager."""
    db = str(tmp_path / "t.db")
    with ddb.connect(db) as conn:
        conn.execute("CREATE TABLE x (a, b)")
        conn.execute("INSERT INTO x VALUES (1, 2)")
    conn.close()
    conn2 = ddb.connect(db)
    try:
        row = conn2.execute("SELECT a, b FROM x").fetchone()
        assert row == (1, 2)          # tuple equality — Row would fail this
        assert type(row) is tuple
    finally:
        conn2.close()


def test_connect_defaults_to_main_db_path(monkeypatch, tmp_path):
    db = str(tmp_path / "main.db")
    monkeypatch.setattr(ddb, "DB_PATH", db)
    conn = ddb.connect()
    try:
        conn.execute("CREATE TABLE IF NOT EXISTS y (a)")
    finally:
        conn.close()
    assert (tmp_path / "main.db").exists()


def test_connect_survives_pragma_failure_on_memory_db():
    """Pragmas are best-effort — :memory: / exotic paths must not raise."""
    conn = ddb.connect(":memory:")
    try:
        conn.execute("SELECT 1")
    finally:
        conn.close()


def test_get_db_now_hardened(monkeypatch, tmp_path):
    """get_db() keeps its Row contract AND gains the pragmas."""
    db = str(tmp_path / "main.db")
    monkeypatch.setattr(ddb, "DB_PATH", db)
    conn = ddb.get_db()
    try:
        assert conn.row_factory is sqlite3.Row
        assert conn.execute("PRAGMA busy_timeout").fetchone()[0] == 30000
    finally:
        conn.close()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `./venv/bin/python -m pytest tests/test_db_connect.py -q`
Expected: FAIL — `AttributeError: module 'data.db' has no attribute 'connect'` (and get_db pragma assert fails).

- [ ] **Step 3: Implement in data/db.py**

Replace the current top of `data/db.py` (imports, `DB_PATH`, `get_db`) with:

```python
import sqlite3
import os
from contextlib import contextmanager

DB_PATH = os.getenv('DB_PATH', os.path.join(os.path.dirname(__file__), 'walkforward.db'))


def connect(path=None, timeout=30):
    """The one SQLite entry point: timeout + busy_timeout + WAL.

    Drop-in replacement for ``sqlite3.connect(path)`` — no row_factory, same
    return type, same ``with conn:`` transaction semantics. Every production
    connection to any of our DBs should come through here so lock-hardening
    lives in exactly one place (audit item 3.3; the 2026-06 lock bugs were all
    missing-pragma variants of the same defect).
    """
    conn = sqlite3.connect(path or DB_PATH, timeout=timeout)
    try:
        conn.execute("PRAGMA busy_timeout=30000")
        conn.execute("PRAGMA journal_mode=WAL")
    except sqlite3.OperationalError:
        pass  # :memory:/read-only paths may reject WAL — timeout still applies
    return conn


def get_db():
    conn = connect()
    conn.row_factory = sqlite3.Row
    return conn
```

(Leave `get_db_context`, `init_db`, and everything below unchanged.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `./venv/bin/python -m pytest tests/test_db_connect.py -q`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add data/db.py tests/test_db_connect.py
git commit -m "feat(db): hardened data.db.connect() — timeout + busy_timeout + WAL in one place (Phase 3C)"
```

---

### Task 2: Hygiene test — the migration driver

**Files:**
- Create: `tests/test_db_centralization.py`

- [ ] **Step 1: Write the (failing) hygiene test**

```python
# tests/test_db_centralization.py
"""Guard: hot production modules must not open raw sqlite3 connections.

Every connection must come through data.db.connect()/get_db() so
timeout/busy_timeout/WAL hardening lives in one place (audit item 3.3).
If this test fails, replace `sqlite3.connect(...)` with
`from data.db import connect as db_connect` + `db_connect(...)`.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

HOT_MODULES = [
    "scheduler/scanner.py",
    "scheduler/jobs.py",
    "scheduler/reports.py",
    "scheduler/utils.py",
    "monitor.py",
    "news_filter.py",
    "flow_filter.py",
    "paper_trade.py",
    "app.py",
    "engine/premover_detector.py",
    "stockbit_fetcher.py",
    "screener/idx_scraper.py",
]

RAW_CONNECT = re.compile(r"sqlite3\s*\.\s*connect\s*\(")


def test_no_raw_sqlite_connect_in_hot_modules():
    offenders = []
    for rel in HOT_MODULES:
        src = (ROOT / rel).read_text(encoding="utf-8")
        for i, line in enumerate(src.splitlines(), 1):
            if RAW_CONNECT.search(line):
                offenders.append(f"{rel}:{i}: {line.strip()}")
    assert not offenders, (
        "Raw sqlite3.connect() in hot modules — use data.db.connect():\n"
        + "\n".join(offenders)
    )
```

- [ ] **Step 2: Run it to verify it fails with ~77 offenders**

Run: `./venv/bin/python -m pytest tests/test_db_centralization.py -q`
Expected: FAIL, listing every raw site (≈77 lines).

- [ ] **Step 3: Commit the test (red is fine — it goes green in Task 5)**

Do NOT commit yet if the project CI would run on this commit alone; instead hold this file staged-only until Task 5 makes it green, OR commit at the end of Task 5 together with the last migration. **Decision: commit it together with Task 5's final migration** so every commit on the branch is green. For now just leave the file in the working tree.

---

### Task 3: Migrate scheduler/ (45 sites)

**Files:**
- Modify: `scheduler/scanner.py`, `scheduler/jobs.py`, `scheduler/reports.py`, `scheduler/utils.py`

- [ ] **Step 1: Add the import to each file**

In each of the four files, next to the existing imports:

```python
from data.db import connect as db_connect
```

(For `scheduler/jobs.py` note it already does `from utils.telegram import send_telegram` at line ~14 — put the new import in that block. Check each file for an existing `from data.db import ...` line and extend it instead of duplicating.)

- [ ] **Step 2: Replace every site mechanically**

For each file, replace per the pattern table (keep argument expressions verbatim, drop explicit `timeout=` args since 30 is now the default):

```
sqlite3.connect(DB_PATH)             → db_connect(DB_PATH)
sqlite3.connect(DB_PATH, timeout=30) → db_connect(DB_PATH)
sqlite3.connect(DB_PATH, timeout=5)  → db_connect(DB_PATH, timeout=5)
sqlite3.connect(db_path)/(db)/(_DB_PATH)/(WALKFORWARD_DB) → db_connect(same-arg)
with sqlite3.connect(X) as c:        → with db_connect(X) as c:
```

Then delete any now-redundant inline hardening immediately after a migrated site (lines like `conn.execute("PRAGMA busy_timeout=30000")` / `journal_mode=WAL` that exist only as previous spot-fixes — e.g. in `refresh_wf_scores` in jobs.py). Keep `import sqlite3` where the module still references `sqlite3.Row` / exceptions.

Verify per file: `grep -c "sqlite3\.connect(" scheduler/scanner.py` → `0` (repeat for all four).

- [ ] **Step 3: Run the scheduler-related tests**

Run: `./venv/bin/python -m pytest tests/scheduler/ tests/test_scheduler_firm_hook.py tests/agent_firm/ tests/test_pipeline_health_jobs.py tests/test_eod_purge.py -q`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add scheduler/
git commit -m "refactor(db): scheduler modules use data.db.connect (45 sites) (Phase 3C)"
```

---

### Task 4: Migrate the trade/report path (24 sites)

**Files:**
- Modify: `monitor.py` (9), `news_filter.py` (6), `flow_filter.py` (5), `paper_trade.py` (2), `app.py` (2)

- [ ] **Step 1: Same import + same mechanical replacement in each file**

Same pattern as Task 3. Watch for: `paper_trade.py` and `monitor.py` may set `row_factory` right after connecting — keep those lines (helper doesn't set it). `app.py` sites may be inside route handlers — pattern unchanged.

Verify per file: `grep -c "sqlite3\.connect(" monitor.py news_filter.py flow_filter.py paper_trade.py app.py` → all `0`.

- [ ] **Step 2: Run the affected tests**

Run: `./venv/bin/python -m pytest tests/test_monitor_kernel_exits.py tests/test_paper_trade_sizing.py tests/test_conformance.py tests/test_health_endpoint.py tests/test_catalyst.py -q`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add monitor.py news_filter.py flow_filter.py paper_trade.py app.py
git commit -m "refactor(db): trade/report path uses data.db.connect (24 sites) (Phase 3C)"
```

---

### Task 5: Migrate the remaining hot modules (8 sites) + hygiene test green

**Files:**
- Modify: `engine/premover_detector.py` (4), `stockbit_fetcher.py` (2), `screener/idx_scraper.py` (2)
- Add: `tests/test_db_centralization.py` (from Task 2)

- [ ] **Step 1: Migrate the three files**

Same pattern. In `engine/premover_detector.py`, the c49e7f1 spot-fix (`timeout=30` + WAL + busy_timeout pragmas around line 402) collapses to a bare `db_connect(db_path)` — delete the two pragma lines.

- [ ] **Step 2: Run the hygiene test — must now be green**

Run: `./venv/bin/python -m pytest tests/test_db_centralization.py tests/test_premover_auto_trade.py tests/test_signal_checkers.py -q`
Expected: PASS (0 offenders)

- [ ] **Step 3: Commit**

```bash
git add engine/premover_detector.py stockbit_fetcher.py screener/idx_scraper.py tests/test_db_centralization.py
git commit -m "refactor(db): remaining hot modules + hygiene guard test (Phase 3C, closes 3.3 core)"
```

---

### Task 6: Full-suite regression + finish

- [ ] **Step 1: Full suite**

Run: `./venv/bin/python -m pytest -q`
Expected: ≥1048 passed (current baseline) + the new db tests, 3 skipped, no new failures.

- [ ] **Step 2: Finish the branch**

Use **superpowers:finishing-a-development-branch**: push, PR to `master`, wait CI, manual merge, merge master into prod branch `feat/tfb-context-filter`, restart app via `./start.sh` in a quiet slot, verify HTTP 200 + clean log.

PR body notes: re-implements the never-merged b7431db centralization on current master; hygiene test pins the invariant; deferred: vpin chunked commits + connection-per-loop (tracked as 3.3 follow-up).

---

## Self-Review Notes

- **Spec coverage:** "one connect() with WAL + busy_timeout used everywhere" → Tasks 1–5 for all hot modules; enforced by hygiene test. The 3.3 sub-items about vpin chunked commits / connection-per-loop are explicitly deferred (stated in PR + memory).
- **Placeholder scan:** migration steps are mechanical by design — pattern table + per-file grep verification is the complete instruction; no TBDs.
- **Type consistency:** `connect(path=None, timeout=30)` everywhere; `db_connect` alias used consistently in migrated modules; `get_db()` contract (Row factory) unchanged for existing callers.
- **Risk notes:** WAL is already the de-facto journal mode on walkforward.db (screener/db.py + ft set it), so the pragma is idempotent; `with conn:` semantics identical (txn scope, not close); pragma failure guarded for `:memory:`.
