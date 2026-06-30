# Forward-Test SHADOW Engine — Scheduler Wiring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the already-built Phase-2 SHADOW position engine actually run in production via one nightly scheduler job, and purge the 204 smoke-test positions so the live cohort starts clean.

**Architecture:** A single fail-soft job `run_forward_test_cycle()` in `scheduler/jobs.py` drives `SignalAdapter.ingest(run_date)` then `ShadowPositionManager.run(run_date)` against `config.DB_PATH`, registered at 18:30 WIB in `scheduler/__init__.py`. A one-time idempotent script `scripts/ft_purge_smoke_cohort.py` clears the smoke cohort. Both `db_path` and `run_date` are injectable for tests.

**Tech Stack:** Python, sqlite3, APScheduler (`CronTrigger`), pytest. Reuses existing `forward_testing/` package and `tests/forward_testing/conftest.py` fixtures.

**Spec:** `docs/superpowers/specs/2026-06-30-forward-test-scheduler-wiring-design.md`

---

## File Structure

- **Create:** `scripts/ft_purge_smoke_cohort.py` — one-time purge of smoke cohort (own responsibility: maintenance cleanup).
- **Modify:** `scheduler/jobs.py` — add `run_forward_test_cycle()` job function (lives with sibling `run_*` jobs).
- **Modify:** `scheduler/__init__.py` — import + register the new job on the cron.
- **Create:** `tests/forward_testing/test_purge_smoke_cohort.py` — purge script test.
- **Create:** `tests/forward_testing/test_scheduler_job.py` — job-level e2e + idempotency test.

Reused as-is: `tests/forward_testing/conftest.py` fixtures `ft_db`, `repo`, helpers `seed_ohlcv`, `seed_signal`.

---

### Task 1: Purge script for the smoke cohort

**Files:**
- Create: `scripts/ft_purge_smoke_cohort.py`
- Test: `tests/forward_testing/test_purge_smoke_cohort.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/forward_testing/test_purge_smoke_cohort.py
"""Purge script clears the shadow cohort and resets affected signals to GENERATED."""
import sqlite3

from forward_testing.adapters.signal_adapter import SignalAdapter
from forward_testing.positions.market_data import MarketDataResolver
from forward_testing.positions.exit_policy import ExitPolicyRegistry
from forward_testing.positions.shadow_manager import ShadowPositionManager
from forward_testing.lifecycle.manager import LifecycleManager
from forward_testing.positions.costs import Costs
from tests.forward_testing.conftest import seed_ohlcv, seed_signal

# 26 flat bars -> ATR 1, plus a D+1 open bar so the position fills.
FLAT = [("2026-06-%02d" % d, 100, 100.5, 99.5, 100, 1000) for d in range(1, 27)]


def _open_one_position(ft_db, repo):
    conn = sqlite3.connect(ft_db)
    seed_signal(conn, "2026-06-26 16:15", "BBCA", "vol_weighted", direction="BUY")
    seed_ohlcv(conn, "BBCA", FLAT + [("2026-06-27", 100, 100.5, 99.5, 100, 1000)])
    conn.commit(); conn.close()
    SignalAdapter(repo, ft_db).ingest("2026-06-26")
    mgr = ShadowPositionManager(repo, MarketDataResolver(ft_db), ExitPolicyRegistry(),
                                LifecycleManager(repo), ft_db, costs=Costs())
    mgr.run("2026-06-26")  # opens BBCA at 2026-06-27


def test_purge_clears_positions_and_resets_state(ft_db, repo):
    from scripts.ft_purge_smoke_cohort import purge_smoke_cohort
    _open_one_position(ft_db, repo)
    assert len(repo.get_open_shadow_positions()) == 1  # precondition

    n_reset = purge_smoke_cohort(ft_db)

    assert n_reset == 1
    assert repo.get_open_shadow_positions() == []
    with sqlite3.connect(ft_db) as c:
        assert c.execute("SELECT COUNT(*) FROM ft_shadow_trade").fetchone()[0] == 0
        assert c.execute("SELECT COUNT(*) FROM ft_shadow_position").fetchone()[0] == 0
        states = [r[0] for r in c.execute("SELECT state FROM ft_signal_state").fetchall()]
    assert states == ["GENERATED"]


def test_purge_is_idempotent_on_empty_db(ft_db, repo):
    from scripts.ft_purge_smoke_cohort import purge_smoke_cohort
    assert purge_smoke_cohort(ft_db) == 0  # nothing to purge -> no error
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && venv/bin/pytest tests/forward_testing/test_purge_smoke_cohort.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.ft_purge_smoke_cohort'` (or ImportError).

