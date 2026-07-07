# Phase 3D — Scheduler Dead-Man's-Switch (item 3.7) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** If the APScheduler (or the whole app process) dies, an *independent* watchdog alarms within ~15 minutes — closing the last Phase-3 chaos-drill exit criterion ("kill the scheduler mid-job → alarm, never silently stop trading").

**Architecture:** Two halves that must live in different processes. (1) An **in-app heartbeat writer**: a 5-minute APScheduler job that writes an ISO timestamp to `logs/scheduler_heartbeat.txt`. It fires 24/7 independent of market hours, so a stale file means the scheduler thread/process is actually dead — not merely idle overnight. (2) An **external watchdog**: a standalone `scripts/check_scheduler_heartbeat.py` invoked by the user's **system crontab** (the existing external-trigger mechanism — auto_token, stockbit_fetcher already run there). It reads the file and Telegram-alarms if the beat is stale/missing. The checker must be external because an in-app checker dies with the scheduler it watches. A pure `heartbeat_status(last_iso, now_dt, stale_after_min)` classifier is the TDD core shared by both. File-based (not DB) to avoid adding lock surface — the opposite of what Phase 3C just cleaned up.

**Tech Stack:** Python 3 stdlib (`datetime`, `pathlib`), APScheduler `CronTrigger` (already imported in `scheduler/__init__.py`), `utils.telegram.send_telegram`, pytest.

---

## File Structure

- **Create** `engine/heartbeat.py` — pure `heartbeat_status()` classifier + `write_heartbeat()` / `read_heartbeat()` file IO.
- **Create** `tests/test_heartbeat.py` — classifier + roundtrip tests.
- **Create** `scripts/check_scheduler_heartbeat.py` — standalone external watchdog (reads file, alarms if stale). Also importable so its decision logic is testable.
- **Create** `tests/test_check_heartbeat_script.py` — watchdog decision/alarm test.
- **Modify** `scheduler/jobs.py` — add `run_scheduler_heartbeat()` job function.
- **Modify** `scheduler/__init__.py` — register the heartbeat job (`CronTrigger(minute="*/5")`).

**Heartbeat file:** `logs/scheduler_heartbeat.txt`, single line, ISO-8601 UTC (`2026-07-07T01:57:00+00:00`). `logs/` already exists (crontab writes there).

**Status contract:** `heartbeat_status(last_iso, now_dt, stale_after_min=15)` returns one of `"FRESH"`, `"STALE"`, `"MISSING"` (MISSING when `last_iso` is None/unparseable).

**Crontab line (provided at deploy, NOT auto-installed):**
```
*/10 * * * * cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && venv/bin/python3 scripts/check_scheduler_heartbeat.py >> logs/heartbeat_check.log 2>&1
```

---

### Task 1: Pure heartbeat core

**Files:**
- Create: `engine/heartbeat.py`
- Test: `tests/test_heartbeat.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_heartbeat.py
"""Tests for engine.heartbeat — the scheduler dead-man's-switch core."""
from datetime import datetime, timedelta, timezone

import engine.heartbeat as hb


def _now():
    return datetime(2026, 7, 7, 12, 0, 0, tzinfo=timezone.utc)


def test_status_fresh_within_window():
    last = (_now() - timedelta(minutes=5)).isoformat()
    assert hb.heartbeat_status(last, _now(), stale_after_min=15) == "FRESH"


def test_status_stale_beyond_window():
    last = (_now() - timedelta(minutes=20)).isoformat()
    assert hb.heartbeat_status(last, _now(), stale_after_min=15) == "STALE"


def test_status_missing_when_none():
    assert hb.heartbeat_status(None, _now(), stale_after_min=15) == "MISSING"


def test_status_missing_when_unparseable():
    assert hb.heartbeat_status("not-a-timestamp", _now(), stale_after_min=15) == "MISSING"


def test_status_exact_boundary_is_fresh():
    last = (_now() - timedelta(minutes=15)).isoformat()
    # exactly at threshold counts as fresh (strictly-greater is stale)
    assert hb.heartbeat_status(last, _now(), stale_after_min=15) == "FRESH"


def test_write_then_read_roundtrip(tmp_path):
    p = str(tmp_path / "hb.txt")
    hb.write_heartbeat(p, _now())
    assert hb.read_heartbeat(p) == _now().isoformat()


def test_read_missing_file_returns_none(tmp_path):
    assert hb.read_heartbeat(str(tmp_path / "nope.txt")) is None
```

