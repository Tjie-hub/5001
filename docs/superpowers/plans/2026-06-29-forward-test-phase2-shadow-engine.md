# Forward Testing — Phase 2 (SHADOW Position Engine) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Paper-trade every SHADOW-track signal through to a closed round-trip in `ft_shadow_trade` (per-signal % + R-multiple), using each strategy's real exit rules via a direction-aware `ExitPolicyRegistry`.

**Architecture:** New `forward_testing/positions/` package. Pure exit math lives in `ExitEvaluator` (no I/O); `ShadowPositionManager` is thin orchestration (open pass + exit pass) over `FTRepo` + `MarketDataResolver` + the Phase-1 `LifecycleManager`. Storage is two new tables (`ft_shadow_position` open-state, `ft_shadow_trade` closed) appended to the existing `walkforward.db` via the idempotent `init_ft_tables()`. Every write is a short compute-then-write transaction (the project's DB-lock discipline). SHADOW bypasses selection: `GENERATED → OPENED → EXITED`.

**Tech Stack:** Python 3, SQLite (stdlib `sqlite3`), pytest (`asyncio_mode=auto`). **No new dependencies** — `forward_testing` stays stdlib-only (ATR is reimplemented locally as SMA-ATR to match `engine.indicators.calc_atr` without importing pandas; costs are an injectable `Costs` value object so tests can pass zero costs for exact math).

**Spec:** `docs/superpowers/specs/2026-06-29-forward-test-phase2-design.md`.

**One deliberate deviation from the spec (flagged):** the spec said "reuses `engine.indicators.calc_atr`." This plan reimplements ATR locally (`atr_sma`, ~10 lines, same SMA convention) so `forward_testing` remains stdlib-only and unit-testable without pandas, consistent with Phase 1's no-dependency stance. The SMA formula is identical to `calc_atr`.

**Test-data convention (so the math is reproducible):** flat OHLCV bars `(P, P+0.5, P-0.5, P)` have True Range = 1, so a 14-bar run gives **ATR14 = 1.0**. LONG `vol_weighted` (sl_mult 1.0 / tp_mult 2.0) at entry 100 → **sl = 99, tp = 102**. All open/exit/e2e tests use this convention with base P = 100 (LONG) or 200 (SHORT).

---

## Scope of Phase 2

**In:** `ft_shadow_position`, `ft_shadow_trade` tables + DAOs; `ExitPolicy`/`ExitPolicyRegistry`/`DEFAULT`; `Costs` + `atr_sma`; `MarketDataResolver` (reads `ohlcv`); `ExitEvaluator` (pure exit math); `ShadowPositionManager`; the `GENERATED → OPENED` lifecycle bypass; full test suite.

**Out (deferred):** PORTFOLIO track + `ft_position`/`ft_fill`/`ft_position_mark` + sizing/equity (Phase 3); corporate-action cost-basis adjustment (Phase 3 — Phase 2 only holds suspended tickers via the existing `suspension_events` detector); Ranker/Sizer (Phase 3); performance/scoreboard/benchmark (Phase 4–5); daily-flow scheduler (Phase 7); partial exits/scaling (YAGNI).

---

## File Structure

```
forward_testing/
  positions/
    __init__.py
    exit_policy.py      # ExitPolicy + ExitPolicyRegistry + DEFAULT + InitialLevels (pure)
    costs.py            # Costs value object + apply_costs() (pure)
    market_data.py      # atr_sma (pure) + MarketDataResolver (reads ohlcv)
    exit_evaluator.py   # PositionView/Bar/ExitDecision + evaluate_exit() (pure, no I/O)
    shadow_manager.py   # ShadowPositionManager — open/exit passes, the only writer
  storage/
    schema.py           # append FT_PHASE2_SCHEMA (ft_shadow_position, ft_shadow_trade)
    repo.py             # append shadow position/trade DAOs + get_signals_by_state
    db.py               # init_ft_tables() applies FT_PHASE1_SCHEMA + FT_PHASE2_SCHEMA
  lifecycle/
    states.py           # add GENERATED -> OPENED to LEGAL_TRANSITIONS
tests/
  forward_testing/
    conftest.py         # extend: ohlcv + suspension_events tables, seed helpers
    test_lifecycle_states.py    # extend: GENERATED -> OPENED legal
    test_storage_db.py          # extend: Phase-2 tables created (+ via init_db)
    test_storage_repo.py        # extend: shadow DAOs
    test_exit_policy.py
    test_costs.py
    test_market_data.py
    test_exit_evaluator.py
    test_shadow_manager.py
    test_phase2_e2e.py
```

**Responsibility boundaries:** `exit_policy.py` owns exit config (pure). `costs.py` owns fill-cost economics (pure). `market_data.py` owns OHLCV reads + ATR (the only reader of `ohlcv`). `exit_evaluator.py` owns the exit decision (pure — given a position snapshot + one bar, decide exit/no-exit; no I/O, no state mutation). `shadow_manager.py` composes all of the above and owns writing `ft_shadow_position`/`ft_shadow_trade` + lifecycle transitions.

---

## Task 1: Lifecycle bypass — `GENERATED → OPENED`

**Files:**
- Modify: `forward_testing/lifecycle/states.py`
- Modify: `tests/forward_testing/test_lifecycle_states.py`

- [ ] **Step 1: Append the failing test**

Append to `tests/forward_testing/test_lifecycle_states.py`:

```python
def test_generated_to_opened_is_legal_shadow_bypass():
    # §3.4 dual-track: SHADOW signals go GENERATED -> OPENED directly (no CONFIRMED).
    assert is_legal(SignalState.GENERATED, SignalState.OPENED)


def test_generated_to_holding_still_illegal():
    # OPENED is allowed; HOLDING is still not (must pass through OPENED).
    assert not is_legal(SignalState.GENERATED, SignalState.HOLDING)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/forward_testing/test_lifecycle_states.py::test_generated_to_opened_is_legal_shadow_bypass -v`
Expected: FAIL — `assert is_legal(GENERATED, OPENED)` is False.

- [ ] **Step 3: Write minimal implementation**

In `forward_testing/lifecycle/states.py`, add `SignalState.OPENED` to the `GENERATED` transitions set:

```python
LEGAL_TRANSITIONS = {
    SignalState.GENERATED: {SignalState.CANDIDATE, SignalState.OPENED, SignalState.ARCHIVED},
    SignalState.CANDIDATE: {SignalState.CONFIRMED, SignalState.ARCHIVED},
    SignalState.CONFIRMED: {SignalState.OPENED, SignalState.ARCHIVED},
    SignalState.OPENED:    {SignalState.HOLDING, SignalState.EXITED},
    SignalState.HOLDING:   {SignalState.EXITED, SignalState.SUSPENDED},
    SignalState.SUSPENDED: {SignalState.HOLDING, SignalState.EXITED},
    SignalState.EXITED:    {SignalState.ARCHIVED},
    SignalState.ARCHIVED:  {SignalState.REVIEWED},
    SignalState.REVIEWED:  set(),
}
```

- [ ] **Step 4: Run the full lifecycle suite to verify nothing regressed**

Run: `pytest tests/forward_testing/test_lifecycle_states.py tests/forward_testing/test_lifecycle_manager.py -v`
Expected: PASS — all green (the existing "skip transitions illegal" test asserts `GENERATED → HOLDING` illegal, which stays illegal).

- [ ] **Step 5: Commit**

```bash
git add forward_testing/lifecycle/states.py tests/forward_testing/test_lifecycle_states.py
git commit -m "feat(forward-test): GENERATED->OPENED lifecycle bypass for SHADOW track"
```

---

## Task 2: Phase-2 schema (`ft_shadow_position`, `ft_shadow_trade`)

**Files:**
- Modify: `forward_testing/storage/schema.py`
- Modify: `forward_testing/storage/db.py`
- Modify: `tests/forward_testing/test_storage_db.py`

- [ ] **Step 1: Append the failing tests**

Append to `tests/forward_testing/test_storage_db.py`:

```python
PHASE2_TABLES = {"ft_shadow_position", "ft_shadow_trade"}


def test_init_ft_tables_creates_phase2_tables(tmp_path):
    db_path = str(tmp_path / "ft.db")
    init_ft_tables(db_path)
    conn = sqlite3.connect(db_path)
    names = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    conn.close()
    assert PHASE2_TABLES.issubset(names)


def test_init_ft_tables_phase2_idempotent(tmp_path):
    db_path = str(tmp_path / "ft.db")
    init_ft_tables(db_path)
    init_ft_tables(db_path)  # re-run must not error
    conn = sqlite3.connect(db_path)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(ft_shadow_position)")}
    conn.close()
    assert {"signal_id", "direction", "entry_price", "status"}.issubset(cols)


def test_init_db_creates_phase2_tables(tmp_path, monkeypatch):
    db_path = str(tmp_path / "init.db")
    import data.db as data_db
    monkeypatch.setattr(data_db, "DB_PATH", db_path)
    data_db.init_db()
    conn = sqlite3.connect(db_path)
    names = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    conn.close()
    assert "ft_shadow_position" in names
    assert "ft_shadow_trade" in names
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/forward_testing/test_storage_db.py -k phase2 -v`
Expected: FAIL — `ft_shadow_position` missing.

- [ ] **Step 3: Append `FT_PHASE2_SCHEMA` to `forward_testing/storage/schema.py`**

Append at the end of `forward_testing/storage/schema.py`:

```python
FT_PHASE2_SCHEMA = """
CREATE TABLE IF NOT EXISTS ft_shadow_position (
    signal_id      INTEGER PRIMARY KEY REFERENCES ft_signal(id),
    ticker         TEXT NOT NULL,
    strategy       TEXT NOT NULL,
    direction      TEXT NOT NULL,
    entry_date     TEXT NOT NULL,
    entry_price    REAL NOT NULL,
    atr14          REAL NOT NULL,
    sl_price       REAL,
    tp_price       REAL,
    trail_atr_mult REAL,
    trail_anchor   REAL,
    highest_seen   REAL NOT NULL,
    lowest_seen    REAL NOT NULL,
    hold_days      INTEGER NOT NULL DEFAULT 0,
    status         TEXT NOT NULL DEFAULT 'OPEN',
    exit_date      TEXT,
    exit_price     REAL,
    exit_reason    TEXT,
    created_at     TEXT DEFAULT (datetime('now','localtime')),
    updated_at     TEXT DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS idx_ft_shadow_pos_status ON ft_shadow_position(status);
CREATE INDEX IF NOT EXISTS idx_ft_shadow_pos_ticker ON ft_shadow_position(ticker);

CREATE TABLE IF NOT EXISTS ft_shadow_trade (
    signal_id    INTEGER PRIMARY KEY REFERENCES ft_signal(id),
    ticker       TEXT NOT NULL,
    strategy     TEXT NOT NULL,
    direction    TEXT NOT NULL,
    signal_date  TEXT NOT NULL,
    entry_date   TEXT NOT NULL,
    entry_price  REAL NOT NULL,
    exit_date    TEXT NOT NULL,
    exit_price   REAL NOT NULL,
    exit_reason  TEXT NOT NULL,
    pnl_pct      REAL NOT NULL,
    r_multiple   REAL NOT NULL,
    hold_days    INTEGER NOT NULL,
    mae_pct      REAL,
    mfe_pct      REAL,
    closed_at    TEXT DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS idx_ft_shadow_trade_strat ON ft_shadow_trade(strategy, exit_date);
CREATE INDEX IF NOT EXISTS idx_ft_shadow_trade_ticker ON ft_shadow_trade(ticker);
"""
```

- [ ] **Step 4: Wire `FT_PHASE2_SCHEMA` into `init_ft_tables()`**

In `forward_testing/storage/db.py`, update `init_ft_tables()` so the `executescript` applies both schemas. Replace the body of the `try:` block inside `init_ft_tables`:

```python
    from forward_testing.storage.schema import FT_PHASE1_SCHEMA, FT_PHASE2_SCHEMA
    db_path = db_path or _default_db_path()
    _ensure_wal(db_path)
    conn = ft_get_db(db_path)
    try:
        conn.executescript(FT_PHASE1_SCHEMA + "\n" + FT_PHASE2_SCHEMA)
        conn.commit()
    finally:
        conn.close()
```

(`init_ft_tables` is the only caller and remains idempotent — `CREATE TABLE IF NOT EXISTS`.)

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/forward_testing/test_storage_db.py -v`
Expected: PASS — all storage-db tests green (Phase 1 + Phase 2).

- [ ] **Step 6: Commit**

```bash
git add forward_testing/storage/schema.py forward_testing/storage/db.py tests/forward_testing/test_storage_db.py
git commit -m "feat(forward-test): Phase-2 ft_shadow_position/ft_shadow_trade schema"
```

---

## Task 3: Shadow position/trade DAOs + `ohlcv`/`suspension_events` test fixtures

**Files:**
- Modify: `forward_testing/storage/repo.py`
- Modify: `tests/forward_testing/conftest.py`
- Modify: `tests/forward_testing/test_storage_repo.py`

- [ ] **Step 1: Extend the shared fixtures**

In `tests/forward_testing/conftest.py`, add `ohlcv` + `suspension_events` tables to the `ft_db` fixture and add two seed helpers. Replace the `ft_db` fixture and add helpers after the `repo` fixture:

```python
@pytest.fixture
def ft_db(tmp_path):
    """Temp DB with Phase-1+2 ft_* tables + source tables (scheduled_signals, daily_screen,
    ohlcv, suspension_events)."""
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
            date TEXT, ticker TEXT, close INTEGER, volume INTEGER, signal TEXT
        );
        CREATE TABLE ohlcv (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT, date TEXT, open REAL, high REAL, low REAL, close REAL, volume REAL
        );
        CREATE TABLE suspension_events (
            ticker TEXT, last_normal_date TEXT, resume_date TEXT,
            missing_td INTEGER, gap_pct REAL, classification TEXT, detected_at TEXT
        );
    """)
    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def repo(ft_db):
    return FTRepo(ft_db)


def seed_ohlcv(conn, ticker, bars):
    """bars: list of (date, open, high, low, close[, volume]) in ascending date order."""
    rows = [b if len(b) == 6 else b + (0.0,) for b in bars]
    conn.executemany(
        "INSERT INTO ohlcv (ticker, date, open, high, low, close, volume) VALUES (?,?,?,?,?,?,?)",
        [(ticker,) + r for r in rows],
    )


def seed_signal(conn, scan_time, ticker, strategies, flow_score=0, direction="BUY"):
    """Insert a scheduled_signals row; returns its id."""
    cur = conn.execute(
        "INSERT INTO scheduled_signals (scan_time, ticker, strategies, flow_score, signal_direction) "
        "VALUES (?,?,?,?,?)",
        (scan_time, ticker, strategies, flow_score, direction),
    )
    return cur.lastrowid
```

- [ ] **Step 2: Append the failing tests**

Append to `tests/forward_testing/test_storage_repo.py`:

```python
def test_get_signals_by_state_filters_track_and_state(repo, ft_db):
    conn = sqlite3.connect(ft_db)
    sid = repo.insert_signal("2026-06-26", "BBCA", "vol_weighted", "SHADOW")
    repo.init_signal_state(sid, "GENERATED")
    pid = repo.insert_signal("2026-06-26", "TLKM", "vol_weighted", "PORTFOLIO")
    repo.init_signal_state(pid, "GENERATED")
    conn.close()

    rows = repo.get_signals_by_state("GENERATED", track="SHADOW")
    assert len(rows) == 1
    assert rows[0]["ticker"] == "BBCA"
    assert set(rows[0].keys()) >= {"id", "signal_date", "ticker", "strategy", "direction"}


def test_open_shadow_position_and_get(repo):
    repo.open_shadow_position(
        signal_id=1, ticker="BBCA", strategy="vol_weighted", direction="LONG",
        entry_date="2026-06-27", entry_price=100.0, atr14=1.0,
        sl_price=99.0, tp_price=102.0, trail_atr_mult=None, trail_anchor=100.0,
        highest_seen=100.0, lowest_seen=100.0,
    )
    pos = repo.get_shadow_position(1)
    assert pos["status"] == "OPEN"
    assert pos["entry_price"] == 100.0


def test_open_shadow_position_is_idempotent(repo):
    kwargs = dict(signal_id=1, ticker="BBCA", strategy="vol_weighted", direction="LONG",
                  entry_date="2026-06-27", entry_price=100.0, atr14=1.0,
                  sl_price=99.0, tp_price=102.0, trail_atr_mult=None, trail_anchor=100.0,
                  highest_seen=100.0, lowest_seen=100.0)
    repo.open_shadow_position(**kwargs)
    repo.open_shadow_position(**kwargs)   # duplicate PK -> ignored, no error
    assert repo.get_shadow_position(1)["entry_price"] == 100.0


def test_get_open_positions_update_and_close(repo):
    for sid in (1, 2):
        repo.open_shadow_position(
            signal_id=sid, ticker=f"T{sid}", strategy="vol_weighted", direction="LONG",
            entry_date="2026-06-27", entry_price=100.0, atr14=1.0,
            sl_price=99.0, tp_price=102.0, trail_atr_mult=None, trail_anchor=100.0,
            highest_seen=100.0, lowest_seen=100.0,
        )
    assert {r["signal_id"] for r in repo.get_open_shadow_positions()} == {1, 2}

    repo.update_shadow_position(1, highest_seen=101.0, lowest_seen=99.5, hold_days=2)
    assert repo.get_shadow_position(1)["highest_seen"] == 101.0

    repo.close_shadow_position(1, exit_date="2026-06-29", exit_price=102.0, exit_reason="TP")
    assert repo.get_shadow_position(1)["status"] == "CLOSED"
    assert repo.get_shadow_position(1)["exit_reason"] == "TP"
    assert {r["signal_id"] for r in repo.get_open_shadow_positions()} == {2}


def test_insert_shadow_trade_is_idempotent(repo):
    kwargs = dict(signal_id=1, ticker="BBCA", strategy="vol_weighted", direction="LONG",
                  signal_date="2026-06-26", entry_date="2026-06-27", entry_price=100.0,
                  exit_date="2026-06-28", exit_price=102.0, exit_reason="TP",
                  pnl_pct=0.02, r_multiple=2.0, hold_days=2, mae_pct=-0.005, mfe_pct=0.02)
    repo.insert_shadow_trade(**kwargs)
    repo.insert_shadow_trade(**kwargs)     # duplicate -> ignored
    assert repo.get_shadow_trade(1)["r_multiple"] == 2.0
    conn = sqlite3.connect(repo.db_path)
    n = conn.execute("SELECT COUNT(*) FROM ft_shadow_trade").fetchone()[0]
    conn.close()
    assert n == 1
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/forward_testing/test_storage_repo.py -v`
Expected: FAIL — `FTRepo has no attribute 'get_signals_by_state'`.

- [ ] **Step 4: Append the DAOs to `forward_testing/storage/repo.py`**

Append inside the `FTRepo` class (after `finish_run`):

```python
    # ---- shadow signals lookup ----
    def get_signals_by_state(self, state, track=None):
        """Return ft_signal rows currently in `state` (optionally filtered by track).

        Each row exposes: id, signal_date, ticker, strategy, direction, track.
        """
        with ft_get_db(self.db_path) as c:
            sql = ("SELECT s.id, s.signal_date, s.ticker, s.strategy, s.direction, s.track "
                   "FROM ft_signal s JOIN ft_signal_state st ON st.signal_id = s.id "
                   "WHERE st.state = ?")
            params = [state]
            if track is not None:
                sql += " AND s.track = ?"
                params.append(track)
            sql += " ORDER BY s.id"
            return [dict(r) for r in c.execute(sql, params).fetchall()]

    # ---- shadow positions ----
    def open_shadow_position(self, signal_id, ticker, strategy, direction,
                             entry_date, entry_price, atr14, sl_price, tp_price,
                             trail_atr_mult, trail_anchor, highest_seen, lowest_seen):
        """Idempotent open (PK = signal_id). No-op if a row already exists."""
        with ft_get_db(self.db_path) as c:
            c.execute(
                """INSERT INTO ft_shadow_position
                   (signal_id, ticker, strategy, direction, entry_date, entry_price,
                    atr14, sl_price, tp_price, trail_atr_mult, trail_anchor,
                    highest_seen, lowest_seen, hold_days, status)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,0,'OPEN')
                   ON CONFLICT(signal_id) DO NOTHING""",
                (signal_id, ticker, strategy, direction, entry_date, entry_price,
                 atr14, sl_price, tp_price, trail_atr_mult, trail_anchor,
                 highest_seen, lowest_seen),
            )
            c.commit()

    def get_shadow_position(self, signal_id):
        with ft_get_db(self.db_path) as c:
            row = c.execute(
                "SELECT * FROM ft_shadow_position WHERE signal_id=?", (signal_id,)
            ).fetchone()
            return dict(row) if row else None

    def get_open_shadow_positions(self):
        with ft_get_db(self.db_path) as c:
            return [dict(r) for r in c.execute(
                "SELECT * FROM ft_shadow_position WHERE status='OPEN' ORDER BY signal_id"
            ).fetchall()]

    def update_shadow_position(self, signal_id, highest_seen, lowest_seen, hold_days):
        """Update running extremes + hold-days for an open position. One transaction."""
        with ft_get_db(self.db_path) as c:
            c.execute(
                """UPDATE ft_shadow_position
                   SET highest_seen=?, lowest_seen=?, hold_days=?,
                       updated_at=datetime('now','localtime')
                   WHERE signal_id=?""",
                (highest_seen, lowest_seen, hold_days, signal_id),
            )
            c.commit()

    def close_shadow_position(self, signal_id, exit_date, exit_price, exit_reason):
        with ft_get_db(self.db_path) as c:
            c.execute(
                """UPDATE ft_shadow_position
                   SET status='CLOSED', exit_date=?, exit_price=?, exit_reason=?,
                       updated_at=datetime('now','localtime')
                   WHERE signal_id=?""",
                (exit_date, exit_price, exit_reason, signal_id),
            )
            c.commit()

    # ---- shadow trades ----
    def insert_shadow_trade(self, signal_id, ticker, strategy, direction, signal_date,
                            entry_date, entry_price, exit_date, exit_price, exit_reason,
                            pnl_pct, r_multiple, hold_days, mae_pct, mfe_pct):
        """Idempotent closed round-trip (PK = signal_id)."""
        with ft_get_db(self.db_path) as c:
            c.execute(
                """INSERT INTO ft_shadow_trade
                   (signal_id, ticker, strategy, direction, signal_date, entry_date,
                    entry_price, exit_date, exit_price, exit_reason, pnl_pct, r_multiple,
                    hold_days, mae_pct, mfe_pct)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(signal_id) DO NOTHING""",
                (signal_id, ticker, strategy, direction, signal_date, entry_date,
                 entry_price, exit_date, exit_price, exit_reason, pnl_pct, r_multiple,
                 hold_days, mae_pct, mfe_pct),
            )
            c.commit()

    def get_shadow_trade(self, signal_id):
        with ft_get_db(self.db_path) as c:
            row = c.execute(
                "SELECT * FROM ft_shadow_trade WHERE signal_id=?", (signal_id,)
            ).fetchone()
            return dict(row) if row else None
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/forward_testing/test_storage_repo.py -v`
Expected: PASS — all repo tests green (Phase 1 + Phase 2).

- [ ] **Step 6: Commit**

```bash
git add forward_testing/storage/repo.py tests/forward_testing/conftest.py tests/forward_testing/test_storage_repo.py
git commit -m "feat(forward-test): shadow position/trade DAOs + ohlcv/suspension fixtures"
```

---

## Task 4: `ExitPolicy` + `ExitPolicyRegistry` + `DEFAULT` (pure)

**Files:**
- Create: `forward_testing/positions/__init__.py` (empty)
- Create: `forward_testing/positions/exit_policy.py`
- Test: `tests/forward_testing/test_exit_policy.py`

- [ ] **Step 1: Write the failing test**

Create `tests/forward_testing/test_exit_policy.py`:

```python
"""ExitPolicy registry: per-strategy configs, DEFAULT fallback, initial-level math."""
import math
from forward_testing.positions.exit_policy import ExitPolicy, ExitPolicyRegistry


def test_registry_returns_named_strategies_with_real_params():
    reg = ExitPolicyRegistry()
    assert reg.get("vol_weighted") == ExitPolicy(sl_mult=1.0, tp_mult=2.0, min_rr=2.0)
    assert reg.get("momentum") == ExitPolicy(sl_mult=1.2, tp_mult=2.4, min_rr=2.0, trail_enable=True)
    assert reg.get("vwap_reversion") == ExitPolicy(sl_mult=0.8, tp_mult=1.6, min_rr=2.0)
    assert reg.get("conservative") == ExitPolicy(sl_mult=0.7, tp_mult=1.4, min_rr=2.0)
    assert reg.get("Liquidity Sweep") == ExitPolicy(sl_mult=1.0, tp_mult=2.5, min_rr=2.5)


def test_registry_default_for_distribution_and_unknown():
    reg = ExitPolicyRegistry()
    expected = ExitPolicy(trail_enable=True, trail_atr_mult=3.0, hold_days=10)
    assert reg.get("distribution") == expected
    assert reg.get("something_unknown") == expected


def test_initial_levels_long_fixed_sl_tp():
    pol = ExitPolicy(sl_mult=1.0, tp_mult=2.0, min_rr=2.0)
    lv = pol.initial_levels("LONG", entry=100.0, atr=1.0)
    assert lv.sl_price == 99.0
    assert lv.tp_price == 102.0
    assert lv.one_r == 1.0
    assert lv.trailing is False
    assert lv.initial_stop == 99.0


def test_initial_levels_min_rr_clamps_tp_outward():
    # sl_mult=0.7 -> R=0.7; tp_mult=1.4 -> 0.98 < min_rr*R=1.4 -> tp clamped to entry+1.4
    pol = ExitPolicy(sl_mult=0.7, tp_mult=1.4, min_rr=2.0)
    lv = pol.initial_levels("LONG", entry=100.0, atr=1.0)
    assert math.isclose(lv.tp_price, 101.4)
    assert lv.sl_price == 99.3


def test_initial_levels_short_mirrors_signs():
    pol = ExitPolicy(sl_mult=1.0, tp_mult=2.0, min_rr=2.0)
    lv = pol.initial_levels("SHORT", entry=100.0, atr=1.0)
    assert lv.sl_price == 101.0          # SL above entry for a short
    assert lv.tp_price == 98.0           # TP below entry
    assert lv.initial_stop == 101.0


def test_initial_levels_pure_trail_long():
    pol = ExitPolicy(trail_enable=True, trail_atr_mult=3.0, hold_days=10)
    lv = pol.initial_levels("LONG", entry=100.0, atr=1.0)
    assert lv.sl_price is None and lv.tp_price is None
    assert lv.one_r == 3.0
    assert lv.trailing is True
    assert lv.trail_mult == 3.0
    assert lv.initial_stop == 97.0       # 100 - 3*1


def test_initial_levels_pure_trail_short():
    pol = ExitPolicy(trail_enable=True, trail_atr_mult=3.0, hold_days=10)
    lv = pol.initial_levels("SHORT", entry=100.0, atr=1.0)
    assert lv.initial_stop == 103.0      # 100 + 3*1


def test_trail_enable_with_fixed_sl_uses_sl_mult_as_trail_distance():
    # momentum: sl_mult=1.2 + trail_enable -> trailing stop distance = 1.2 ATR
    pol = ExitPolicy(sl_mult=1.2, tp_mult=2.4, min_rr=2.0, trail_enable=True)
    lv = pol.initial_levels("LONG", entry=100.0, atr=1.0)
    assert lv.trailing is True
    assert lv.trail_mult == 1.2
    assert lv.initial_stop == 98.8
    assert lv.tp_price == 102.4
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/forward_testing/test_exit_policy.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'forward_testing.positions'`.

- [ ] **Step 3: Write minimal implementation**

Create `forward_testing/positions/__init__.py` (empty).

Create `forward_testing/positions/exit_policy.py`:

```python
"""Exit policy per strategy + registry. Pure module (no I/O).