- [ ] **Step 3: Write the script**

```python
# scripts/ft_purge_smoke_cohort.py
"""One-time purge of the smoke-test SHADOW cohort.

Deletes every ft_shadow_trade + ft_shadow_position row and resets the lifecycle
state of each affected signal to GENERATED, so a legitimately re-emitted signal
re-opens cleanly on the next nightly cycle. Idempotent. Touches ONLY ft-owned
shadow rows -- never scheduled_signals source data.

GENERATED is a *backward* transition, so this writes ft_signal_state directly
(a one-off maintenance op) rather than via LifecycleManager.transition, which
only permits forward moves.

Usage:
    venv/bin/python -m scripts.ft_purge_smoke_cohort
"""
import sqlite3

from config import DB_PATH


def purge_smoke_cohort(db_path=None):
    """Purge shadow rows and reset affected signals. Returns # of signals reset."""
    db = db_path or DB_PATH
    with sqlite3.connect(db, timeout=30) as c:
        sig_ids = [r[0] for r in c.execute(
            "SELECT DISTINCT signal_id FROM ft_shadow_position").fetchall()]
        c.execute("DELETE FROM ft_shadow_trade")
        c.execute("DELETE FROM ft_shadow_position")
        if sig_ids:
            qmarks = ",".join("?" * len(sig_ids))
            c.execute(
                f"UPDATE ft_signal_state SET state='GENERATED' "
                f"WHERE signal_id IN ({qmarks})",
                sig_ids,
            )
        c.commit()
    return len(sig_ids)


if __name__ == "__main__":
    n = purge_smoke_cohort()
    print(f"Purged shadow cohort; reset {n} signal(s) to GENERATED.")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && venv/bin/pytest tests/forward_testing/test_purge_smoke_cohort.py -v`
Expected: PASS — both tests green.

- [ ] **Step 5: Commit**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001"
git add scripts/ft_purge_smoke_cohort.py tests/forward_testing/test_purge_smoke_cohort.py
git commit -m "feat(forward-test): one-time smoke-cohort purge script

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Nightly cycle job `run_forward_test_cycle()`

**Files:**
- Modify: `scheduler/jobs.py` (append a new `run_*` function; `DB_PATH`, `WIB`, `datetime`, `sqlite3` already imported at top)
- Test: `tests/forward_testing/test_scheduler_job.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/forward_testing/test_scheduler_job.py
"""Job-level e2e: run_forward_test_cycle ingests + opens, and is idempotent."""
import sqlite3

from tests.forward_testing.conftest import seed_ohlcv, seed_signal

FLAT = [("2026-06-%02d" % d, 100, 100.5, 99.5, 100, 1000) for d in range(1, 27)]


def _seed(ft_db):
    conn = sqlite3.connect(ft_db)
    seed_signal(conn, "2026-06-26 16:15", "BBCA", "vol_weighted", direction="BUY")
    seed_ohlcv(conn, "BBCA", FLAT + [("2026-06-27", 100, 100.5, 99.5, 100, 1000)])
    conn.commit(); conn.close()


def test_cycle_ingests_and_opens(ft_db, repo):
    from scheduler.jobs import run_forward_test_cycle
    _seed(ft_db)

    run_forward_test_cycle(db_path=ft_db, run_date="2026-06-26")

    positions = repo.get_open_shadow_positions()
    assert len(positions) == 1
    assert positions[0]["ticker"] == "BBCA"


def test_cycle_is_idempotent(ft_db, repo):
    from scheduler.jobs import run_forward_test_cycle
    _seed(ft_db)

    run_forward_test_cycle(db_path=ft_db, run_date="2026-06-26")
    run_forward_test_cycle(db_path=ft_db, run_date="2026-06-26")  # second run = no-op

    assert len(repo.get_open_shadow_positions()) == 1


def test_cycle_failsoft_on_bad_db(capsys):
    """A broken db_path must not raise -- the scheduler must survive."""
    from scheduler.jobs import run_forward_test_cycle
    run_forward_test_cycle(db_path="/nonexistent/dir/x.db", run_date="2026-06-26")
    out = capsys.readouterr().out
    assert "Forward-test cycle error" in out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && venv/bin/pytest tests/forward_testing/test_scheduler_job.py -v`