- [ ] **Step 2: Run to verify failure**

Run: `./venv/bin/python -m pytest tests/test_heartbeat.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'engine.heartbeat'`

- [ ] **Step 3: Implement**

```python
# engine/heartbeat.py
"""Scheduler dead-man's-switch core (audit item 3.7).

The in-app writer stamps ``logs/scheduler_heartbeat.txt`` every 5 minutes; an
external watchdog (scripts/check_scheduler_heartbeat.py, run from crontab)
reads it and alarms when stale. This module is the pure, side-effect-light
core shared by both — no Telegram, no scheduler imports.
"""
from datetime import datetime
from pathlib import Path


def heartbeat_status(last_iso, now_dt, stale_after_min=15):
    """Classify heartbeat freshness → 'FRESH' | 'STALE' | 'MISSING'.

    MISSING: no/unparseable timestamp. STALE: older than stale_after_min.
    The threshold boundary counts as FRESH (only strictly-older is STALE).
    """
    if not last_iso:
        return "MISSING"
    try:
        last = datetime.fromisoformat(last_iso)
    except (ValueError, TypeError):
        return "MISSING"
    age_min = (now_dt - last).total_seconds() / 60.0
    return "STALE" if age_min > stale_after_min else "FRESH"


def write_heartbeat(path, now_dt):
    """Atomically stamp the heartbeat file with an ISO-8601 timestamp."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(now_dt.isoformat(), encoding="utf-8")
    tmp.replace(p)  # atomic on POSIX


def read_heartbeat(path):
    """Return the stored ISO string, or None if the file is absent/empty."""
    try:
        txt = Path(path).read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None
    return txt or None
```

- [ ] **Step 4: Run to verify pass**

Run: `./venv/bin/python -m pytest tests/test_heartbeat.py -q`
Expected: PASS (7 passed)

- [ ] **Step 5: Commit**

```bash
git add engine/heartbeat.py tests/test_heartbeat.py
git commit -m "feat(ops): scheduler heartbeat core — status classifier + file IO (Phase 3D)"
```

---

### Task 2: In-app heartbeat writer job

**Files:**
- Modify: `scheduler/jobs.py` (add job fn), `scheduler/__init__.py` (register)
- Test: `tests/test_heartbeat_job.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_heartbeat_job.py
"""The in-app heartbeat job must stamp a fresh, parseable timestamp."""
from datetime import datetime, timezone

import engine.heartbeat as hb
from scheduler.jobs import run_scheduler_heartbeat, HEARTBEAT_PATH


def test_run_scheduler_heartbeat_writes_fresh(tmp_path, monkeypatch):
    p = str(tmp_path / "hb.txt")
    monkeypatch.setattr("scheduler.jobs.HEARTBEAT_PATH", p)
    run_scheduler_heartbeat()
    last = hb.read_heartbeat(p)
    assert last is not None
    assert hb.heartbeat_status(last, datetime.now(timezone.utc)) == "FRESH"
```

- [ ] **Step 2: Run to verify failure**

Run: `./venv/bin/python -m pytest tests/test_heartbeat_job.py -q`
Expected: FAIL — `ImportError: cannot import name 'run_scheduler_heartbeat'`

- [ ] **Step 3: Implement in scheduler/jobs.py**

Near the other job functions, add (and an import for heartbeat at the top with the other `from ...` lines):