Two flavors:
  * Fixed ATR SL/TP (sl_mult/tp_mult set): stop and target fixed at entry;
    trail_enable ratchets the SL using sl_mult as the trail distance.
  * Pure trail (trail_atr_mult set, sl_mult=None): no fixed target; trail + time-stop.

Direction-aware: SHORT mirrors all signs (SL above entry, TP below).
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class InitialLevels:
    sl_price: float | None
    tp_price: float | None
    trail_anchor: float
    one_r: float
    trailing: bool
    trail_mult: float | None   # ATR distance used to recompute the trailing stop
    initial_stop: float


@dataclass(frozen=True)
class ExitPolicy:
    sl_mult: float | None = None
    tp_mult: float | None = None
    min_rr: float = 2.0
    trail_enable: bool = False
    trail_atr_mult: float | None = None
    hold_days: int | None = None

    def initial_levels(self, direction, entry, atr):
        sign = 1 if direction == "LONG" else -1
        if self.sl_mult is not None:
            sl = entry - sign * self.sl_mult * atr
            # TP honours min_rr: at least min_rr*R beyond entry (R = sl_mult*atr).
            tp = entry + sign * max(self.tp_mult, self.min_rr * self.sl_mult) * atr
            trailing = self.trail_enable
            trail_mult = self.sl_mult if trailing else None
            one_r = self.sl_mult * atr
            return InitialLevels(sl, tp, entry, one_r, trailing, trail_mult, sl)
        # Pure trail.
        mult = self.trail_atr_mult
        stop = entry - sign * mult * atr
        return InitialLevels(None, None, entry, mult * atr, True, mult, stop)