Expected: FAIL — `ImportError: cannot import name 'run_forward_test_cycle' from 'scheduler.jobs'`.

- [ ] **Step 3: Add the job function to `scheduler/jobs.py`**

Append at the end of `scheduler/jobs.py`:

```python
def run_forward_test_cycle(db_path=None, run_date=None):
    """Nightly SHADOW forward-test cycle: ingest today's signals + exit-pass open positions.

    Fail-soft: logs and returns on any error so a bad cycle never takes down the
    scheduler. db_path / run_date are injectable for tests; in production both
    default (DB_PATH and today in WIB).
    """
    from forward_testing.storage.db import init_ft_tables
    from forward_testing.storage.repo import FTRepo
    from forward_testing.adapters.signal_adapter import SignalAdapter
    from forward_testing.positions.market_data import MarketDataResolver
    from forward_testing.positions.exit_policy import ExitPolicyRegistry
    from forward_testing.positions.shadow_manager import ShadowPositionManager
    from forward_testing.lifecycle.manager import LifecycleManager
    from forward_testing.positions.costs import Costs

    db = db_path or DB_PATH
    rd = run_date or datetime.now(WIB).strftime("%Y-%m-%d")
    try:
        init_ft_tables(db)
        repo = FTRepo(db)

        def _trade_count():
            with sqlite3.connect(db, timeout=30) as c:
                return c.execute("SELECT COUNT(*) FROM ft_shadow_trade").fetchone()[0]

        open_before = len(repo.get_open_shadow_positions())
        trades_before = _trade_count()

        n_ingested = SignalAdapter(repo, db).ingest(rd)
        mgr = ShadowPositionManager(
            repo, MarketDataResolver(db), ExitPolicyRegistry(),
            LifecycleManager(repo), db, costs=Costs(),
        )
        mgr.run(rd)

        open_after = len(repo.get_open_shadow_positions())
        closed = _trade_count() - trades_before
        opened = (open_after - open_before) + closed
        print(f"[{datetime.now(WIB).strftime('%H:%M')}] Forward-test cycle {rd}: "
              f"ingested={n_ingested} opened={opened} closed={closed} open_now={open_after}")
    except Exception as e:
        print(f"[scheduler] Forward-test cycle error: {e}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && venv/bin/pytest tests/forward_testing/test_scheduler_job.py -v`
Expected: PASS — all three tests green.

- [ ] **Step 5: Commit**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001"
git add scheduler/jobs.py tests/forward_testing/test_scheduler_job.py
git commit -m "feat(forward-test): nightly run_forward_test_cycle job

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Register the job on the 18:30 cron

**Files:**
- Modify: `scheduler/__init__.py` (import block near lines 44-54; registration near line 179; banner near line 192)

This task has no unit test (registering an APScheduler cron job is verified by the existing suite staying green plus a grep assertion — building the live scheduler in a test would start background threads).

- [ ] **Step 1: Add the import**

In `scheduler/__init__.py`, find the job-import block that already imports `run_eod_trade_plan` (around line 54) and add `run_forward_test_cycle` to it. Example — change:

```python
    run_premarket_firm_scan,
    run_eod_trade_plan,
```

to:

```python
    run_premarket_firm_scan,
    run_eod_trade_plan,
    run_forward_test_cycle,
```

- [ ] **Step 2: Register the cron job**