```python
from engine.heartbeat import write_heartbeat  # noqa: E402

HEARTBEAT_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                              "logs", "scheduler_heartbeat.txt")


def run_scheduler_heartbeat():
    """Dead-man's-switch writer: stamp the heartbeat file (audit 3.7).

    Fires every 5 min regardless of market hours, so a stale file means the
    scheduler is actually dead — the external watchdog
    (scripts/check_scheduler_heartbeat.py) alarms on staleness.
    """
    from datetime import datetime, timezone
    try:
        write_heartbeat(HEARTBEAT_PATH, datetime.now(timezone.utc))
    except Exception as e:  # never let the heartbeat crash the scheduler
        logging.warning(f"[heartbeat] write failed: {e}")
```

(`os` and `logging` are already imported in jobs.py.)

- [ ] **Step 4: Register in scheduler/__init__.py**

After the last `scheduler.add_job(...)` and before `scheduler.start()`, add (importing `run_scheduler_heartbeat` alongside the other job imports at the top of the file):

```python
    scheduler.add_job(run_scheduler_heartbeat, CronTrigger(
        minute="*/5", timezone=WIB), id="scheduler_heartbeat",
        replace_existing=True)
    print("  💓 SCHEDULER HEARTBEAT: every 5 min (dead-man's-switch)")
```

- [ ] **Step 5: Run tests**

Run: `./venv/bin/python -m pytest tests/test_heartbeat_job.py -q && ./venv/bin/python -c "import scheduler"`
Expected: PASS + import OK

- [ ] **Step 6: Commit**

```bash
git add scheduler/jobs.py scheduler/__init__.py tests/test_heartbeat_job.py
git commit -m "feat(ops): register 5-min in-app heartbeat writer job (Phase 3D)"
```

---

### Task 3: External watchdog script

**Files:**
- Create: `scripts/check_scheduler_heartbeat.py`
- Test: `tests/test_check_heartbeat_script.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_check_heartbeat_script.py
"""The external watchdog alarms on STALE/MISSING, stays silent on FRESH."""
from datetime import datetime, timedelta, timezone

import scripts.check_scheduler_heartbeat as chk


def _write(path, dt):
    from engine.heartbeat import write_heartbeat
    write_heartbeat(path, dt)


def test_fresh_does_not_alarm(tmp_path, monkeypatch):
    alarms = []
    monkeypatch.setattr(chk, "send_telegram", lambda m: alarms.append(m))
    p = str(tmp_path / "hb.txt")
    _write(p, datetime.now(timezone.utc) - timedelta(minutes=3))
    rc = chk.check(path=p, stale_after_min=15)
    assert rc == 0
    assert alarms == []


def test_stale_alarms(tmp_path, monkeypatch):
    alarms = []
    monkeypatch.setattr(chk, "send_telegram", lambda m: alarms.append(m))
    p = str(tmp_path / "hb.txt")
    _write(p, datetime.now(timezone.utc) - timedelta(minutes=40))
    rc = chk.check(path=p, stale_after_min=15)
    assert rc == 1
    assert len(alarms) == 1
    assert "STALE" in alarms[0] or "heartbeat" in alarms[0].lower()


def test_missing_alarms(tmp_path, monkeypatch):
    alarms = []
    monkeypatch.setattr(chk, "send_telegram", lambda m: alarms.append(m))
    rc = chk.check(path=str(tmp_path / "nope.txt"), stale_after_min=15)
    assert rc == 1
    assert len(alarms) == 1
```

- [ ] **Step 2: Run to verify failure**

Run: `./venv/bin/python -m pytest tests/test_check_heartbeat_script.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.check_scheduler_heartbeat'`

(If `scripts/` lacks `__init__.py`, the import will still work via path; but the test imports `scripts.check_scheduler_heartbeat` — verify `scripts/__init__.py` exists, and if not, `Create: scripts/__init__.py` empty as part of this task.)

- [ ] **Step 3: Implement**