class ExitPolicyRegistry:
    """Maps ft_signal.strategy -> ExitPolicy. Unknown keys fall back to DEFAULT."""

    DEFAULT = ExitPolicy(trail_enable=True, trail_atr_mult=3.0, hold_days=10)

    def __init__(self):
        # Params mirror each strategy's run_strategy(...) call-site in engine/strategies.py.
        self._by_strategy = {
            "vol_weighted":     ExitPolicy(sl_mult=1.0, tp_mult=2.0, min_rr=2.0),
            "momentum":         ExitPolicy(sl_mult=1.2, tp_mult=2.4, min_rr=2.0, trail_enable=True),
            "vwap_reversion":   ExitPolicy(sl_mult=0.8, tp_mult=1.6, min_rr=2.0),
            "conservative":     ExitPolicy(sl_mult=0.7, tp_mult=1.4, min_rr=2.0),
            "Liquidity Sweep":  ExitPolicy(sl_mult=1.0, tp_mult=2.5, min_rr=2.5),
        }

    def get(self, strategy):
        return self._by_strategy.get(strategy, self.DEFAULT)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/forward_testing/test_exit_policy.py -v`
Expected: PASS — 8 passed.

- [ ] **Step 5: Commit**

```bash
git add forward_testing/positions/__init__.py forward_testing/positions/exit_policy.py \
        tests/forward_testing/test_exit_policy.py