In `scheduler/__init__.py`, immediately after the `eod_trade_plan` registration block (ends ~line 181, before `scheduler.start()`), add:

```python
    # Forward-test SHADOW cycle — 18:30 WIB (after 16:00 close, 16:05 flow fetch,
    # 18:00 VPIN batch). Ingests today's scheduled_signals into the ft model and
    # runs the open + exit passes so the shadow-position population grows daily.
    scheduler.add_job(run_forward_test_cycle, CronTrigger(
        day_of_week="mon-fri", hour=18, minute=30, timezone=WIB),
        id="forward_test_cycle", name="Forward-Test Cycle 18:30")
```

- [ ] **Step 3: Add a banner line**

In the startup banner print block (around line 192, after the `EOD TRADE PLAN` line), add:

```python
    print("  🧪 FORWARD-TEST CYCLE: 18:30 (ingest signals → open/exit shadow positions)")
```

- [ ] **Step 4: Verify registration + import health**

Run:
```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001"
grep -n "forward_test_cycle" scheduler/__init__.py
venv/bin/python -c "import scheduler"
```
Expected: grep shows the import, the `add_job(... id=\"forward_test_cycle\" ...)` line, and the banner; `import scheduler` exits 0 with no traceback.

- [ ] **Step 5: Commit**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001"
git add scheduler/__init__.py
git commit -m "feat(forward-test): register nightly cycle at 18:30 WIB

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Full ft suite regression + live data-availability check

**Files:** none (verification only)

- [ ] **Step 1: Run the full forward_testing suite**

Run: `cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && venv/bin/pytest tests/forward_testing/ -q`
Expected: all green (previously 83 ft tests + the new purge & job tests). If any fail, fix before proceeding.

- [ ] **Step 2: Verify the 18:30 data-availability assumption against the prod DB**

The exit pass evaluates today's open positions against **today's daily OHLCV bar**. Confirm that bar lands in `walkforward.db` before 18:30. Run after 18:00 on a trading day:

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001"
venv/bin/python -c "import sqlite3; from config import DB_PATH; from datetime import datetime; import pytz; \
d=datetime.now(pytz.timezone('Asia/Jakarta')).strftime('%Y-%m-%d'); \
c=sqlite3.connect(DB_PATH); \
print('bars for', d, '=', c.execute('SELECT COUNT(*) FROM ohlcv WHERE date=?',(d,)).fetchone()[0])"
```

Expected: a non-zero count (today's bars present). **If zero:** today's exits would defer a day — change the `CronTrigger` slot to later in the evening, or switch to the next-morning variant (`run_date` = previous trading day, job at ~08:15 WIB). Record the finding either way.

- [ ] **Step 3: Run the one-time purge against the prod DB**

Only after Steps 1-2 pass:

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001"
venv/bin/python -m scripts.ft_purge_smoke_cohort
```
Expected: `Purged shadow cohort; reset N signal(s) to GENERATED.` (N ≈ 204).

- [ ] **Step 4: Restart the app so the new job registers**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && ./start.sh
```
Then confirm the banner shows `FORWARD-TEST CYCLE: 18:30` (check `/tmp/app5001.log` or the start.sh output).

- [ ] **Step 5: Confirm the first live cycle**

After the first 18:30 run, check the log for the summary line:
`Forward-test cycle YYYY-MM-DD: ingested=N opened=Δ closed=Δ open_now=K`
and confirm the numbers are sane (cohort starts near zero post-purge and grows). No commit — this is operational verification.

---

## Notes for the implementer

- Always invoke pytest/python via `venv/bin/` — the system `python3` lacks this project's deps (documented gotcha).
- `repo.get_open_shadow_positions()` returns a list of dict-like rows keyed by column name (`pos["ticker"]`, `pos["entry_date"]`).
- Opens fill at the **D+1** bar (`next_open` after `signal_date`), so a signal ingested for date X needs an OHLCV bar dated > X to open. The flat 26-bar history (`range(1, 27)`) gives ATR=1 so `atr14` is non-None and the position can open.
- The job and purge script both default to `config.DB_PATH` (`data/walkforward.db`) and accept an injected path for tests.
