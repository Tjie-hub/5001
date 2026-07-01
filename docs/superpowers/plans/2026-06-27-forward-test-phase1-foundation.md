# Forward Testing — Phase 1 (Foundation) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land the forward-testing foundation — a versioned `ft_*` schema in `walkforward.db`, a compute-then-write `FTRepo`, an 8-state signal lifecycle state machine, and an adapter that ingests `scheduled_signals` into the forward-test signal model — so that a day's screener output can be persisted with a fully auditable lifecycle.

**Architecture:** New top-level `forward_testing/` package (per the blueprint §11). Storage lives in the existing `walkforward.db` (SQLite/WAL, `busy_timeout=30s`) via dependency-injected `db_path` so tests use temp DBs. Every write is a short transaction on its own connection (compute-then-write — the repo's hard-won DB-lock discipline). The lifecycle is a forward-only guarded state machine; illegal transitions are rejected and logged, re-runs are idempotent.

**Tech Stack:** Python 3, SQLite (stdlib `sqlite3`), pytest (`asyncio_mode=auto`, `testpaths=tests`). No new dependencies.

**Blueprint reference:** `docs/Forward_Testing_Architecture.md` — §2 (modules), §3 (lifecycle), §4 (DB), §5 (daily flow), §11 (project structure).

---

## Scope of Phase 1 (and what is deliberately deferred)

**In scope:** `ft_strategy_version`, `ft_signal`, `ft_signal_state`, `ft_transition_log`, `ft_run`, `ft_run_log` tables; `FTRepo` DAOs; `SignalState` enum + legal transitions; `LifecycleManager`; `SignalAdapter` (ingest `scheduled_signals` → `SHADOW` track at `GENERATED`); startup wiring; full test suite.

**Deferred to later phases (do NOT build now):** positions/fills/trades/marks (Phase 2–3), `ExitPolicy` (Phase 2), ranker/sizer/corporate-actions (Phase 3), performance/scoreboard/feedback/AI (Phase 4–6), the daily-flow scheduler + reports (Phase 7). `strategy_version_id`/`config_hash` on `ft_signal` are nullable and left unset in Phase 1 (version resolution needs the strategy registry, wired in Phase 2). The `PORTFOLIO` track is not written in Phase 1 — every ingested signal lands on `SHADOW`.

---

## File Structure (Phase 1)

```
forward_testing/
  __init__.py                      # package marker
  storage/
    __init__.py
    db.py                          # ft_get_db(), init_ft_tables() — WAL + busy_timeout + idempotent migration
    schema.py                      # FT_PHASE1_SCHEMA DDL (versioned, single source of truth)
    repo.py                        # FTRepo — compute-then-write DAOs
  lifecycle/
    __init__.py
    states.py                      # SignalState enum, LEGAL_TRANSITIONS, TransitionError, is_legal()
    manager.py                     # LifecycleManager — guarded idempotent transitions
  adapters/
    __init__.py
    signal_adapter.py              # SignalAdapter.ingest(run_date) — scheduled_signals → ft_signal
tests/
  forward_testing/
    __init__.py
    conftest.py                    # ft_db + repo fixtures (tmp_path DB)
    test_storage_db.py             # Task 1, 2
    test_storage_repo.py           # Task 3
    test_lifecycle_states.py       # Task 4
    test_lifecycle_manager.py      # Task 5
    test_signal_adapter.py         # Task 6
    test_phase1_e2e.py             # Task 7
data/
  db.py                            # Task 8 — one lazy init_ft_tables() call added to init_db()
```

**Responsibility boundaries:** `db.py` owns connections + schema bootstrap (no business logic). `schema.py` owns DDL only (no code). `repo.py` owns persistence (no state-machine logic). `states.py` owns transition rules (pure, no I/O). `manager.py` composes `states` + `repo` (the only place that decides a transition is legal). `signal_adapter.py` owns source→canonical mapping (the only place that reads `scheduled_signals`).

---

## Task 1: Package skeleton + WAL/busy-timeout connection helper

**Files:**
- Create: `forward_testing/__init__.py`
- Create: `forward_testing/storage/__init__.py`
- Create: `forward_testing/storage/db.py`
- Create: `tests/forward_testing/__init__.py`
- Test: `tests/forward_testing/test_storage_db.py`

> `conftest.py` is deliberately created in Task 3 (not here): it imports `FTRepo` and `init_ft_tables`, which only exist after Tasks 2–3. Tasks 1 and 2 tests use the built-in `tmp_path` fixture directly and need no custom fixtures.

- [ ] **Step 1: Write the failing test**

Create `tests/forward_testing/__init__.py` (empty) and `tests/forward_testing/test_storage_db.py`:

```python
"""Connection helper tests: WAL mode, busy_timeout, row factory."""
import sqlite3
from forward_testing.storage.db import ft_get_db


def test_ft_get_db_sets_row_factory_and_busy_timeout(tmp_path):
    db_path = str(tmp_path / "ft.db")
    conn = ft_get_db(db_path)
    try:
        assert conn.row_factory is sqlite3.Row
        bt = conn.execute("PRAGMA busy_timeout").fetchone()[0]
        assert bt == 30000
    finally:
        conn.close()


def test_ft_get_db_uses_wal(tmp_path):
    db_path = str(tmp_path / "ft.db")
    conn = ft_get_db(db_path)
    conn.close()
    # WAL is persistent on the db file; re-open and check.
    conn = sqlite3.connect(db_path)
    mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
    conn.close()
    assert mode.lower() == "wal"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/forward_testing/test_storage_db.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'forward_testing'`

- [ ] **Step 3: Write minimal implementation**

Create `forward_testing/__init__.py` (empty) and `forward_testing/storage/__init__.py` (empty).

Create `forward_testing/storage/db.py`:

```python
"""Forward-testing storage: connection helper + idempotent schema bootstrap.

DB-lock discipline (incident 2026-06-25): every caller opens a SHORT-LIVED
connection, writes in one transaction, and closes. Never hold a connection
open across long computation. WAL is persistent on the db file; busy_timeout
is set per-connection.
"""
import sqlite3


def _default_db_path():
    """Resolve the canonical DB path lazily so tests can inject a temp path
    without importing config."""
    from config import DB_PATH
    return DB_PATH


def ft_get_db(db_path=None):
    """Open a short-lived FT connection: Row factory + busy_timeout.

    Caller is responsible for closing promptly (use `with ft_get_db(...) as c:`).
    """
    conn = sqlite3.connect(db_path or _default_db_path(), timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


def _ensure_wal(db_path):
    conn = sqlite3.connect(db_path, timeout=30)
    try:
        conn.execute("PRAGMA busy_timeout=30000")
        conn.execute("PRAGMA journal_mode=WAL")
    finally:
        conn.close()


def init_ft_tables(db_path=None):
    """Create the Phase-1 forward-testing tables. Idempotent.

    Later phases extend this with positions/trades/performance/scoreboard tables.
    """
    from forward_testing.storage.schema import FT_PHASE1_SCHEMA
    db_path = db_path or _default_db_path()
    _ensure_wal(db_path)
    conn = ft_get_db(db_path)
    try:
        conn.executescript(FT_PHASE1_SCHEMA)
        conn.commit()
    finally:
        conn.close()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/forward_testing/test_storage_db.py -v`
Expected: PASS — 2 passed.

- [ ] **Step 5: Commit**

```bash
git add forward_testing/__init__.py forward_testing/storage/__init__.py \
        forward_testing/storage/db.py tests/forward_testing/__init__.py \
        tests/forward_testing/test_storage_db.py
git commit -m "feat(forward-test): package skeleton + WAL/busy_timeout connection helper"
```

---

## Task 2: Versioned schema (`ft_*` Phase-1 tables)

**Files:**
- Create: `forward_testing/storage/schema.py`
- Test: `tests/forward_testing/test_storage_db.py` (append)

- [ ] **Step 1: Append the failing test**

Append to `tests/forward_testing/test_storage_db.py`:

```python
from forward_testing.storage.db import init_ft_tables


EXPECTED_TABLES = {
    "ft_strategy_version", "ft_signal", "ft_signal_state",
    "ft_transition_log", "ft_run", "ft_run_log",
}


def test_init_ft_tables_creates_all_phase1_tables(tmp_path):
    db_path = str(tmp_path / "ft.db")
    init_ft_tables(db_path)
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    conn.close()
    names = {r[0] for r in rows}
    missing = EXPECTED_TABLES - names
    assert not missing, f"missing tables: {missing}"


def test_init_ft_tables_is_idempotent(tmp_path):
    db_path = str(tmp_path / "ft.db")
    init_ft_tables(db_path)
    init_ft_tables(db_path)  # second call must not error
    conn = sqlite3.connect(db_path)
    # ft_signal unique constraint survives re-create
    cols = {r[1] for r in conn.execute("PRAGMA table_info(ft_signal)")}
    conn.close()
    assert {"signal_date", "ticker", "strategy", "track"}.issubset(cols)


def test_ft_signal_unique_constraint(tmp_path):
    db_path = str(tmp_path / "ft.db")
    init_ft_tables(db_path)
    conn = sqlite3.connect(db_path)
    conn.executemany(
        "INSERT INTO ft_signal (signal_date, ticker, strategy, track, direction) "
        "VALUES (?,?,?,?,?)",
        [("2026-06-27", "BBCA", "TFB", "SHADOW", "LONG")],
    )
    # same (date,ticker,strategy,track) must be rejected
    try:
        conn.execute(
            "INSERT INTO ft_signal (signal_date, ticker, strategy, track, direction) "
            "VALUES (?,?,?,?,?)",
            ("2026-06-27", "BBCA", "TFB", "SHADOW", "LONG"),
        )
        collided = False
    except sqlite3.IntegrityError:
        collided = True
    conn.commit()
    conn.close()
    assert collided
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/forward_testing/test_storage_db.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'forward_testing.storage.schema'`

- [ ] **Step 3: Write minimal implementation**

Create `forward_testing/storage/schema.py`:

```python
"""Versioned DDL for forward-testing tables (single source of truth).

Phase 1 (foundation): strategy_version, signal, signal_state, transition_log,
run, run_log. Later phases (positions, trades, marks, adjustments, performance,
scoreboard, benchmark, improvement_log) extend init_ft_tables() with their own
schema constants appended here.
"""

FT_PHASE1_SCHEMA = """
CREATE TABLE IF NOT EXISTS ft_strategy_version (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy         TEXT NOT NULL,
    version          TEXT NOT NULL,
    config_json      TEXT,
    config_hash      TEXT NOT NULL,
    entry_rules_ref  TEXT,
    exit_policy_ref  TEXT,
    created_at       TEXT DEFAULT (datetime('now','localtime')),
    UNIQUE(strategy, version)
);
CREATE INDEX IF NOT EXISTS idx_ft_sv_hash ON ft_strategy_version(config_hash);

CREATE TABLE IF NOT EXISTS ft_signal (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_date         TEXT NOT NULL,
    ticker              TEXT NOT NULL,
    strategy            TEXT NOT NULL,
    strategy_version_id INTEGER REFERENCES ft_strategy_version(id),
    track               TEXT NOT NULL CHECK(track IN ('SHADOW','PORTFOLIO')),
    direction           TEXT NOT NULL DEFAULT 'LONG',
    entry_price_intent  REAL,
    atr14               REAL,
    conviction          REAL,
    source_table        TEXT,
    source_id           INTEGER,
    config_hash         TEXT,
    created_at          TEXT DEFAULT (datetime('now','localtime')),
    UNIQUE(signal_date, ticker, strategy, track)
);
CREATE INDEX IF NOT EXISTS idx_ft_signal_strategy_date ON ft_signal(strategy, signal_date);
CREATE INDEX IF NOT EXISTS idx_ft_signal_track_date ON ft_signal(track, signal_date);

CREATE TABLE IF NOT EXISTS ft_signal_state (
    signal_id   INTEGER PRIMARY KEY REFERENCES ft_signal(id),
    state       TEXT NOT NULL,
    since       TEXT,
    updated_at  TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS ft_transition_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_id   INTEGER NOT NULL REFERENCES ft_signal(id),
    from_state  TEXT,
    to_state    TEXT NOT NULL,
    at          TEXT DEFAULT (datetime('now','localtime')),
    actor       TEXT,
    reason      TEXT,
    run_date    TEXT,
    violation   TEXT
);
CREATE INDEX IF NOT EXISTS idx_ft_trans_signal ON ft_transition_log(signal_id);
CREATE INDEX IF NOT EXISTS idx_ft_trans_run ON ft_transition_log(run_date);

CREATE TABLE IF NOT EXISTS ft_run (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    run_date    TEXT NOT NULL,
    kind        TEXT NOT NULL,
    started_at  TEXT,
    finished_at TEXT,
    status      TEXT NOT NULL,
    pid         INTEGER
);
CREATE INDEX IF NOT EXISTS idx_ft_run_date ON ft_run(run_date);

CREATE TABLE IF NOT EXISTS ft_run_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id      INTEGER REFERENCES ft_run(id),
    phase       TEXT,
    started_at  TEXT,
    finished_at TEXT,
    rows_in     INTEGER,
    rows_out    INTEGER,
    status      TEXT,
    error       TEXT
);
"""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/forward_testing/test_storage_db.py -v`
Expected: PASS — 5 passed (2 from Task 1 + 3 from Task 2).

- [ ] **Step 5: Commit**

```bash
git add forward_testing/storage/schema.py tests/forward_testing/test_storage_db.py
git commit -m "feat(forward-test): versioned Phase-1 ft_* schema (idempotent migration)"
```

---

## Task 3: `FTRepo` — compute-then-write DAOs

**Files:**
- Create: `tests/forward_testing/conftest.py`
- Create: `forward_testing/storage/repo.py`
- Test: `tests/forward_testing/test_storage_repo.py`

- [ ] **Step 1: Create the shared fixtures**

Create `tests/forward_testing/conftest.py`. (`init_ft_tables` from Task 2 and `FTRepo` from this task both exist once Step 4 lands; the fixtures are exercised by the tests below.)

```python
"""Shared fixtures for forward_testing tests."""
import sqlite3
import pytest

from forward_testing.storage.db import init_ft_tables
from forward_testing.storage.repo import FTRepo


@pytest.fixture
def ft_db(tmp_path):
    """Temp DB with Phase-1 ft_* tables + empty source tables (scheduled_signals, daily_screen)."""
    db_path = str(tmp_path / "ft.db")
    init_ft_tables(db_path)
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE scheduled_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_time TEXT, ticker TEXT, strategies TEXT,
            flow_score INTEGER, flow_verdict TEXT, smart_money TEXT,
            signal_reasons TEXT, signal_direction TEXT DEFAULT 'BUY'
        );
        CREATE TABLE daily_screen (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT, ticker TEXT, close INTEGER, volume INTEGER,
            signal TEXT
        );
    """)
    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def repo(ft_db):
    return FTRepo(ft_db)
```

- [ ] **Step 2: Write the failing test**

Create `tests/forward_testing/test_storage_repo.py`:

```python
"""FTRepo tests: insert idempotency, state init, transition audit."""
import sqlite3
from forward_testing.storage.repo import FTRepo


def test_insert_signal_is_idempotent_and_returns_id(repo, ft_db):
    sid1 = repo.insert_signal("2026-06-27", "BBCA", "TFB", "SHADOW")
    sid2 = repo.insert_signal("2026-06-27", "BBCA", "TFB", "SHADOW")  # dup
    assert sid1 == sid2  # same row
    conn = sqlite3.connect(ft_db)
    n = conn.execute("SELECT COUNT(*) FROM ft_signal").fetchone()[0]
    conn.close()
    assert n == 1


def test_insert_signal_distinct_tracks_are_separate_rows(repo, ft_db):
    a = repo.insert_signal("2026-06-27", "BBCA", "TFB", "SHADOW")
    b = repo.insert_signal("2026-06-27", "BBCA", "TFB", "PORTFOLIO")
    assert a != b
    conn = sqlite3.connect(ft_db)
    n = conn.execute("SELECT COUNT(*) FROM ft_signal").fetchone()[0]
    conn.close()
    assert n == 2


def test_get_signal_state_none_until_initialised(repo):
    sid = repo.insert_signal("2026-06-27", "BBCA", "TFB", "SHADOW")
    assert repo.get_signal_state(sid) is None


def test_init_signal_state_sets_generated(repo):
    sid = repo.insert_signal("2026-06-27", "BBCA", "TFB", "SHADOW")
    repo.init_signal_state(sid, "GENERATED")
    assert repo.get_signal_state(sid) == "GENERATED"


def test_init_signal_state_idempotent(repo):
    sid = repo.insert_signal("2026-06-27", "BBCA", "TFB", "SHADOW")
    repo.init_signal_state(sid, "GENERATED")
    repo.init_signal_state(sid, "GENERATED")  # no error, no change
    assert repo.get_signal_state(sid) == "GENERATED"


def test_write_transition_updates_state_and_logs(repo):
    sid = repo.insert_signal("2026-06-27", "BBCA", "TFB", "SHADOW")
    repo.init_signal_state(sid, "GENERATED")
    repo.write_transition(sid, "GENERATED", "CANDIDATE", "2026-06-27",
                          actor="manager", reason="dedupe-ok")
    assert repo.get_signal_state(sid) == "CANDIDATE"
    assert repo.count_transitions(sid) == 1


def test_create_run_and_finish_run(repo, ft_db):
    rid = repo.create_run("2026-06-27", kind="EOD")
    repo.finish_run(rid, "OK")
    conn = sqlite3.connect(ft_db)
    row = conn.execute("SELECT status FROM ft_run WHERE id=?", (rid,)).fetchone()
    conn.close()
    assert row[0] == "OK"
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/forward_testing/test_storage_repo.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'forward_testing.storage.repo'`

- [ ] **Step 4: Write minimal implementation**

Create `forward_testing/storage/repo.py`:

```python
"""FTRepo — compute-then-write data-access objects for forward testing.

DISCIPLINE: each method opens its own short connection, writes in one
transaction, and closes. Never hold a connection open across long computation.
A run is single-writer (pid-locked at the scheduler level in Phase 7), so
read-then-write within a method is race-free in practice.
"""
import os

from forward_testing.storage.db import ft_get_db


class FTRepo:
    def __init__(self, db_path):
        self.db_path = db_path

    # ---- signals ----
    def insert_signal(self, signal_date, ticker, strategy, track,
                      direction="LONG", entry_price_intent=None, atr14=None,
                      conviction=None, strategy_version_id=None,
                      source_table=None, source_id=None, config_hash=None):
        """Idempotent insert on (signal_date, ticker, strategy, track).

        Returns the signal id (existing id on duplicate).
        """
        with ft_get_db(self.db_path) as c:
            c.execute(
                """INSERT INTO ft_signal
                   (signal_date, ticker, strategy, strategy_version_id, track,
                    direction, entry_price_intent, atr14, conviction,
                    source_table, source_id, config_hash)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(signal_date, ticker, strategy, track) DO NOTHING""",
                (signal_date, ticker, strategy, strategy_version_id, track,
                 direction, entry_price_intent, atr14, conviction,
                 source_table, source_id, config_hash),
            )
            c.commit()
            row = c.execute(
                """SELECT id FROM ft_signal
                   WHERE signal_date=? AND ticker=? AND strategy=? AND track=?""",
                (signal_date, ticker, strategy, track),
            ).fetchone()
            return row["id"]

    def get_signal_state(self, signal_id):
        with ft_get_db(self.db_path) as c:
            row = c.execute(
                "SELECT state FROM ft_signal_state WHERE signal_id=?",
                (signal_id,),
            ).fetchone()
            return row["state"] if row else None

    def init_signal_state(self, signal_id, state):
        """Create the state row if absent (PK = signal_id). Idempotent."""
        with ft_get_db(self.db_path) as c:
            c.execute(
                """INSERT INTO ft_signal_state (signal_id, state, since)
                   VALUES (?,?, datetime('now','localtime'))
                   ON CONFLICT(signal_id) DO NOTHING""",
                (signal_id, state),
            )
            c.commit()

    def write_transition(self, signal_id, from_state, to_state, run_date,
                         actor=None, reason=None, violation=None):
        """Append a transition row AND advance ft_signal_state. One transaction."""
        with ft_get_db(self.db_path) as c:
            c.execute(
                """INSERT INTO ft_transition_log
                   (signal_id, from_state, to_state, actor, reason, run_date, violation)
                   VALUES (?,?,?,?,?,?,?)""",
                (signal_id, from_state, to_state, actor, reason, run_date, violation),
            )
            c.execute(
                """UPDATE ft_signal_state
                   SET state=?, since=datetime('now','localtime'),
                       updated_at=datetime('now','localtime')
                   WHERE signal_id=?""",
                (to_state, signal_id),
            )
            c.commit()

    def count_transitions(self, signal_id):
        with ft_get_db(self.db_path) as c:
            return c.execute(
                "SELECT COUNT(*) AS n FROM ft_transition_log WHERE signal_id=?",
                (signal_id,),
            ).fetchone()["n"]

    # ---- run bookkeeping ----
    def create_run(self, run_date, kind="EOD"):
        with ft_get_db(self.db_path) as c:
            cur = c.execute(
                "INSERT INTO ft_run (run_date, kind, started_at, status, pid) "
                "VALUES (?,?, datetime('now','localtime'),'RUNNING',?)",
                (run_date, kind, os.getpid()),
            )
            c.commit()
            return cur.lastrowid

    def finish_run(self, run_id, status):
        with ft_get_db(self.db_path) as c:
            c.execute(
                "UPDATE ft_run SET status=?, finished_at=datetime('now','localtime') "
                "WHERE id=?",
                (status, run_id),
            )
            c.commit()
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/forward_testing/test_storage_repo.py -v`
Expected: PASS — 7 passed. (The `repo` and `ft_db` fixtures from `conftest.py` now resolve.)

- [ ] **Step 6: Commit**

```bash
git add tests/forward_testing/conftest.py forward_testing/storage/repo.py \
        tests/forward_testing/test_storage_repo.py
git commit -m "feat(forward-test): FTRepo compute-then-write DAOs + shared fixtures (signals, state, transitions, runs)"
```

---

## Task 4: Lifecycle states (pure rules)

**Files:**
- Create: `forward_testing/lifecycle/__init__.py`
- Create: `forward_testing/lifecycle/states.py`
- Test: `tests/forward_testing/test_lifecycle_states.py`

- [ ] **Step 1: Write the failing test**

Create `tests/forward_testing/test_lifecycle_states.py`:

```python
"""Pure lifecycle rules: legal forward transitions, illegal reversals, terminal."""
from forward_testing.lifecycle.states import (
    SignalState, LEGAL_TRANSITIONS, TransitionError, is_legal,
)


def test_all_forward_transitions_legal():
    assert is_legal(SignalState.GENERATED, SignalState.CANDIDATE)
    assert is_legal(SignalState.CANDIDATE, SignalState.CONFIRMED)
    assert is_legal(SignalState.CONFIRMED, SignalState.OPENED)
    assert is_legal(SignalState.OPENED, SignalState.HOLDING)
    assert is_legal(SignalState.HOLDING, SignalState.EXITED)
    assert is_legal(SignalState.EXITED, SignalState.ARCHIVED)
    assert is_legal(SignalState.ARCHIVED, SignalState.REVIEWED)


def test_reversal_transitions_illegal():
    assert not is_legal(SignalState.CONFIRMED, SignalState.GENERATED)
    assert not is_legal(SignalState.ARCHIVED, SignalState.HOLDING)
    assert not is_legal(SignalState.REVIEWED, SignalState.ARCHIVED)


def test_skip_transitions_illegal():
    # cannot jump GENERATED straight to HOLDING
    assert not is_legal(SignalState.GENERATED, SignalState.HOLDING)


def test_suspension_round_trip_legal():
    assert is_legal(SignalState.HOLDING, SignalState.SUSPENDED)
    assert is_legal(SignalState.SUSPENDED, SignalState.HOLDING)
    assert is_legal(SignalState.SUSPENDED, SignalState.EXITED)


def test_reviewed_is_terminal():
    assert LEGAL_TRANSITIONS[SignalState.REVIEWED] == set()
    assert not is_legal(SignalState.REVIEWED, SignalState.GENERATED)


def test_enum_is_string():
    assert SignalState.GENERATED == "GENERATED"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/forward_testing/test_lifecycle_states.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'forward_testing.lifecycle'`

- [ ] **Step 3: Write minimal implementation**

Create `forward_testing/lifecycle/__init__.py` (empty).

Create `forward_testing/lifecycle/states.py`:

```python
"""Forward-testing signal lifecycle: states, legal transitions, errors.

Pure module — no I/O. The LifecycleManager (manager.py) is the only caller
that decides whether a transition may proceed.
"""
from enum import Enum


class SignalState(str, Enum):
    GENERATED = "GENERATED"
    CANDIDATE = "CANDIDATE"
    CONFIRMED = "CONFIRMED"
    OPENED = "OPENED"
    HOLDING = "HOLDING"
    SUSPENDED = "SUSPENDED"
    EXITED = "EXITED"
    ARCHIVED = "ARCHIVED"
    REVIEWED = "REVIEWED"


# Forward-only legal transitions: from_state -> {allowed to_states}.
# Matches the blueprint §3.1 state machine.
LEGAL_TRANSITIONS = {
    SignalState.GENERATED: {SignalState.CANDIDATE, SignalState.ARCHIVED},
    SignalState.CANDIDATE: {SignalState.CONFIRMED, SignalState.ARCHIVED},
    SignalState.CONFIRMED: {SignalState.OPENED, SignalState.ARCHIVED},
    SignalState.OPENED:    {SignalState.HOLDING, SignalState.EXITED},
    SignalState.HOLDING:   {SignalState.EXITED, SignalState.SUSPENDED},
    SignalState.SUSPENDED: {SignalState.HOLDING, SignalState.EXITED},
    SignalState.EXITED:    {SignalState.ARCHIVED},
    SignalState.ARCHIVED:  {SignalState.REVIEWED},
    SignalState.REVIEWED:  set(),
}

INITIAL_STATE = SignalState.GENERATED


class TransitionError(Exception):
    """Raised when an illegal state transition is attempted."""


def is_legal(from_state, to_state) -> bool:
    if from_state not in LEGAL_TRANSITIONS:
        return False
    return to_state in LEGAL_TRANSITIONS[from_state]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/forward_testing/test_lifecycle_states.py -v`
Expected: PASS — 6 passed.

- [ ] **Step 5: Commit**

```bash
git add forward_testing/lifecycle/__init__.py forward_testing/lifecycle/states.py \
        tests/forward_testing/test_lifecycle_states.py
git commit -m "feat(forward-test): signal lifecycle states + legal-transition rules"
```

---

## Task 5: `LifecycleManager` — guarded, idempotent transitions

**Files:**
- Create: `forward_testing/lifecycle/manager.py`
- Test: `tests/forward_testing/test_lifecycle_manager.py`

- [ ] **Step 1: Write the failing test**

Create `tests/forward_testing/test_lifecycle_manager.py`:

```python
"""LifecycleManager tests: legal move, idempotency, illegal rejection + audit."""
import sqlite3
import pytest

from forward_testing.lifecycle.states import SignalState, TransitionError
from forward_testing.lifecycle.manager import LifecycleManager


def _seed_generated(repo):
    sid = repo.insert_signal("2026-06-27", "BBCA", "TFB", "SHADOW")
    repo.init_signal_state(sid, SignalState.GENERATED.value)
    return sid


def test_legal_transition_updates_state_and_logs(repo):
    sid = _seed_generated(repo)
    mgr = LifecycleManager(repo)
    new = mgr.transition(sid, SignalState.CANDIDATE, "2026-06-27",
                         actor="ranker", reason="passed-dedupe")
    assert new == SignalState.CANDIDATE
    assert repo.get_signal_state(sid) == "CANDIDATE"
    assert repo.count_transitions(sid) == 1


def test_transition_to_current_state_is_idempotent(repo):
    sid = _seed_generated(repo)
    mgr = LifecycleManager(repo)
    mgr.transition(sid, SignalState.CANDIDATE, "2026-06-27")
    mgr.transition(sid, SignalState.CANDIDATE, "2026-06-27")  # no-op
    assert repo.count_transitions(sid) == 1  # no extra log row


def test_illegal_transition_raises_and_logs_violation(repo, ft_db):
    sid = _seed_generated(repo)
    repo.write_transition(sid, "GENERATED", "ARCHIVED", "2026-06-27")  # fast-forward to ARCHIVED
    mgr = LifecycleManager(repo)
    with pytest.raises(TransitionError):
        mgr.transition(sid, SignalState.HOLDING, "2026-06-27")
    # state must NOT have changed ...
    assert repo.get_signal_state(sid) == "ARCHIVED"
    # ... but a violation row must have been logged
    conn = sqlite3.connect(ft_db)
    v = conn.execute(
        "SELECT COUNT(*) FROM ft_transition_log WHERE signal_id=? AND violation='ILLEGAL'",
        (sid,),
    ).fetchone()[0]
    conn.close()
    assert v == 1


def test_transition_accepts_string_state(repo):
    sid = _seed_generated(repo)
    mgr = LifecycleManager(repo)
    mgr.transition(sid, "CANDIDATE", "2026-06-27")  # string, not enum
    assert repo.get_signal_state(sid) == "CANDIDATE"


def test_current_state_returns_enum(repo):
    sid = _seed_generated(repo)
    mgr = LifecycleManager(repo)
    assert mgr.current_state(sid) == SignalState.GENERATED
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/forward_testing/test_lifecycle_manager.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'forward_testing.lifecycle.manager'`

- [ ] **Step 3: Write minimal implementation**

Create `forward_testing/lifecycle/manager.py`:

```python
"""LifecycleManager — the only component that decides a transition may proceed.

Guarded: rejects illegal transitions (after logging a violation).
Idempotent: transitioning to the current state is a no-op (no log row).
"""
from forward_testing.lifecycle.states import (
    SignalState, TransitionError, is_legal,
)


class LifecycleManager:
    def __init__(self, repo):
        self.repo = repo

    def current_state(self, signal_id):
        s = self.repo.get_signal_state(signal_id)
        return SignalState(s) if s else None

    def transition(self, signal_id, to_state, run_date, actor=None, reason=None):
        """Move signal_id to to_state.

        Returns the new SignalState. Raises TransitionError on illegal moves.
        Idempotent: if the signal is already in to_state, returns it with no log.
        """
        to_state = SignalState(to_state)
        current = self.current_state(signal_id)
        if current is None:
            raise TransitionError(f"signal {signal_id} has no state row")
        if current == to_state:
            return current  # idempotent no-op
        if not is_legal(current, to_state):
            self.repo.write_transition(
                signal_id, current.value, to_state.value, run_date,
                actor=actor, reason=reason, violation="ILLEGAL",
            )
            raise TransitionError(
                f"illegal transition {current.value} -> {to_state.value} "
                f"for signal {signal_id}"
            )
        self.repo.write_transition(
            signal_id, current.value, to_state.value, run_date,
            actor=actor, reason=reason,
        )
        return to_state
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/forward_testing/test_lifecycle_manager.py -v`
Expected: PASS — 5 passed.

- [ ] **Step 5: Commit**

```bash
git add forward_testing/lifecycle/manager.py tests/forward_testing/test_lifecycle_manager.py
git commit -m "feat(forward-test): LifecycleManager — guarded idempotent transitions + violation audit"
```

---

## Task 6: `SignalAdapter` — ingest `scheduled_signals` → `ft_signal`

**Files:**
- Create: `forward_testing/adapters/__init__.py`
- Create: `forward_testing/adapters/signal_adapter.py`
- Test: `tests/forward_testing/test_signal_adapter.py`

- [ ] **Step 1: Write the failing test**

Create `tests/forward_testing/test_signal_adapter.py`:

```python
"""SignalAdapter tests: ingest, dedupe, strategy/direction mapping, idempotency."""
import sqlite3

from forward_testing.adapters.signal_adapter import SignalAdapter


def _seed_signal(conn, scan_time, ticker, strategies, flow_score, direction="BUY"):
    conn.execute(
        "INSERT INTO scheduled_signals "
        "(scan_time, ticker, strategies, flow_score, signal_direction) "
        "VALUES (?,?,?,?,?)",
        (scan_time, ticker, strategies, flow_score, direction),
    )


def test_ingest_creates_shadow_signals_at_generated(ft_db, repo):
    conn = sqlite3.connect(ft_db)
    _seed_signal(conn, "2026-06-27 16:15", "BBCA", "TFB,Swing", 60)
    _seed_signal(conn, "2026-06-27 16:15", "TLKM", "MTF_REVERSAL", 45)
    conn.commit()
    conn.close()

    n = SignalAdapter(repo, ft_db).ingest("2026-06-27")
    assert n == 2

    conn = sqlite3.connect(ft_db)
    rows = conn.execute(
        "SELECT ticker, strategy, track, direction FROM ft_signal ORDER BY ticker"
    ).fetchall()
    states = conn.execute(
        "SELECT state FROM ft_signal_state"
    ).fetchall()
    conn.close()
    assert [r[0] for r in rows] == ["BBCA", "TLKM"]
    assert all(r[2] == "SHADOW" for r in rows)
    assert all(r[1] for r in rows)  # strategy resolved
    assert {s[0] for s in states} == {"GENERATED"}


def test_ingest_takes_first_strategy_from_comma_list(ft_db, repo):
    conn = sqlite3.connect(ft_db)
    _seed_signal(conn, "2026-06-27 16:15", "BBCA", "TFB,Swing,Panic", 60)
    conn.commit()
    conn.close()
    SignalAdapter(repo, ft_db).ingest("2026-06-27")
    conn = sqlite3.connect(ft_db)
    strat = conn.execute("SELECT strategy FROM ft_signal").fetchone()[0]
    conn.close()
    assert strat == "TFB"


def test_ingest_maps_direction(ft_db, repo):
    conn = sqlite3.connect(ft_db)
    _seed_signal(conn, "2026-06-27 16:15", "BBCA", "TFB", 60, direction="SELL")
    conn.commit()
    conn.close()
    SignalAdapter(repo, ft_db).ingest("2026-06-27")
    conn = sqlite3.connect(ft_db)
    d = conn.execute("SELECT direction FROM ft_signal").fetchone()[0]
    conn.close()
    assert d == "SHORT"


def test_ingest_is_idempotent(ft_db, repo):
    conn = sqlite3.connect(ft_db)
    _seed_signal(conn, "2026-06-27 16:15", "BBCA", "TFB", 60)
    conn.commit()
    conn.close()
    adapter = SignalAdapter(repo, ft_db)
    assert adapter.ingest("2026-06-27") == 1
    assert adapter.ingest("2026-06-27") == 0  # re-run: nothing new
    conn = sqlite3.connect(ft_db)
    n_signals = conn.execute("SELECT COUNT(*) FROM ft_signal").fetchone()[0]
    n_trans = conn.execute("SELECT COUNT(*) FROM ft_transition_log").fetchone()[0]
    conn.close()
    assert n_signals == 1
    assert n_trans == 1  # only the GENERATED entry, not duplicated


def test_ingest_records_source_link(ft_db, repo):
    conn = sqlite3.connect(ft_db)
    _seed_signal(conn, "2026-06-27 16:15", "BBCA", "TFB", 60)
    conn.commit()
    src_id = conn.execute("SELECT id FROM scheduled_signals").fetchone()[0]
    conn.close()
    SignalAdapter(repo, ft_db).ingest("2026-06-27")
    conn = sqlite3.connect(ft_db)
    row = conn.execute(
        "SELECT source_table, source_id, conviction FROM ft_signal"
    ).fetchone()
    conn.close()
    assert row[0] == "scheduled_signals"
    assert row[1] == src_id
    assert row[2] == 60


def test_ingest_filters_by_run_date_only(ft_db, repo):
    conn = sqlite3.connect(ft_db)
    _seed_signal(conn, "2026-06-27 16:15", "BBCA", "TFB", 60)
    _seed_signal(conn, "2026-06-28 16:15", "TLKM", "TFB", 60)  # different day
    conn.commit()
    conn.close()
    n = SignalAdapter(repo, ft_db).ingest("2026-06-27")
    assert n == 1  # only the 27th
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/forward_testing/test_signal_adapter.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'forward_testing.adapters.signal_adapter'`

- [ ] **Step 3: Write minimal implementation**

Create `forward_testing/adapters/__init__.py` (empty).

Create `forward_testing/adapters/signal_adapter.py`:

```python
"""SignalAdapter — ingest screener output into the forward-test signal model.

Reads (read-only): scheduled_signals.
Writes: ft_signal (SHADOW track), ft_signal_state, ft_transition_log.

Phase 1: every ingested signal lands on the SHADOW track at GENERATED.
Selection to the PORTFOLIO track happens in Phase 3 (Ranker/Sizer).
strategy_version_id/config_hash are left NULL until Phase 2 wires the
strategy registry.
"""
from forward_testing.lifecycle.states import SignalState
from forward_testing.storage.db import ft_get_db

SHADOW = "SHADOW"


class SignalAdapter:
    def __init__(self, repo, db_path):
        self.repo = repo
        self.db_path = db_path

    def ingest(self, run_date):
        """Ingest all scheduled_signals whose scan_time falls on run_date.

        Returns the number of NEWLY ingested signals (re-runs return 0).
        """
        n = 0
        for row in self._read_source_signals(run_date):
            sid = self.repo.insert_signal(
                signal_date=run_date,
                ticker=row["ticker"],
                strategy=self._strategy(row),
                track=SHADOW,
                direction=self._direction(row),
                conviction=row["flow_score"],
                source_table="scheduled_signals",
                source_id=row["id"],
            )
            if self.repo.get_signal_state(sid) is None:
                self.repo.init_signal_state(sid, SignalState.GENERATED.value)
                self.repo.write_transition(
                    sid, None, SignalState.GENERATED.value, run_date,
                    actor="adapter", reason="ingest",
                )
                n += 1
        return n

    def _read_source_signals(self, run_date):
        # scan_time is stored as "YYYY-MM-DD HH:MM"; match by date prefix.
        with ft_get_db(self.db_path) as c:
            return c.execute(
                """SELECT id, ticker, strategies, flow_score, signal_direction
                   FROM scheduled_signals
                   WHERE substr(scan_time, 1, 10) = ?
                   ORDER BY id""",
                (run_date,),
            ).fetchall()

    @staticmethod
    def _strategy(row):
        # scheduled_signals.strategies is comma-joined; first entry is primary.
        joined = (row["strategies"] or "").strip()
        first = joined.split(",")[0].strip()
        return first or "UNKNOWN"

    @staticmethod
    def _direction(row):
        d = (row["signal_direction"] or "BUY").upper()
        return "SHORT" if d == "SELL" else "LONG"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/forward_testing/test_signal_adapter.py -v`
Expected: PASS — 6 passed.

- [ ] **Step 5: Commit**

```bash
git add forward_testing/adapters/__init__.py forward_testing/adapters/signal_adapter.py \
        tests/forward_testing/test_signal_adapter.py
git commit -m "feat(forward-test): SignalAdapter ingests scheduled_signals -> ft_signal (SHADOW/GENERATED)"
```

---

## Task 7: Phase-1 end-to-end wiring test

**Files:**
- Test: `tests/forward_testing/test_phase1_e2e.py`

- [ ] **Step 1: Write the failing test**

Create `tests/forward_testing/test_phase1_e2e.py`:

```python
"""Phase-1 end-to-end: source -> adapter -> lifecycle, with audit + idempotency."""
import sqlite3

from forward_testing.adapters.signal_adapter import SignalAdapter
from forward_testing.lifecycle.manager import LifecycleManager
from forward_testing.lifecycle.states import SignalState


def test_full_phase1_flow(ft_db, repo):
    # seed two screener signals for the day
    conn = sqlite3.connect(ft_db)
    conn.executemany(
        "INSERT INTO scheduled_signals "
        "(scan_time, ticker, strategies, flow_score, signal_direction) VALUES (?,?,?,?,?)",
        [
            ("2026-06-27 16:15", "BBCA", "TFB", 60, "BUY"),
            ("2026-06-27 16:15", "TLKM", "MTF_REVERSAL", 45, "BUY"),
        ],
    )
    conn.commit()
    conn.close()

    run_id = repo.create_run("2026-06-27", kind="EOD")
    adapter = SignalAdapter(repo, ft_db)
    mgr = LifecycleManager(repo)

    ingested = adapter.ingest("2026-06-27")
    assert ingested == 2

    # both start at GENERATED
    conn = sqlite3.connect(ft_db)
    sids = [r[0] for r in conn.execute(
        "SELECT id FROM ft_signal ORDER BY ticker").fetchall()]
    conn.close()
    assert [mgr.current_state(s) for s in sids] == [SignalState.GENERATED,
                                                     SignalState.GENERATED]

    # advance both to CANDIDATE
    for s in sids:
        mgr.transition(s, SignalState.CANDIDATE, "2026-06-27", actor="ranker")
    assert [mgr.current_state(s) for s in sids] == [SignalState.CANDIDATE,
                                                     SignalState.CANDIDATE]

    # re-ingest must be a no-op (idempotent)
    assert adapter.ingest("2026-06-27") == 0

    # every signal has exactly: 1 GENERATED (adapter) + 1 CANDIDATE (manager) = 2 transitions
    for s in sids:
        assert repo.count_transitions(s) == 2

    repo.finish_run(run_id, "OK")
    conn = sqlite3.connect(ft_db)
    status = conn.execute("SELECT status FROM ft_run WHERE id=?", (run_id,)).fetchone()[0]
    conn.close()
    assert status == "OK"
```

- [ ] **Step 2: Run test to verify it fails (then passes)**

Run: `pytest tests/forward_testing/test_phase1_e2e.py -v`
Expected: PASS — 1 passed. (All components already exist from Tasks 1–6; this test verifies they compose.)

- [ ] **Step 3: Run the whole Phase-1 suite together**

Run: `pytest tests/forward_testing/ -v`
Expected: PASS — all tests green across `test_storage_db`, `test_storage_repo`, `test_lifecycle_states`, `test_lifecycle_manager`, `test_signal_adapter`, `test_phase1_e2e`.

- [ ] **Step 4: Commit**

```bash
git add tests/forward_testing/test_phase1_e2e.py
git commit -m "test(forward-test): Phase-1 end-to-end (source -> adapter -> lifecycle -> audit)"
```

---

## Task 8: Wire `init_ft_tables()` into application startup

**Files:**
- Modify: `data/db.py` (add a lazy call at the end of `init_db()`)
- Test: `tests/forward_testing/test_storage_db.py` (append)

- [ ] **Step 1: Append the failing test**

Append to `tests/forward_testing/test_storage_db.py`:

```python
def test_init_db_creates_ft_tables(tmp_path, monkeypatch):
    # Point data.db + config at a temp DB so init_db() bootstraps in isolation.
    db_path = str(tmp_path / "init.db")
    import data.db as data_db
    monkeypatch.setattr(data_db, "DB_PATH", db_path)

    # init_db() also calls init_agent_firm_tables(); that is fine on a fresh DB.
    data_db.init_db()

    conn = sqlite3.connect(db_path)
    names = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    conn.close()
    assert "ft_signal" in names
    assert "ft_transition_log" in names
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/forward_testing/test_storage_db.py::test_init_db_creates_ft_tables -v`
Expected: FAIL — `assert 'ft_signal' in names` is False (`init_db()` does not yet create ft_ tables).

- [ ] **Step 3: Write minimal implementation**

In `data/db.py`, add a lazy call at the end of `init_db()` (after the `init_agent_firm_tables()` line, line 53). The edited tail of `init_db()`:

```python
    print("DB initialized.")
    init_agent_firm_tables()
    # Forward-testing foundation tables (Phase 1). Lazy import avoids any
    # import cycle; idempotent so safe on every startup.
    from forward_testing.storage.db import init_ft_tables
    init_ft_tables(DB_PATH)
```

> `DB_PATH` here is the module-level `data.db.DB_PATH` (already used by `get_db()`). `init_ft_tables` accepts the explicit path; tests monkeypatch `data_db.DB_PATH` so the same value is passed in.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/forward_testing/test_storage_db.py::test_init_db_creates_ft_tables -v`
Expected: PASS — 1 passed.

- [ ] **Step 5: Run the full Phase-1 suite once more**

Run: `pytest tests/forward_testing/ -v`
Expected: PASS — all green.

- [ ] **Step 6: Commit**

```bash
git add data/db.py tests/forward_testing/test_storage_db.py
git commit -m "feat(forward-test): auto-create ft_* tables on app startup (lazy, idempotent)"
```

---

## Definition of Done (Phase 1)

- [ ] All 8 tasks committed on the feature branch.
- [ ] `pytest tests/forward_testing/ -v` is fully green.
- [ ] `pytest tests/ -q` (the existing repo suite) still passes — Phase 1 is additive and touches only `data/db.py` (one lazy, idempotent call) plus new files.
- [ ] `init_ft_tables()` has been run once against the production `data/walkforward.db` (via app startup or a one-off `python -c "from forward_testing.storage.db import init_ft_tables; init_ft_tables()"`), and `sqlite3 data/walkforward.db ".tables" | grep ft_` shows the six Phase-1 tables.
- [ ] A manual smoke confirms an ingest on a recent `scheduled_signals` date populates `ft_signal`/`ft_signal_state`/`ft_transition_log` without locking the DB during the run.

---

## Self-Review

**1. Spec coverage (blueprint → task):**
- §4 `ft_*` schema (Phase-1 subset) → Tasks 2, 8.
- §3 lifecycle state machine + transitions + audit + idempotency → Tasks 4, 5.
- §2.2.1 Signal Adapter → Task 6.
- §2.2.2 Lifecycle Manager → Tasks 4, 5.
- §4.1 compute-then-write / WAL / busy_timeout → Tasks 1, 3.
- §5 run bookkeeping (`ft_run`/`ft_run_log`) → Task 3 (`create_run`/`finish_run`).
- **Gaps by design (deferred to named phases):** positions/fills/trades/marks/adjustments (Phase 2–3), ExitPolicy (Phase 2), ranker/sizer/corporate-actions (Phase 3), performance/scoreboard/benchmark (Phase 4–5), feedback/AI (Phase 6), daily-flow scheduler + reports (Phase 7). These are out of Phase-1 scope by the decomposition decision, not oversights.

**2. Placeholder scan:** none. Every step has complete code; no "TODO/TBD/handle edge cases" text. The deferred items are stated as explicit scope decisions, not in-code placeholders.

**3. Type/name consistency:**
- `SignalState` used identically in `states.py`, `manager.py`, `signal_adapter.py`, and tests.
- `FTRepo` method names match across `repo.py`, `manager.py`, `signal_adapter.py`, and all tests: `insert_signal`, `get_signal_state`, `init_signal_state`, `write_transition`, `count_transitions`, `create_run`, `finish_run`.
- `ft_get_db`, `init_ft_tables`, `FT_PHASE1_SCHEMA` names consistent across `db.py`/`schema.py`/`repo.py`/`conftest.py`.
- `SignalAdapter(repo, ft_db)` constructor signature consistent across Task 6 tests, Task 7 e2e.
- Column names in DDL match every INSERT/SELECT in repo + adapter + tests (`signal_date`, `track`, `strategies`, `scan_time`, `source_table`, `source_id`, `conviction`).

**4. Refinement from blueprint:** the blueprint's §4.3 suggested `ft_transition_log` idempotency on `(signal_id, run_date)`. Refined here to **manager-level idempotency** (a signal enters each state at most once; the manager no-ops on same-state and rejects/log-violates illegal moves), because multiple legal transitions can occur within one run_date. This is noted inline in Task 5 and is the correct model for a forward-only lifecycle.

---

*End of Phase 1 plan. Phases 2–7 are separate plans, written after Phase 1 ships and the foundation is verified against the production database.*