git commit -m "feat(forward-test): ExitPolicy registry + DEFAULT (direction-aware, pure)"
```

---

## Task 5: `Costs` + `atr_sma` + `MarketDataResolver`

**Files:**
- Create: `forward_testing/positions/costs.py`
- Create: `forward_testing/positions/market_data.py`
- Test: `tests/forward_testing/test_costs.py`
- Test: `tests/forward_testing/test_market_data.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/forward_testing/test_costs.py`:

```python
"""Costs value object + apply_costs (mirrors engine.strategies constants)."""
from forward_testing.positions.costs import Costs, apply_costs


def test_default_costs_match_engine():
    c = Costs()
    assert c.commission_buy == 0.0015
    assert c.commission_sell == 0.0025
    assert c.slippage == 0.001


def test_apply_costs_buy_adds_sell_subtracts():
    c = Costs()
    assert round(apply_costs(100.0, "BUY", c), 6) == round(100.0 * (1 + 0.0015 + 0.001), 6)
    assert round(apply_costs(100.0, "SELL", c), 6) == round(100.0 * (1 - 0.0025 - 0.001), 6)


def test_zero_costs_pass_through():
    z = Costs.zero()
    assert apply_costs(123.456, "BUY", z) == 123.456
    assert apply_costs(123.456, "SELL", z) == 123.456
```

Create `tests/forward_testing/test_market_data.py`:

```python
"""MarketDataResolver: ATR14 (SMA), next_open, bar — read from ohlcv."""
import sqlite3
from forward_testing.positions.market_data import atr_sma, MarketDataResolver
from tests.forward_testing.conftest import seed_ohlcv


def test_atr_sma_matches_simple_average_of_true_range():
    # 14 flat bars (h=11,l=9,c=10): TR=2 each -> ATR14=2.0
    rows = [(11, 9, 10)] * 14
    assert atr_sma(rows, 14) == 2.0


def test_atr_sma_none_when_insufficient_history():
    assert atr_sma([(11, 9, 10)] * 13, 14) is None


def test_atr_sma_uses_gap_vs_prev_close():
    rows = [(11, 9, 10), (12, 11, 11.5)]   # bar1 TR = max(1, |12-10|, |11-10|) = 2
    assert atr_sma(rows, 2) == 2.0          # mean(2, 2)


def _resolver(ft_db):
    conn = sqlite3.connect(ft_db)
    seed_ohlcv(conn, "BBCA", [
        ("2026-06-20", 100, 100.5, 99.5, 100, 1000),
        ("2026-06-21", 100, 100.5, 99.5, 100, 1000),
        ("2026-06-22", 100, 100.5, 99.5, 100, 1000),
        ("2026-06-23", 100, 100.5, 99.5, 100, 1000),
        ("2026-06-27", 105, 105.5, 104.5, 105, 1000),   # D+1 open after a 06-26 signal
    ])
    conn.commit(); conn.close()
    return MarketDataResolver(ft_db)


def test_resolver_next_open_returns_first_bar_after(ft_db):
    r = _resolver(ft_db)
    assert r.next_open("BBCA", "2026-06-26") == ("2026-06-27", 105)


def test_resolver_next_open_none_when_no_future_bar(ft_db):
    r = _resolver(ft_db)
    assert r.next_open("BBCA", "2026-06-29") is None


def test_resolver_bar_returns_ohlc(ft_db):
    r = _resolver(ft_db)
    assert r.bar("BBCA", "2026-06-27") == ("2026-06-27", 105, 105.5, 104.5, 105)
    assert r.bar("BBCA", "2026-06-30") is None


def test_resolver_atr14_none_with_too_few_bars(ft_db):
    r = _resolver(ft_db)   # only 5 bars seeded
    assert r.atr14("BBCA", "2026-06-27") is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/forward_testing/test_costs.py tests/forward_testing/test_market_data.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'forward_testing.positions.costs'`.

- [ ] **Step 3: Write minimal implementation**

Create `forward_testing/positions/costs.py`:

```python
"""Fill-cost economics. Defaults mirror engine.strategies (COMMISSION_BUY/SELL, SLIPPAGE).

side semantics: 'BUY' acquires (long open / short cover), 'SELL' disposes
(long close / short open). Injectable so tests can pass Costs.zero() for exact math.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Costs:
    commission_buy: float = 0.0015
    commission_sell: float = 0.0025
    slippage: float = 0.001

    @classmethod
    def zero(cls):
        return cls(0.0, 0.0, 0.0)


def apply_costs(price, side, costs):
    if side == "BUY":
        return price * (1 + costs.commission_buy + costs.slippage)
    return price * (1 - costs.commission_sell - costs.slippage)
```

Create `forward_testing/positions/market_data.py`:

```python
"""OHLCV reads + SMA-ATR for the SHADOW engine.