```python
#!/usr/bin/env python3
"""External dead-man's-switch for the APScheduler (audit item 3.7).

Run from crontab every ~10 min:
    */10 * * * * cd "<repo>" && venv/bin/python3 scripts/check_scheduler_heartbeat.py >> logs/heartbeat_check.log 2>&1

Reads logs/scheduler_heartbeat.txt (stamped every 5 min by the in-app writer)
and Telegram-alarms when the beat is STALE or MISSING. Independent of the app
process on purpose — if the scheduler dies, this still runs.
"""
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.heartbeat import heartbeat_status, read_heartbeat  # noqa: E402
from utils.telegram import send_telegram  # noqa: E402

DEFAULT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "logs", "scheduler_heartbeat.txt")


def check(path=DEFAULT_PATH, stale_after_min=15):
    """Return 0 if FRESH, 1 (and alarm) if STALE/MISSING."""
    last = read_heartbeat(path)
    status = heartbeat_status(last, datetime.now(timezone.utc), stale_after_min)
    if status == "FRESH":
        return 0
    msg = (f"🔴 SCHEDULER HEARTBEAT {status} — last beat: {last or 'never'}. "
           f"APScheduler/app may be dead; trades/reports NOT running. "
           f"Restart via ./start.sh.")
    try:
        send_telegram(msg)
    except Exception:
        pass  # cron log still captures the print below
    print(msg)
    return 1


if __name__ == "__main__":
    sys.exit(check())
```

- [ ] **Step 4: Run tests**

Run: `./venv/bin/python -m pytest tests/test_check_heartbeat_script.py -q`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add scripts/check_scheduler_heartbeat.py tests/test_check_heartbeat_script.py
# include scripts/__init__.py if it had to be created
git commit -m "feat(ops): external scheduler-heartbeat watchdog script (Phase 3D)"
```

---

### Task 4: Full-suite regression + finish

- [ ] **Step 1: Full suite**

Run: `./venv/bin/python -m pytest -q`
Expected: ≥1054 passed + new tests (≈1067), 3 skipped, no new failures.

- [ ] **Step 2: Manual end-to-end smoke (local, no restart)**

```bash
./venv/bin/python -c "from scheduler.jobs import run_scheduler_heartbeat; run_scheduler_heartbeat(); print(open('logs/scheduler_heartbeat.txt').read())"
./venv/bin/python scripts/check_scheduler_heartbeat.py; echo "rc=$?"   # rc=0, fresh
```

- [ ] **Step 3: Finish the branch**

Use **superpowers:finishing-a-development-branch**: push, PR to `master`, wait CI, manual merge, merge master into prod branch `feat/tfb-context-filter`, restart app in a quiet slot (registers the heartbeat job), verify HTTP 200 + `logs/scheduler_heartbeat.txt` gets stamped within 5 min.

- [ ] **Step 4: Crontab (CONFIRM WITH USER — do not auto-install)**

Present this line and ask the user to add it (or confirm appending it via `crontab`):
```
*/10 * * * * cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && venv/bin/python3 scripts/check_scheduler_heartbeat.py >> logs/heartbeat_check.log 2>&1
```
Note the existing crontab has some entries under the no-space path `/home/tjiesar/idx-walkforward-5001` and one under `/home/tjiesar/10 Projects/...` — use the space path (the live checkout) for this entry.

---

## Self-Review Notes

- **Spec coverage:** 3.7 dead-man's-switch = Tasks 1–3 (writer + external checker + pure core); closes the "kill the scheduler → alarm" chaos-drill. Log unification (print→logging) from the audit's 3.7 bundle is **explicitly deferred** (large, low-correctness-value; noted in PR + memory).
- **Placeholder scan:** every step has real code; crontab line is literal.
- **Type consistency:** `heartbeat_status(last_iso, now_dt, stale_after_min=15) -> str`, `write_heartbeat(path, now_dt)`, `read_heartbeat(path) -> str|None`, `check(path, stale_after_min) -> int` used consistently across job, script, and tests.
- **Why file not DB:** avoids adding lock/connection surface right after Phase 3C consolidated it; heartbeat is ops-metadata, not trading state.
- **Independence invariant:** the checker runs from crontab, never from APScheduler — otherwise it dies with what it watches. This is the crux; the crontab step is required for the drill to actually pass.