ATR is reimplemented locally (SMA convention, identical to engine.indicators.calc_atr)
so forward_testing stays stdlib-only — no pandas dependency.
"""
from forward_testing.storage.db import ft_get_db


def atr_sma(rows, period=14):
    """SMA-ATR. rows: list of (high, low, close) in ascending date order.

    Returns the mean of the last `period` True Ranges, or None if fewer than
    `period` bars are available (matches calc_atr's min_periods behaviour).
    """
    if len(rows) < period:
        return None
    trs = []
    prev_close = None
    for h, l, c in rows:
        if prev_close is None:
            tr = h - l
        else:
            tr = max(h - l, abs(h - prev_close), abs(l - prev_close))
        trs.append(tr)
        prev_close = c
    return sum(trs[-period:]) / period


class MarketDataResolver:
    """Reads ohlcv per ticker (cached for the run)."""

    def __init__(self, db_path):
        self.db_path = db_path
        self._cache = {}

    def _rows(self, ticker):
        if ticker not in self._cache:
            with ft_get_db(self.db_path) as c:
                self._cache[ticker] = [
                    dict(r) for r in c.execute(
                        "SELECT date, open, high, low, close FROM ohlcv "
                        "WHERE ticker=? ORDER BY date", (ticker,)
                    ).fetchall()
                ]
        return self._cache[ticker]

    def atr14(self, ticker, as_of):
        rows = [(r["high"], r["low"], r["close"]) for r in self._rows(ticker) if r["date"] <= as_of]
        return atr_sma(rows, 14)

    def next_open(self, ticker, after_date):
        for r in self._rows(ticker):
            if r["date"] > after_date:
                return (r["date"], r["open"])
        return None

    def bar(self, ticker, on_date):
        for r in self._rows(ticker):
            if r["date"] == on_date:
                return (r["date"], r["open"], r["high"], r["low"], r["close"])
        return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/forward_testing/test_costs.py tests/forward_testing/test_market_data.py -v`
Expected: PASS — 8 passed.

- [ ] **Step 5: Commit**

```bash
git add forward_testing/positions/costs.py forward_testing/positions/market_data.py \
        tests/forward_testing/test_costs.py tests/forward_testing/test_market_data.py
git commit -m "feat(forward-test): Costs value object + MarketDataResolver (SMA-ATR, ohlcv)"
```

---

## Task 6: `ExitEvaluator` — pure exit decision (the core math)

**Files:**
- Create: `forward_testing/positions/exit_evaluator.py`
- Test: `tests/forward_testing/test_exit_evaluator.py`

This is the heart of Phase 2. Pure: given a read-only position snapshot + one daily bar, return an `ExitDecision` or `None`. No I/O, no DB, no mutation. All direction-aware.

- [ ] **Step 1: Write the failing tests**

Create `tests/forward_testing/test_exit_evaluator.py`:

```python
"""ExitEvaluator: direction-aware SL/TP/trail/time, deterministic order, gap fills, metrics."""
from forward_testing.positions.exit_evaluator import PositionView, Bar, evaluate_exit
from forward_testing.positions.exit_policy import ExitPolicy

LONG_FIXED = ExitPolicy(sl_mult=1.0, tp_mult=2.0, min_rr=2.0)        # sl=99, tp=102 @ entry 100, atr 1
SHORT_TRAIL = ExitPolicy(trail_enable=True, trail_atr_mult=3.0, hold_days=10)  # 3xATR trail


def view(policy, direction, entry=100.0, atr=1.0, highest=100.0, lowest=100.0, hold=1):
    return PositionView(policy=policy, direction=direction, entry=entry, atr=atr,
                        highest_seen=highest, lowest_seen=lowest, hold_days=hold)


def bar(o, h, l, c, date="2026-06-27"):
    return Bar(date=date, open=o, high=h, low=l, close=c)


# ---- LONG fixed SL/TP ----

def test_long_stop_hit_level_fill():
    d = evaluate_exit(view(LONG_FIXED, "LONG"), bar(100, 100.5, 98.5, 99))
    assert d.reason == "SL"
    assert d.fill_price == 99.0                  # low breached 99, open 100 > 99 -> level fill
    assert d.r_multiple == -1.0                  # (99-100)/1
    assert d.pnl_pct == -0.01


def test_long_tp_hit_level_fill():
    d = evaluate_exit(view(LONG_FIXED, "LONG"), bar(100, 102.5, 99.9, 102))
    assert d.reason == "TP"
    assert d.fill_price == 102.0
    assert d.r_multiple == 2.0
    assert d.pnl_pct == 0.02


def test_long_stop_beats_tp_on_conflict_bar():
    # both SL (low<=99) and TP (high>=102) touched -> SL first
    d = evaluate_exit(view(LONG_FIXED, "LONG"), bar(100, 103, 98, 99))
    assert d.reason == "SL"
    assert d.fill_price == 99.0


def test_long_gap_below_stop_fills_at_open():
    d = evaluate_exit(view(LONG_FIXED, "LONG"), bar(97, 97.5, 96, 96.5))  # opens below SL
    assert d.reason == "SL"
    assert d.fill_price == 97.0                  # gap fill at open


def test_long_no_exit_returns_none():
    d = evaluate_exit(view(LONG_FIXED, "LONG", highest=100, lowest=100),
                      bar(100, 101, 99.5, 100.5))
    assert d is None                             # low 99.5 > sl 99; high 101 < tp 102


def test_long_mae_mfe_signed():
    d = evaluate_exit(view(LONG_FIXED, "LONG"), bar(100, 103, 98, 102))   # SL also hit
    assert d.mae_pct == -0.02                    # (98-100)/100
    assert d.mfe_pct == 0.03                     # (103-100)/100


# ---- LONG trailing (momentum-style: sl_mult + trail_enable) ----

def test_long_trail_ratchets_then_hits():
    pol = ExitPolicy(sl_mult=1.2, tp_mult=2.4, min_rr=2.0, trail_enable=True)
    # highest 100 -> stop 98.8. New high 103 -> stop ratchets to 103-1.2=100.8;
    # bar low 100.7 <= 100.8 -> trail hit at 100.8 (open 102 > stop -> level fill).
    d = evaluate_exit(view(pol, "LONG", highest=100, lowest=99), bar(102, 103, 100.7, 102.5))
    assert d.reason == "TRAIL"
    assert d.fill_price == 100.8


def test_long_trail_holds_when_low_above_ratcheted_stop():
    pol = ExitPolicy(sl_mult=1.2, tp_mult=2.4, min_rr=2.0, trail_enable=True)
    # highest 100 -> stop 98.8. New high 101 -> stop 99.8; low 100 > 99.8 -> hold.
    d = evaluate_exit(view(pol, "LONG", highest=100, lowest=99), bar(100, 101, 100, 100.5))
    assert d is None


# ---- SHORT pure trail (distribution DEFAULT) ----

def test_short_trail_ratchets_down_then_hits():
    # entry 100, trail 3 -> stop starts 103. bar1 low 97 -> new lowest 97 -> stop 100; high 99<100 hold.
    d = evaluate_exit(view(SHORT_TRAIL, "SHORT", highest=100, lowest=100),
                      bar(100, 99, 97, 98))
    assert d is None
    # next: lowest 97 -> stop 100; bar high 100.5 >= 100 -> TRAIL at 100 (level; open 99<100)
    d = evaluate_exit(view(SHORT_TRAIL, "SHORT", highest=100, lowest=97),
                      bar(99, 100.5, 99, 100))
    assert d.reason == "TRAIL"
    assert d.fill_price == 100.0
    assert d.r_multiple == 0.0                   # (100-100)/3


def test_short_pure_trail_favourable_move_holds():
    # favourable (low 97 -> stop 100) but high 99.5 < stop -> holds; pure trail has no TP.
    d = evaluate_exit(view(SHORT_TRAIL, "SHORT", highest=100, lowest=100),
                      bar(99, 99.5, 97, 98))
    assert d is None


def test_short_fixed_stop_gap_fills_at_open():
    pol = ExitPolicy(sl_mult=1.0, tp_mult=2.0, min_rr=2.0)   # short: sl=101, tp=98
    d = evaluate_exit(view(pol, "SHORT"), bar(103, 104, 102.5, 103))  # opens above SL 101
    assert d.reason == "SL"
    assert d.fill_price == 103.0                 # gap fill at open


# ---- TIME stop ----

def test_time_stop_exits_at_close_when_hold_reached():
    pol = ExitPolicy(sl_mult=1.0, tp_mult=2.0, min_rr=2.0, hold_days=5)
    d = evaluate_exit(view(pol, "LONG", hold=5), bar(100, 100.5, 99.8, 100.2))
    assert d.reason == "TIME"
    assert d.fill_price == 100.2                 # time exits at close


def test_stop_takes_precedence_over_time_on_same_bar():
    pol = ExitPolicy(sl_mult=1.0, tp_mult=2.0, min_rr=2.0, hold_days=1)
    d = evaluate_exit(view(pol, "LONG", hold=1), bar(100, 100.5, 98.5, 99))   # SL also hit
    assert d.reason == "SL"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/forward_testing/test_exit_evaluator.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'forward_testing.positions.exit_evaluator'`.

- [ ] **Step 3: Write minimal implementation**

Create `forward_testing/positions/exit_evaluator.py`:

```python
"""ExitEvaluator — pure exit decision for one open SHADOW position over one daily bar.

No I/O. Direction-aware (LONG/SHORT). Deterministic ordering on a conflict bar:
STOP (SL if fixed, TRAIL if trailing) -> TP -> TIME. Gap-aware fills.
Metrics are raw (pre-cost); the manager layers Costs on entry/exit for stored pnl_pct.
"""
from dataclasses import dataclass
from forward_testing.positions.exit_policy import ExitPolicy


@dataclass(frozen=True)
class Bar:
    date: str
    open: float
    high: float
    low: float
    close: float


@dataclass(frozen=True)
class PositionView:
    policy: ExitPolicy
    direction: str            # "LONG" / "SHORT"
    entry: float              # raw fill price (costs applied by manager at persist)
    atr: float                # atr14 at entry (fixed for the position's life)
    highest_seen: float
    lowest_seen: float
    hold_days: int


@dataclass(frozen=True)
class ExitDecision:
    reason: str               # SL / TP / TRAIL / TIME
    fill_price: float         # raw, gap-aware
    pnl_pct: float            # raw, direction-signed
    r_multiple: float         # realised / one_r
    mae_pct: float            # most adverse excursion (signed, <=0 typically)
    mfe_pct: float            # most favourable excursion (signed, >=0 typically)


def _stop_for(view, new_high, new_low):
    """Recompute the stop level for this bar and whether it is trailing."""
    lv = view.policy.initial_levels(view.direction, view.entry, view.atr)
    if lv.trailing:
        mult = lv.trail_mult
        if view.direction == "LONG":
            return new_high - mult * view.atr, True
        return new_low + mult * view.atr, True
    return lv.initial_stop, False


def evaluate_exit(view, bar):
    """Return an ExitDecision if the bar triggers an exit, else None."""
    long = view.direction == "LONG"
    sign = 1 if long else -1
    lv = view.policy.initial_levels(view.direction, view.entry, view.atr)

    new_high = max(view.highest_seen, bar.high)
    new_low = min(view.lowest_seen, bar.low)
    mae = ((new_low - view.entry) / view.entry) if long else ((new_high - view.entry) / view.entry)
    mfe = ((new_high - view.entry) / view.entry) if long else ((new_low - view.entry) / view.entry)

    stop, trailing = _stop_for(view, new_high, new_low)

    def realised(fill):
        return sign * (fill - view.entry)

    # 1) STOP (SL/TRAIL)
    stop_hit = (bar.low <= stop) if long else (bar.high >= stop)
    if stop_hit:
        gap = (bar.open <= stop) if long else (bar.open >= stop)
        fill = bar.open if gap else stop
        reason = "TRAIL" if trailing else "SL"
        return ExitDecision(reason, fill, realised(fill) / view.entry,
                            realised(fill) / lv.one_r, mae, mfe)

    # 2) TP (fixed policies only)
    if lv.tp_price is not None:
        tp_hit = (bar.high >= lv.tp_price) if long else (bar.low <= lv.tp_price)
        if tp_hit:
            gap = (bar.open >= lv.tp_price) if long else (bar.open <= lv.tp_price)
            fill = bar.open if gap else lv.tp_price
            return ExitDecision("TP", fill, realised(fill) / view.entry,
                                realised(fill) / lv.one_r, mae, mfe)

    # 3) TIME
    if view.policy.hold_days is not None and view.hold_days >= view.policy.hold_days:
        fill = bar.close
        return ExitDecision("TIME", fill, realised(fill) / view.entry,
                            realised(fill) / lv.one_r, mae, mfe)

    return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/forward_testing/test_exit_evaluator.py -v`
Expected: PASS — all exit-math cases green.

- [ ] **Step 5: Commit**

```bash
git add forward_testing/positions/exit_evaluator.py tests/forward_testing/test_exit_evaluator.py
git commit -m "feat(forward-test): ExitEvaluator — pure direction-aware exit math"
```

---

## Task 7: `ShadowPositionManager` — OPEN pass

**Files:**
- Create: `forward_testing/positions/shadow_manager.py`
- Test: `tests/forward_testing/test_shadow_manager.py`

- [ ] **Step 1: Write the failing tests (open pass)**

Create `tests/forward_testing/test_shadow_manager.py`:

```python
"""ShadowPositionManager: open pass (next-open fill, policy levels, lifecycle)."""
import sqlite3
from forward_testing.storage.repo import FTRepo
from forward_testing.lifecycle.manager import LifecycleManager
from forward_testing.positions.market_data import MarketDataResolver
from forward_testing.positions.exit_policy import ExitPolicyRegistry
from forward_testing.positions.costs import Costs
from forward_testing.positions.shadow_manager import ShadowPositionManager
from forward_testing.adapters.signal_adapter import SignalAdapter
from tests.forward_testing.conftest import seed_ohlcv, seed_signal

# Flat bars (100, 100.5, 99.5, 100): TR = 1 -> ATR14 = 1. vol_weighted LONG -> sl 99, tp 102.
FLAT = [("2026-06-%02d" % d, 100, 100.5, 99.5, 100, 1000) for d in range(1, 27)]


def _mgr(ft_db, costs=None):
    return ShadowPositionManager(
        repo=FTRepo(ft_db), resolver=MarketDataResolver(ft_db),
        registry=ExitPolicyRegistry(), lifecycle=LifecycleManager(FTRepo(ft_db)),
        db_path=ft_db, costs=costs or Costs.zero(),
    )


def _ingest_one(ft_db, repo, ticker, strategy, direction):
    conn = sqlite3.connect(ft_db)
    seed_signal(conn, "2026-06-26 16:15", ticker, strategy, direction=direction)
    conn.commit(); conn.close()
    SignalAdapter(repo, ft_db).ingest("2026-06-26")
    return repo.get_signals_by_state("GENERATED", track="SHADOW")[0]["id"]


def test_open_pass_fills_at_next_open_and_sets_levels(ft_db, repo):
    conn = sqlite3.connect(ft_db)
    seed_ohlcv(conn, "BBCA", FLAT + [("2026-06-27", 100, 100.5, 99.5, 100, 1000)])
    conn.commit(); conn.close()
    sid = _ingest_one(ft_db, repo, "BBCA", "vol_weighted", "BUY")

    _mgr(ft_db).run("2026-06-27")

    pos = repo.get_shadow_position(sid)
    assert pos["status"] == "OPEN"
    assert pos["entry_date"] == "2026-06-27"
    assert pos["entry_price"] == 100.0          # zero costs
    assert pos["atr14"] == 1.0
    assert pos["sl_price"] == 99.0              # 100 - 1.0*1
    assert pos["tp_price"] == 102.0             # 100 + 2.0*1


def test_open_pass_transitions_lifecycle_to_opened(ft_db, repo):
    conn = sqlite3.connect(ft_db)
    seed_ohlcv(conn, "BBCA", FLAT + [("2026-06-27", 100, 100.5, 99.5, 100, 1000)])
    conn.commit(); conn.close()
    sid = _ingest_one(ft_db, repo, "BBCA", "vol_weighted", "BUY")
    _mgr(ft_db).run("2026-06-27")
    assert repo.get_signal_state(sid) == "OPENED"


def test_open_pass_skips_when_next_open_not_yet_available(ft_db, repo):
    conn = sqlite3.connect(ft_db)
    seed_ohlcv(conn, "BBCA", FLAT)              # no 06-27 bar
    conn.commit(); conn.close()
    sid = _ingest_one(ft_db, repo, "BBCA", "vol_weighted", "BUY")
    _mgr(ft_db).run("2026-06-26")               # D+1 not available
    assert repo.get_signal_state(sid) == "GENERATED"   # deferred
    assert repo.get_shadow_position(sid) is None


def test_open_pass_skips_when_atr_history_insufficient(ft_db, repo):
    conn = sqlite3.connect(ft_db)
    # only ~7 bars up to 06-26 -> atr14 None; but 06-27 bar exists (so next_open resolves)
    seed_ohlcv(conn, "BBCA",
               [("2026-06-%02d" % d, 100, 100.5, 99.5, 100, 1000) for d in range(20, 28)])
    conn.commit(); conn.close()
    sid = _ingest_one(ft_db, repo, "BBCA", "vol_weighted", "BUY")
    _mgr(ft_db).run("2026-06-27")
    assert repo.get_shadow_position(sid) is None        # not opened blind
    assert repo.get_signal_state(sid) == "GENERATED"    # stays deferred
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/forward_testing/test_shadow_manager.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'forward_testing.positions.shadow_manager'`.

- [ ] **Step 3: Write minimal implementation**

Create `forward_testing/positions/shadow_manager.py`:

```python
"""ShadowPositionManager — paper-trades every SHADOW signal to a closed round-trip.

Two idempotent passes per run_date: OPEN (GENERATED -> OPENED at next-open fill),
then EXIT-CHECK (OPEN positions evaluated against the run_date bar -> ft_shadow_trade).
All writes are short compute-then-write transactions via FTRepo (DB-lock discipline).
"""
from forward_testing.positions.costs import Costs, apply_costs
from forward_testing.positions.exit_evaluator import PositionView, evaluate_exit
from forward_testing.lifecycle.states import SignalState


def _default_suspension_checker(db_path):
    """Returns (ticker, on_date) -> bool using suspension_events if the table exists.

    A ticker is suspended on on_date when a 'suspension'-classified row covers it:
    last_normal_date < on_date <= resume_date (or resume_date unknown).
    """
    import sqlite3

    def check(ticker, on_date):
        conn = sqlite3.connect(db_path, timeout=30)
        try:
            row = conn.execute(
                "SELECT 1 FROM suspension_events WHERE ticker=? AND classification='suspension' "
                "AND ? > last_normal_date AND (resume_date IS NULL OR ? <= resume_date) LIMIT 1",
                (ticker, on_date, on_date),
            ).fetchone()
            return row is not None
        except sqlite3.OperationalError:
            return False  # table missing -> treat as not suspended
        finally:
            conn.close()
    return check


class ShadowPositionManager:
    def __init__(self, repo, resolver, registry, lifecycle, db_path,
                 costs=None, suspension_checker=None):
        self.repo = repo
        self.resolver = resolver
        self.registry = registry
        self.lifecycle = lifecycle
        self.db_path = db_path
        self.costs = costs if costs is not None else Costs()
        self._suspended = suspension_checker or _default_suspension_checker(db_path)

    # ---- public API ----
    def run(self, run_date):
        run_id = self.repo.create_run(run_date, kind="SHADOW_EOD")
        self._open_pass(run_date)
        self._exit_pass(run_date)
        self.repo.finish_run(run_id, "OK")

    # ---- OPEN pass ----
    def _open_pass(self, run_date):
        for sig in self.repo.get_signals_by_state(SignalState.GENERATED.value, track="SHADOW"):
            self._maybe_open(sig, run_date)

    def _maybe_open(self, sig, run_date):
        signal_id = sig["id"]
        if self.repo.get_shadow_position(signal_id) is not None:
            return  # already opened (idempotent)

        nxt = self.resolver.next_open(sig["ticker"], sig["signal_date"])
        if nxt is None:
            return  # D+1 bar not yet available -> defer
        entry_date, raw_entry = nxt

        atr = self.resolver.atr14(sig["ticker"], sig["signal_date"])
        if atr is None:
            return  # insufficient history -> do not open blind

        policy = self.registry.get(sig["strategy"])
        open_side = "BUY" if sig["direction"] == "LONG" else "SELL"
        entry_price = apply_costs(raw_entry, open_side, self.costs)
        # Levels/anchors derive from the stored (cost-adjusted) entry so they match what
        # ExitEvaluator recomputes each pass from pos["entry_price"].
        lv = policy.initial_levels(sig["direction"], entry_price, atr)

        self.repo.open_shadow_position(
            signal_id=signal_id, ticker=sig["ticker"], strategy=sig["strategy"],
            direction=sig["direction"], entry_date=entry_date, entry_price=entry_price,
            atr14=atr, sl_price=lv.sl_price, tp_price=lv.tp_price,
            trail_atr_mult=policy.trail_atr_mult, trail_anchor=entry_price,
            highest_seen=entry_price, lowest_seen=entry_price,
        )
        self.lifecycle.transition(signal_id, SignalState.OPENED, run_date, actor="shadow_mgr",
                                  reason="next-open-fill")

        # Evaluate the entry bar itself (a gap can exit on day one).
        self._check_one(signal_id, entry_date)

    # ---- EXIT pass (replaces the stubs below in Task 8) ----
    def _exit_pass(self, run_date):
        return  # TEMPORARY STUB — replaced in Task 8 Step 3

    def _check_one(self, signal_id, on_date):
        return  # TEMPORARY STUB — replaced in Task 8 Step 3
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/forward_testing/test_shadow_manager.py -v`
Expected: PASS — the four open-pass tests green (positions opened, lifecycle OPENED, deferred when no D+1/ATR).

- [ ] **Step 5: Commit**

```bash
git add forward_testing/positions/shadow_manager.py tests/forward_testing/test_shadow_manager.py
git commit -m "feat(forward-test): ShadowPositionManager OPEN pass (next-open fill, GENERATED->OPENED)"
```

---

## Task 8: `ShadowPositionManager` — EXIT pass + safety + idempotency

**Files:**
- Modify: `forward_testing/positions/shadow_manager.py`
- Modify: `tests/forward_testing/test_shadow_manager.py`

- [ ] **Step 1: Append the failing tests (exit pass + safety + idempotency)**

Append to `tests/forward_testing/test_shadow_manager.py`:

```python
def test_exit_pass_closes_on_tp_and_writes_trade(ft_db, repo):
    conn = sqlite3.connect(ft_db)
    seed_ohlcv(conn, "BBCA", FLAT + [
        ("2026-06-27", 100, 100.5, 99.5, 100, 1000),    # entry bar; no exit
        ("2026-06-28", 100, 102.5, 99.5, 102, 1000)])    # high 102.5 >= tp 102 -> TP
    conn.commit(); conn.close()
    sid = _ingest_one(ft_db, repo, "BBCA", "vol_weighted", "BUY")

    mgr = _mgr(ft_db)
    mgr.run("2026-06-27")   # opens at 100
    mgr.run("2026-06-28")   # TP hit
    trade = repo.get_shadow_trade(sid)
    assert trade["exit_reason"] == "TP"
    assert trade["exit_price"] == 102.0
    assert round(trade["r_multiple"], 6) == 2.0          # (102-100)/1
    assert round(trade["pnl_pct"], 6) == round((102 - 100) / 100, 6)
    assert repo.get_signal_state(sid) == "EXITED"
    assert repo.get_shadow_position(sid)["status"] == "CLOSED"


def test_exit_pass_holds_then_updates_extremes_when_no_exit(ft_db, repo):
    conn = sqlite3.connect(ft_db)
    seed_ohlcv(conn, "BBCA", FLAT + [
        ("2026-06-27", 100, 100.5, 99.5, 100, 1000),
        ("2026-06-28", 100, 101, 99.8, 100.5, 1000)])     # no SL/TP hit
    conn.commit(); conn.close()
    sid = _ingest_one(ft_db, repo, "BBCA", "vol_weighted", "BUY")
    mgr = _mgr(ft_db)
    mgr.run("2026-06-27")
    mgr.run("2026-06-28")
    pos = repo.get_shadow_position(sid)
    assert pos["status"] == "OPEN"
    assert pos["highest_seen"] == 101.0
    assert pos["hold_days"] == 2


def test_missing_bar_holds_without_force_exit(ft_db, repo):
    conn = sqlite3.connect(ft_db)
    seed_ohlcv(conn, "BBCA", FLAT + [("2026-06-27", 100, 100.5, 99.5, 100, 1000)])  # no 06-28 bar
    conn.commit(); conn.close()
    sid = _ingest_one(ft_db, repo, "BBCA", "vol_weighted", "BUY")
    mgr = _mgr(ft_db)
    mgr.run("2026-06-27")
    mgr.run("2026-06-28")   # no ohlcv bar -> hold
    assert repo.get_shadow_position(sid)["status"] == "OPEN"
    assert repo.get_shadow_trade(sid) is None


def test_suspended_ticker_holds(ft_db, repo):
    conn = sqlite3.connect(ft_db)
    seed_ohlcv(conn, "BBCA", FLAT + [
        ("2026-06-27", 100, 100.5, 99.5, 100, 1000),
        ("2026-06-28", 100, 200, 99.5, 199, 1000)])       # would TP hugely, but suspended
    conn.execute("INSERT INTO suspension_events (ticker,last_normal_date,resume_date,classification) "
                 "VALUES ('BBCA','2026-06-27','2026-07-05','suspension')")
    conn.commit(); conn.close()
    sid = _ingest_one(ft_db, repo, "BBCA", "vol_weighted", "BUY")
    mgr = _mgr(ft_db)
    mgr.run("2026-06-27")   # 06-27 not suspended yet (strict > last_normal_date) -> opens
    mgr.run("2026-06-28")   # suspended -> hold despite TP-bar
    assert repo.get_shadow_position(sid)["status"] == "OPEN"
    assert repo.get_shadow_trade(sid) is None


def test_rerun_is_idempotent(ft_db, repo):
    conn = sqlite3.connect(ft_db)
    seed_ohlcv(conn, "BBCA", FLAT + [
        ("2026-06-27", 100, 100.5, 99.5, 100, 1000),
        ("2026-06-28", 100, 102.5, 99.5, 102, 1000)])
    conn.commit(); conn.close()
    sid = _ingest_one(ft_db, repo, "BBCA", "vol_weighted", "BUY")
    mgr = _mgr(ft_db)
    mgr.run("2026-06-27")
    mgr.run("2026-06-28")   # closes on TP
    mgr.run("2026-06-28")   # re-run -> no-op
    conn = sqlite3.connect(ft_db)
    n_trades = conn.execute("SELECT COUNT(*) FROM ft_shadow_trade").fetchone()[0]
    conn.close()
    assert n_trades == 1
    assert repo.get_signal_state(sid) == "EXITED"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/forward_testing/test_shadow_manager.py -k "exit_pass or holds_then or missing_bar or suspended or idempotent" -v`
Expected: FAIL — exit-pass tests error or positions never close (stubs still in place).

- [ ] **Step 3: Replace the stubs with the real EXIT pass**

In `forward_testing/positions/shadow_manager.py`, **delete** the temporary `_exit_pass`/`_check_one` stub methods from Task 7 and add the real implementation in their place:

```python
    # ---- EXIT pass ----
    def _exit_pass(self, run_date):
        for pos in self.repo.get_open_shadow_positions():
            if run_date < pos["entry_date"]:
                continue  # not yet (guard)
            self._check_one(pos["signal_id"], run_date)

    def _check_one(self, signal_id, on_date):
        pos = self.repo.get_shadow_position(signal_id)
        if pos is None or pos["status"] != "OPEN":
            return  # idempotent: already closed

        if self._suspended(pos["ticker"], on_date):
            return  # suspension-hold (§9); full CA handling is Phase 3

        bar_tuple = self.resolver.bar(pos["ticker"], on_date)
        if bar_tuple is None:
            return  # missing ohlcv -> hold + flag, never force-exit (§5.4)

        from forward_testing.positions.exit_evaluator import Bar
        bar = Bar(date=bar_tuple[0], open=bar_tuple[1], high=bar_tuple[2],
                  low=bar_tuple[3], close=bar_tuple[4])

        policy = self.registry.get(pos["strategy"])
        new_hold = pos["hold_days"] + 1
        view = PositionView(
            policy=policy, direction=pos["direction"], entry=pos["entry_price"],
            atr=pos["atr14"], highest_seen=pos["highest_seen"], lowest_seen=pos["lowest_seen"],
            hold_days=new_hold,
        )
        decision = evaluate_exit(view, bar)
        if decision is None:
            new_high = max(pos["highest_seen"], bar.high)
            new_low = min(pos["lowest_seen"], bar.low)
            self.repo.update_shadow_position(signal_id, new_high, new_low, new_hold)
            return

        # Close: persist cost-adjusted entry/exit + raw r/mae/mfe.
        close_side = "SELL" if pos["direction"] == "LONG" else "BUY"
        exit_price = apply_costs(decision.fill_price, close_side, self.costs)
        entry = pos["entry_price"]
        pnl_pct = ((exit_price - entry) / entry) if pos["direction"] == "LONG" \
                  else ((entry - exit_price) / entry)
        self.repo.close_shadow_position(signal_id, on_date, exit_price, decision.reason)
        self.repo.insert_shadow_trade(
            signal_id=signal_id, ticker=pos["ticker"], strategy=pos["strategy"],
            direction=pos["direction"], signal_date=pos["entry_date"], entry_date=pos["entry_date"],
            entry_price=entry, exit_date=on_date, exit_price=exit_price, exit_reason=decision.reason,
            pnl_pct=pnl_pct, r_multiple=decision.r_multiple, hold_days=new_hold,
            mae_pct=decision.mae_pct, mfe_pct=decision.mfe_pct,
        )
        self.lifecycle.transition(signal_id, SignalState.EXITED, on_date, actor="shadow_mgr",
                                  reason=decision.reason)
```

> **Note on `signal_date`:** `ft_shadow_position` does not store the original signal date, so the trade's `signal_date` is set to `entry_date` as a best-available proxy. If Phase 4 attribution needs the true signal date, add a `signal_date` column to `ft_shadow_position` in Task 2 and carry it through — not required for Phase-2 metrics.

- [ ] **Step 4: Run the full manager suite to verify it passes**

Run: `pytest tests/forward_testing/test_shadow_manager.py -v`
Expected: PASS — all open + exit + safety + idempotency tests green.

- [ ] **Step 5: Commit**

```bash
git add forward_testing/positions/shadow_manager.py tests/forward_testing/test_shadow_manager.py
git commit -m "feat(forward-test): ShadowPositionManager EXIT pass + safety holds + idempotency"
```

---

## Task 9: Phase-2 end-to-end + full suite + Definition of Done

**Files:**
- Test: `tests/forward_testing/test_phase2_e2e.py`

- [ ] **Step 1: Write the end-to-end test**

Create `tests/forward_testing/test_phase2_e2e.py`:

```python
"""Phase-2 end-to-end: ingest -> open -> exit across a LONG (TP) and a SHORT (TRAIL)."""
import sqlite3
from forward_testing.adapters.signal_adapter import SignalAdapter
from forward_testing.positions.market_data import MarketDataResolver
from forward_testing.positions.exit_policy import ExitPolicyRegistry
from forward_testing.positions.costs import Costs
from forward_testing.positions.shadow_manager import ShadowPositionManager
from forward_testing.storage.repo import FTRepo
from forward_testing.lifecycle.manager import LifecycleManager
from tests.forward_testing.conftest import seed_ohlcv, seed_signal

LONG_FLAT = [("2026-06-%02d" % d, 100, 100.5, 99.5, 100, 1000) for d in range(1, 27)]   # ATR 1
SHORT_FLAT = [("2026-06-%02d" % d, 200, 200.5, 199.5, 200, 1000) for d in range(1, 27)]  # ATR 1


def test_phase2_full_flow_long_tp_and_short_trail(ft_db, repo):
    conn = sqlite3.connect(ft_db)
    seed_signal(conn, "2026-06-26 16:15", "BBCA", "vol_weighted", direction="BUY")
    seed_signal(conn, "2026-06-26 16:15", "UNVR", "distribution", direction="SELL")
    # LONG: entry 100 on 06-27, TP 102 on 06-28.
    seed_ohlcv(conn, "BBCA", LONG_FLAT + [
        ("2026-06-27", 100, 100.5, 99.5, 100, 1000),
        ("2026-06-28", 100, 102.5, 99.5, 102, 1000)])
    # SHORT distribution (trail 3xATR=3): entry 200 on 06-27; price falls (lowest 195 ->
    # stop 198) then rebounds; 06-28 high 199 >= 198 -> TRAIL at 198 (a small short win).
    seed_ohlcv(conn, "UNVR", SHORT_FLAT + [
        ("2026-06-27", 200, 196, 195, 195.5, 1000),   # lowest 195 -> stop 198; high 196<198 hold
        ("2026-06-28", 195.5, 199, 195, 198, 1000)])   # high 199 >= 198 -> TRAIL @ 198
    conn.commit(); conn.close()

    SignalAdapter(repo, ft_db).ingest("2026-06-26")   # 2 GENERATED SHADOW signals
    mgr = ShadowPositionManager(repo, MarketDataResolver(ft_db), ExitPolicyRegistry(),
                                LifecycleManager(repo), ft_db, costs=Costs.zero())
    mgr.run("2026-06-27")   # open both; entry-bar no exit
    mgr.run("2026-06-28")   # BBCA -> TP; UNVR -> TRAIL

    conn = sqlite3.connect(ft_db)
    trades = {r["ticker"]: dict(r) for r in conn.execute("SELECT * FROM ft_shadow_trade").fetchall()}
    conn.close()

    assert set(trades) == {"BBCA", "UNVR"}
    assert trades["BBCA"]["exit_reason"] == "TP"
    assert trades["BBCA"]["direction"] == "LONG"
    assert round(trades["BBCA"]["r_multiple"], 6) == 2.0
    assert trades["UNVR"]["exit_reason"] == "TRAIL"
    assert trades["UNVR"]["direction"] == "SHORT"
    assert round(trades["UNVR"]["exit_price"], 6) == 198.0
    assert round(trades["UNVR"]["r_multiple"], 6) == round((200 - 198) / 3, 6)   # +0.667R

    # idempotent re-run
    mgr.run("2026-06-28")
    conn = sqlite3.connect(ft_db)
    assert conn.execute("SELECT COUNT(*) FROM ft_shadow_trade").fetchone()[0] == 2
    conn.close()
```

- [ ] **Step 2: Run the e2e test**

Run: `pytest tests/forward_testing/test_phase2_e2e.py -v`
Expected: PASS — both a LONG/TP and a SHORT/TRAIL round-trip recorded; re-run idempotent.

- [ ] **Step 3: Run the whole forward_testing suite**

Run: `pytest tests/forward_testing/ -v`
Expected: PASS — all Phase 1 + Phase 2 tests green.

- [ ] **Step 4: Run the existing repo suite to confirm no regressions**

Run: `pytest tests/ -q`
Expected: PASS — Phase 2 is additive (one lifecycle edge, new tables/files; `data/db.py` unchanged).

- [ ] **Step 5: Apply Phase-2 schema to the production DB + smoke**

Run:
```bash
venv/bin/python -c "from forward_testing.storage.db import init_ft_tables; init_ft_tables()"
sqlite3 data/walkforward.db ".tables" | tr ' ' '\n' | grep '^ft_shadow'
```
Expected: both `ft_shadow_position` and `ft_shadow_trade` listed (idempotent — Phase-1 `ft_*` tables unaffected).

Then a one-off prod smoke on the already-ingested 2026-06-26 cohort:
```bash
venv/bin/python -c "
from forward_testing.storage.repo import FTRepo
from forward_testing.lifecycle.manager import LifecycleManager
from forward_testing.positions.market_data import MarketDataResolver
from forward_testing.positions.exit_policy import ExitPolicyRegistry
from forward_testing.positions.shadow_manager import ShadowPositionManager
DB='data/walkforward.db'
repo=FTRepo(DB)
ShadowPositionManager(repo, MarketDataResolver(DB), ExitPolicyRegistry(),
                     LifecycleManager(repo), DB).run('2026-06-27')
import sqlite3
c=sqlite3.connect(DB)
print('open  ', c.execute(\"SELECT COUNT(*) FROM ft_shadow_position WHERE status='OPEN'\").fetchone()[0])
print('closed', c.execute(\"SELECT COUNT(*) FROM ft_shadow_position WHERE status='CLOSED'\").fetchone()[0])
print('trades', c.execute('SELECT COUNT(*) FROM ft_shadow_trade').fetchone()[0])
print('by_reason', c.execute('SELECT exit_reason, COUNT(*) FROM ft_shadow_trade GROUP BY exit_reason').fetchall())
"
```
Expected: numbers > 0 where `ohlcv` permits (the 2026-06-26 signals open on 2026-06-27); no `database is locked`. Re-running is a no-op (idempotent).

- [ ] **Step 6: Commit**

```bash
git add tests/forward_testing/test_phase2_e2e.py
git commit -m "test(forward-test): Phase-2 end-to-end (ingest -> open -> exit, long TP + short trail)"
```

---

## Definition of Done (Phase 2)

- [ ] All 9 tasks committed on the feature branch.
- [ ] `pytest tests/forward_testing/ -v` fully green (Phase 1 + Phase 2).
- [ ] `pytest tests/ -q` (existing repo suite) still passes — Phase 2 is additive.
- [ ] `init_ft_tables()` run against production `data/walkforward.db`; `ft_shadow_position` + `ft_shadow_trade` exist; a `ShadowPositionManager.run(...)` smoke opens/closes signals with no DB lock and an idempotent re-run.
- [ ] `ft_shadow_trade` holds at least one LONG (TP/SL) and one SHORT (TRAIL) round-trip with sensible `pnl_pct` / `r_multiple`.

---

## Self-Review

**1. Spec coverage (spec section → task):**
- §4.1/4.2 tables (`ft_shadow_position`, `ft_shadow_trade`) → Task 2 (schema), Task 3 (DAOs).
- §5.1 `ExitPolicyRegistry` + per-strategy table + DEFAULT → Task 4.
- §5.2 `MarketDataResolver` (ATR14, next_open, bar) → Task 5 (local `atr_sma` per the flagged deviation).
- §5.3 `ShadowPositionManager` open + exit passes → Tasks 7, 8.
- §6 exit semantics (direction-aware SL/TP/trail/time, deterministic order, gap fill, r-multiple/mae/mfe) → Task 6 (`ExitEvaluator`, pure) consumed by Task 8.
- §7 lifecycle `GENERATED → OPENED` bypass → Task 1.
- §8 EOD run flow + idempotency → Tasks 7, 8, 9.
- §9 error handling (missing ohlcv hold, suspension hold, missing-ATR skip, compute-then-write) → Tasks 7, 8.
- §10 testing (unit + integration) → Tasks 1–9.
- **Gaps by design (deferred):** PORTFOLIO/ft_position/fill/mark + sizing/equity (Phase 3), full CA cost-basis (Phase 3), ranker (Phase 3), performance/scoreboard (Phase 4–5), scheduler (Phase 7), partial exits (YAGNI).

**2. Placeholder scan:** none. Every step has complete code. The Task 7 `_exit_pass`/`_check_one` stubs are explicitly labelled temporary and replaced verbatim in Task 8 Step 3 (a documented two-task build of one class, not a placeholder). Test math is pinned: flat bars `(P, P+0.5, P-0.5, P)` ⇒ TR=1 ⇒ ATR14=1, giving deterministic levels (vol_weighted LONG @ 100 → sl 99, tp 102) and a verified SHORT-trail outcome (entry 200 → TRAIL @ 198, +0.667R).

**3. Type/name consistency:** `ExitPolicy`/`InitialLevels` (Task 4) consumed identically by `ExitEvaluator` (Task 6) and `ShadowPositionManager` (Tasks 7–8). `PositionView`/`Bar`/`ExitDecision` (Task 6) field names match Task 8's construction and the test assertions. DAO names (`open_shadow_position`, `get_shadow_position`, `get_open_shadow_positions`, `update_shadow_position`, `close_shadow_position`, `insert_shadow_trade`, `get_shadow_trade`, `get_signals_by_state`) consistent across `repo.py`, manager, and tests. `MarketDataResolver.atr14/next_open/bar` consistent across Task 5, manager, tests. `Costs`/`apply_costs` consistent across Task 5 and manager. `insert_shadow_trade` parameter order matches the DAO (Task 3) and the manager call (Task 8): `signal_id, ticker, strategy, direction, signal_date, entry_date, entry_price, exit_date, exit_price, exit_reason, pnl_pct, r_multiple, hold_days, mae_pct, mfe_pct`.

---

*End of Phase 2 plan. Phases 3–7 are separate plans, written after Phase 2 ships and the SHADOW spine is verified against the production database.*
