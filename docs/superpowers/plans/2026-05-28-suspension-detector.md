# G2 — Suspension / Data-Gap Detector — Implementation Plan

> ✅ SHIPPED 2026-05-28 — 15 unit tests, 1,477 suspension events detected. See `engine/suspension_detector.py`.

**Goal:** Build a standalone module that scans the project's OHLCV history for trading-day gaps, classifies each as a real suspension or a benign data-fetch gap by price discontinuity, persists events to SQLite, and exposes a small read API for downstream consumers (G8/G9/etc).

**Architecture:** One new module (`engine/suspension_detector.py`) with three layers — a pure `detect_gaps(df)` function for synthetic-fixture testability, an I/O `scan_all(ohlcv_map)` that persists to a new `suspension_events` table, and a `get_status(ticker)` read API. Schema is applied inline via `CREATE TABLE IF NOT EXISTS`, matching the rest of the project. One fail-soft call site added at the end of `fetch_latest()` in `scheduler.py`.

**Tech Stack:** Python 3, pandas, sqlite3, pytest. Reuses `engine/calendar_filter.is_trading_day` for IDX-calendar-aware gap counting.

**Spec:** [`docs/superpowers/specs/2026-05-28-suspension-detector-design.md`](../specs/2026-05-28-suspension-detector-design.md)

---

## File Structure

| File | Status | Responsibility |
|---|---|---|
| `engine/suspension_detector.py` | Create | The whole feature: `GapEvent`, `detect_gaps`, `scan_all`, `get_status`, `_ensure_schema`, helpers. ~180 lines. |
| `tests/test_suspension_detector.py` | Create | All unit tests + one in-memory-SQLite round-trip. ~120 lines. |
| `scheduler.py` | Modify | Add a fail-soft call to `scan_all()` at the end of the successful branch of `fetch_latest()` (around line 58). |

Everything else (alerts, chart markers, indicator math) is explicit non-goal per the spec.

---

## Conventions

- **Run tests from repo root**: `pytest tests/test_suspension_detector.py -v`. `pytest.ini` sets `testpaths = tests`.
- **Commit prefix**: `feat(g2):` for code, `test(g2):` if commit is tests-only, `chore(g2):` for wiring.
- **Each commit must leave the test suite green.** Tests-first within each task; commit after green.
- **Dates in tests**: use 2026 dates (the IDX holiday calendar in `engine/calendar_filter.py` is hard-coded for 2026).
- **`detected_at` parameter**: every function that stamps `detected_at` accepts an override so tests can assert exact row contents.

---

## Task 1: Module skeleton + `GapEvent` + empty-input behavior

**Files:**
- Create: `engine/suspension_detector.py`
- Create: `tests/test_suspension_detector.py`

- [x] **Step 1: Write the failing tests**

Create `tests/test_suspension_detector.py`:

```python
import pandas as pd
import pytest

from engine.suspension_detector import GapEvent, detect_gaps


def _df(rows):
    """Build an OHLCV dataframe from a list of (date, o, h, l, c, v) tuples."""
    return pd.DataFrame(rows, columns=["date", "open", "high", "low", "close", "volume"])


def test_gapevent_dataclass_fields():
    ev = GapEvent(
        ticker="X",
        last_normal_date="2026-01-05",
        resume_date="2026-01-12",
        missing_td=4,
        gap_pct=-0.15,
        classification="suspension",
        detected_at="2026-05-28T00:00:00+00:00",
    )
    assert ev.ticker == "X"
    assert ev.missing_td == 4
    assert ev.classification == "suspension"


def test_detect_gaps_empty_df_returns_empty_list():
    assert detect_gaps(pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])) == []


def test_detect_gaps_single_row_returns_empty_list():
    df = _df([("2026-04-13", 100.0, 101.0, 99.0, 100.0, 1000)])
    assert detect_gaps(df) == []


def test_detect_gaps_none_returns_empty_list():
    assert detect_gaps(None) == []
```

- [x] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_suspension_detector.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'engine.suspension_detector'`.

- [x] **Step 3: Write the minimal module**

Create `engine/suspension_detector.py`:

```python
"""
suspension_detector.py — Detects trading suspensions and data-fetch gaps in
OHLCV history. See docs/superpowers/specs/2026-05-28-suspension-detector-design.md.

Three layers:
  detect_gaps(df, ...)  — pure, no I/O, returns list[GapEvent]
  scan_all(...)         — runs detect_gaps across all tickers, persists to SQLite
  get_status(ticker)    — read API for downstream consumers
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import pandas as pd


@dataclass
class GapEvent:
    ticker: str
    last_normal_date: str   # ISO date (YYYY-MM-DD)
    resume_date: str        # ISO date (YYYY-MM-DD)
    missing_td: int         # trading-day count, calendar-aware
    gap_pct: float          # (resume_open - last_close) / last_close
    classification: str     # 'suspension' | 'data_gap'
    detected_at: str        # ISO timestamp


def detect_gaps(
    df: Optional[pd.DataFrame],
    *,
    threshold_days: int = 3,
    price_jump_pct: float = 10.0,
    detected_at: Optional[str] = None,
) -> List[GapEvent]:
    """Detect trading-day gaps in df. Pure — no DB, no I/O."""
    if df is None or len(df) < 2:
        return []
    return []
```

- [x] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_suspension_detector.py -v`
Expected: PASS (4 tests).

- [x] **Step 5: Commit**

```bash
git add engine/suspension_detector.py tests/test_suspension_detector.py
git commit -m "feat(g2): suspension_detector module skeleton + GapEvent dataclass"
```

---

## Task 2: Detect a real suspension (BRPT-shaped fixture)

This task forces the core detection loop: iterate consecutive bars, count calendar-aware missing trading days using `is_trading_day`, build a `GapEvent` when the threshold is exceeded and the price gap is large.

**Files:**
- Modify: `engine/suspension_detector.py`
- Modify: `tests/test_suspension_detector.py`

- [x] **Step 1: Write the failing test**

Append to `tests/test_suspension_detector.py`:

```python
def test_detect_gaps_brpt_shaped_suspension():
    """
    BRPT-shaped: last bar 2026-05-13, resume 2026-05-25, ~-28% gap-down.
    Trading days strictly between 5/13 and 5/25, given IDX 2026 holidays:
      5/14 Kenaikan Isa Al Masih (holiday)   — excluded
      5/15 Fri                               — TRADING (1)
      5/16, 5/17 weekend                     — excluded
      5/18, 5/19, 5/20, 5/21 Mon-Thu         — TRADING (2,3,4,5)
      5/22 Waisak holiday                    — excluded
      5/23, 5/24 weekend                     — excluded
    Total missing trading days: 5.
    """
    df = _df([
        ("2026-05-13", 2100.0, 2110.0, 2080.0, 2080.0, 50_000_000),
        ("2026-05-25", 1495.0, 1565.0, 1495.0, 1565.0, 200_000_000),
    ])
    events = detect_gaps(df, detected_at="2026-05-28T00:00:00+00:00")
    assert len(events) == 1
    ev = events[0]
    assert ev.last_normal_date == "2026-05-13"
    assert ev.resume_date == "2026-05-25"
    assert ev.missing_td == 5
    assert ev.classification == "suspension"
    assert ev.gap_pct == pytest.approx((1495.0 - 2080.0) / 2080.0, rel=1e-6)
    assert ev.detected_at == "2026-05-28T00:00:00+00:00"
    # ticker is set by scan_all, not by detect_gaps
    assert ev.ticker == ""
```

- [x] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_suspension_detector.py::test_detect_gaps_brpt_shaped_suspension -v`
Expected: FAIL — `assert len(events) == 1` fails because `detect_gaps` still returns `[]`.

- [x] **Step 3: Implement the detection loop**

Replace `engine/suspension_detector.py` with the full implementation (adds imports for `date`/`datetime`/`timedelta`, the trading-day-counter helper, and the iteration). Open the file and replace its contents with:

```python
"""
suspension_detector.py — Detects trading suspensions and data-fetch gaps in
OHLCV history. See docs/superpowers/specs/2026-05-28-suspension-detector-design.md.

Three layers:
  detect_gaps(df, ...)  — pure, no I/O, returns list[GapEvent]
  scan_all(...)         — runs detect_gaps across all tickers, persists to SQLite
  get_status(ticker)    — read API for downstream consumers
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional

import pandas as pd

from engine.calendar_filter import is_trading_day


@dataclass
class GapEvent:
    ticker: str
    last_normal_date: str   # ISO date (YYYY-MM-DD)
    resume_date: str        # ISO date (YYYY-MM-DD)
    missing_td: int         # trading-day count, calendar-aware
    gap_pct: float          # (resume_open - last_close) / last_close
    classification: str     # 'suspension' | 'data_gap'
    detected_at: str        # ISO timestamp


def _count_missing_trading_days(start_exclusive: date, end_exclusive: date) -> int:
    """Trading days strictly between two dates (both endpoints excluded)."""
    if end_exclusive <= start_exclusive:
        return 0
    count = 0
    d = start_exclusive + timedelta(days=1)
    while d < end_exclusive:
        ok, _ = is_trading_day(d)
        if ok:
            count += 1
        d += timedelta(days=1)
    return count


def detect_gaps(
    df: Optional[pd.DataFrame],
    *,
    threshold_days: int = 3,
    price_jump_pct: float = 10.0,
    detected_at: Optional[str] = None,
) -> List[GapEvent]:
    """Detect trading-day gaps in df. Pure — no DB, no I/O."""
    if df is None or len(df) < 2:
        return []
    if detected_at is None:
        detected_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    dates = pd.to_datetime(df["date"]).dt.date.tolist()
    closes = df["close"].tolist()
    opens = df["open"].tolist()

    events: List[GapEvent] = []
    for i in range(len(df) - 1):
        d0, d1 = dates[i], dates[i + 1]
        missing = _count_missing_trading_days(d0, d1)
        if missing <= threshold_days:
            continue
        last_close = closes[i]
        resume_open = opens[i + 1]
        if last_close <= 0:
            continue
        gap_pct = (resume_open - last_close) / last_close
        classification = (
            "suspension" if abs(gap_pct) * 100.0 >= price_jump_pct else "data_gap"
        )
        events.append(GapEvent(
            ticker="",
            last_normal_date=d0.isoformat(),
            resume_date=d1.isoformat(),
            missing_td=missing,
            gap_pct=float(gap_pct),
            classification=classification,
            detected_at=detected_at,
        ))
    return events
```

- [x] **Step 4: Run the full test file**

Run: `pytest tests/test_suspension_detector.py -v`
Expected: PASS (5 tests).

- [x] **Step 5: Commit**

```bash
git add engine/suspension_detector.py tests/test_suspension_detector.py
git commit -m "feat(g2): detect_gaps core loop with calendar-aware trading-day counter"
```

---

## Task 3: `data_gap` classification (continuous price)

Tests the `else` branch of the classifier: 4-trading-day fetcher miss with continuous price → `classification='data_gap'`.

**Files:**
- Modify: `tests/test_suspension_detector.py`

- [x] **Step 1: Write the failing test**

Append to `tests/test_suspension_detector.py`:

```python
def test_detect_gaps_data_gap_when_price_continuous():
    """
    4 missing trading days but price moves only 0.5% → classify as data_gap.
    2026-04-06 (Mon) -> 2026-04-13 (Mon).
    Strictly between: 4/7 Tue, 4/8 Wed, 4/9 Thu, 4/10 Fri = 4 trading days.
    (4/3 Good Friday is *before* the start so doesn't affect this gap.)
    """
    df = _df([
        ("2026-04-06", 100.0, 101.0, 99.0, 100.0, 1000),
        ("2026-04-13", 100.5, 101.5, 100.0, 100.5, 1100),
    ])
    events = detect_gaps(df, detected_at="2026-05-28T00:00:00+00:00")
    assert len(events) == 1
    ev = events[0]
    assert ev.missing_td == 4
    assert ev.classification == "data_gap"
    assert ev.gap_pct == pytest.approx(0.005, rel=1e-6)
```

- [x] **Step 2: Run test to verify it passes (already covered by Task 2's impl)**

Run: `pytest tests/test_suspension_detector.py::test_detect_gaps_data_gap_when_price_continuous -v`
Expected: PASS — Task 2's implementation already handles the `else` branch. This test pins the behavior so a future refactor can't silently drop the classifier.

If it fails, the classifier branch is broken — re-check the `abs(gap_pct) * 100.0 >= price_jump_pct` comparison in `detect_gaps`.

- [x] **Step 3: Commit (tests-only)**

```bash
git add tests/test_suspension_detector.py
git commit -m "test(g2): pin data_gap classification when price stays continuous"
```

---

## Task 4: Calendar-aware non-gap regression (long holiday cluster)

Verifies that an Idul Fitri holiday cluster — many calendar days between two bars but **zero missing trading days** — does NOT produce an event. This is the test that proves we are using `is_trading_day`, not naive calendar counting.

**Files:**
- Modify: `tests/test_suspension_detector.py`

- [x] **Step 1: Write the failing test**

Append to `tests/test_suspension_detector.py`:

```python
def test_detect_gaps_long_holiday_cluster_returns_empty():
    """
    Idul Fitri cluster: bar on 2026-03-18 (Wed), next bar on 2026-03-25 (Wed).
    Strictly between, IDX 2026 calendar:
      3/19 Cuti Bersama Idul Fitri        — excluded
      3/20 Idul Fitri day 1               — excluded
      3/21, 3/22 weekend                  — excluded
      3/23 Cuti Bersama Idul Fitri        — excluded
      3/24 Cuti Bersama Idul Fitri        — excluded
    Total missing trading days: 0 → no event, despite a 7-calendar-day gap.
    """
    df = _df([
        ("2026-03-18", 100.0, 101.0, 99.0, 100.0, 1000),
        ("2026-03-25", 102.0, 103.0, 101.0, 102.0, 1100),
    ])
    assert detect_gaps(df) == []


def test_detect_gaps_normal_weekend_returns_empty():
    """Fri -> Mon, no missing trading days."""
    df = _df([
        ("2026-04-10", 100.0, 101.0, 99.0, 100.0, 1000),
        ("2026-04-13", 100.5, 101.5, 100.0, 100.5, 1100),
    ])
    assert detect_gaps(df) == []
```

- [x] **Step 2: Run tests**

Run: `pytest tests/test_suspension_detector.py -v`
Expected: PASS (8 tests). Calendar-aware counting is already in place from Task 2.

- [x] **Step 3: Commit (tests-only)**

```bash
git add tests/test_suspension_detector.py
git commit -m "test(g2): regression tests for calendar-aware non-gap cases"
```

---

## Task 5: `_ensure_schema` + `scan_all` (persistence + idempotency)

Adds the SQLite layer. Schema is applied inline via `_ensure_schema()`. `scan_all` iterates `ohlcv_map`, calls `detect_gaps` per ticker, stamps the ticker onto each event, and upserts via `INSERT OR REPLACE`. Accepts an explicit `conn` so tests can drive an in-memory database.

**Files:**
- Modify: `engine/suspension_detector.py`
- Modify: `tests/test_suspension_detector.py`

- [x] **Step 1: Write the failing tests**

Append to `tests/test_suspension_detector.py`:

```python
import sqlite3

from engine.suspension_detector import scan_all


def test_scan_all_writes_suspension_event_and_skips_quiet_ticker():
    conn = sqlite3.connect(":memory:")
    try:
        ohlcv_map = {
            "BRPT": _df([
                ("2026-05-13", 2100.0, 2110.0, 2080.0, 2080.0, 50_000_000),
                ("2026-05-25", 1495.0, 1565.0, 1495.0, 1565.0, 200_000_000),
            ]),
            "QUIET": _df([
                ("2026-04-13", 100.0, 101.0, 99.0, 100.0, 1000),
                ("2026-04-14", 100.0, 102.0, 99.0, 101.0, 1100),
            ]),
        }
        n = scan_all(ohlcv_map, conn=conn)
        assert n == 1
        rows = conn.execute(
            "SELECT ticker, last_normal_date, resume_date, missing_td, classification "
            "FROM suspension_events"
        ).fetchall()
        assert rows == [("BRPT", "2026-05-13", "2026-05-25", 5, "suspension")]
    finally:
        conn.close()


def test_scan_all_is_idempotent():
    """Re-running scan_all on the same data must not duplicate rows."""
    conn = sqlite3.connect(":memory:")
    try:
        ohlcv_map = {
            "BRPT": _df([
                ("2026-05-13", 2100.0, 2110.0, 2080.0, 2080.0, 50_000_000),
                ("2026-05-25", 1495.0, 1565.0, 1495.0, 1565.0, 200_000_000),
            ]),
        }
        scan_all(ohlcv_map, conn=conn)
        scan_all(ohlcv_map, conn=conn)
        count = conn.execute("SELECT COUNT(*) FROM suspension_events").fetchone()[0]
        assert count == 1
    finally:
        conn.close()
```

- [x] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_suspension_detector.py -v`
Expected: FAIL — `ImportError: cannot import name 'scan_all'`.

- [x] **Step 3: Implement `_ensure_schema` and `scan_all`**

Open `engine/suspension_detector.py` and append at the bottom of the file (do NOT rewrite the existing contents):

```python
import os
import sqlite3
from typing import Dict


_DEFAULT_DB_PATH = os.getenv(
    "DB_PATH",
    "/home/tjiesar/10 Projects/idx-walkforward-5001/data/walkforward.db",
)


def _ensure_schema(conn: sqlite3.Connection) -> None:
    """Idempotent DDL. Called at the top of every public I/O function."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS suspension_events (
            ticker            TEXT NOT NULL,
            last_normal_date  TEXT NOT NULL,
            resume_date       TEXT NOT NULL,
            missing_td        INTEGER NOT NULL,
            gap_pct           REAL NOT NULL,
            classification    TEXT NOT NULL,
            detected_at       TEXT NOT NULL,
            PRIMARY KEY (ticker, last_normal_date, resume_date)
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_suspension_ticker_resume
            ON suspension_events(ticker, resume_date DESC)
    """)


def _load_ohlcv_bulk(conn: sqlite3.Connection) -> Dict[str, pd.DataFrame]:
    """Bulk-load the ohlcv table into {ticker: df}. Mirrors scheduler._load_ohlcv_bulk."""
    df = pd.read_sql("SELECT * FROM ohlcv ORDER BY ticker, date ASC", conn)
    for c in ["open", "high", "low", "close", "volume"]:
        df[c] = df[c].astype(float)
    return {t: g.reset_index(drop=True) for t, g in df.groupby("ticker")}


def scan_all(
    ohlcv_map: Optional[Dict[str, pd.DataFrame]] = None,
    *,
    threshold_days: int = 3,
    price_jump_pct: float = 10.0,
    conn: Optional[sqlite3.Connection] = None,
    db_path: Optional[str] = None,
) -> int:
    """Scan every ticker's OHLCV for gap events and persist them. Returns rows written."""
    own_conn = conn is None
    if own_conn:
        conn = sqlite3.connect(db_path or _DEFAULT_DB_PATH)
    try:
        _ensure_schema(conn)
        if ohlcv_map is None:
            ohlcv_map = _load_ohlcv_bulk(conn)
        total = 0
        for ticker, df in ohlcv_map.items():
            events = detect_gaps(
                df,
                threshold_days=threshold_days,
                price_jump_pct=price_jump_pct,
            )
            for ev in events:
                ev.ticker = ticker
                conn.execute(
                    "INSERT OR REPLACE INTO suspension_events "
                    "(ticker, last_normal_date, resume_date, missing_td, gap_pct, classification, detected_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        ev.ticker, ev.last_normal_date, ev.resume_date,
                        ev.missing_td, ev.gap_pct, ev.classification, ev.detected_at,
                    ),
                )
                total += 1
        conn.commit()
        return total
    finally:
        if own_conn:
            conn.close()
```

- [x] **Step 4: Run tests**

Run: `pytest tests/test_suspension_detector.py -v`
Expected: PASS (10 tests).

- [x] **Step 5: Commit**

```bash
git add engine/suspension_detector.py tests/test_suspension_detector.py
git commit -m "feat(g2): scan_all persists gap events with idempotent upsert"
```

---

## Task 6: `get_status` read API

Implements the consumer-facing read API. Three behaviors verified: ticker with no event, ticker just past a recent suspension (`post_suspension=True`), and ticker far past the suspension (`post_suspension=False`).

**Files:**
- Modify: `engine/suspension_detector.py`
- Modify: `tests/test_suspension_detector.py`

- [x] **Step 1: Write the failing tests**

Append to `tests/test_suspension_detector.py`:

```python
from datetime import date

from engine.suspension_detector import get_status


def test_get_status_no_event_returns_clean_flags():
    conn = sqlite3.connect(":memory:")
    try:
        status = get_status("NEVER", as_of=date(2026, 5, 28), conn=conn)
        assert status == {
            "ticker": "NEVER",
            "suspended_now": False,
            "post_suspension": False,
            "days_since_resume": None,
            "last_event": None,
        }
    finally:
        conn.close()


def test_get_status_within_post_window_flags_post_suspension():
    """
    BRPT resume 2026-05-25; check on 2026-05-28.
    Trading days from 5/25 (incl) up to 5/28 (incl), IDX 2026:
      5/25 Mon trading, 5/26 Tue trading, 5/27 Idul Adha holiday,
      5/28 Cuti Bersama Idul Adha holiday.
    Trading days inclusive count = 2 → days_since_resume = 2 - 1 = 1.
    """
    conn = sqlite3.connect(":memory:")
    try:
        scan_all({
            "BRPT": _df([
                ("2026-05-13", 2100.0, 2110.0, 2080.0, 2080.0, 50_000_000),
                ("2026-05-25", 1495.0, 1565.0, 1495.0, 1565.0, 200_000_000),
            ]),
        }, conn=conn)
        status = get_status("BRPT", as_of=date(2026, 5, 28), conn=conn, post_window=14)
        assert status["suspended_now"] is False
        assert status["post_suspension"] is True
        assert status["days_since_resume"] == 1
        assert status["last_event"]["classification"] == "suspension"
        assert status["last_event"]["resume_date"] == "2026-05-25"
    finally:
        conn.close()


def test_get_status_beyond_post_window_clears_flag():
    conn = sqlite3.connect(":memory:")
    try:
        scan_all({
            "BRPT": _df([
                ("2026-05-13", 2100.0, 2110.0, 2080.0, 2080.0, 50_000_000),
                ("2026-05-25", 1495.0, 1565.0, 1495.0, 1565.0, 200_000_000),
            ]),
        }, conn=conn)
        # ~7 weeks later, well past the 14-trading-day default window
        status = get_status("BRPT", as_of=date(2026, 7, 15), conn=conn, post_window=14)
        assert status["post_suspension"] is False
        assert status["suspended_now"] is False
        assert status["days_since_resume"] is not None
        assert status["days_since_resume"] > 14
        assert status["last_event"]["classification"] == "suspension"
    finally:
        conn.close()


def test_get_status_data_gap_does_not_trip_post_suspension():
    """A recent data_gap event must NOT set post_suspension=True (only real suspensions do)."""
    conn = sqlite3.connect(":memory:")
    try:
        scan_all({
            "FETCHGAP": _df([
                ("2026-04-06", 100.0, 101.0, 99.0, 100.0, 1000),
                ("2026-04-13", 100.5, 101.5, 100.0, 100.5, 1100),
            ]),
        }, conn=conn)
        status = get_status("FETCHGAP", as_of=date(2026, 4, 14), conn=conn)
        assert status["last_event"]["classification"] == "data_gap"
        assert status["post_suspension"] is False
    finally:
        conn.close()
```

- [x] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_suspension_detector.py -v`
Expected: FAIL — `ImportError: cannot import name 'get_status'`.

- [x] **Step 3: Implement `get_status` and the inclusive-counting helper**

Append to `engine/suspension_detector.py`:

```python
def _trading_days_inclusive(start: date, end: date) -> int:
    """Trading days from start to end, both inclusive. Returns 0 if start > end."""
    if start > end:
        return 0
    count = 0
    d = start
    while d <= end:
        ok, _ = is_trading_day(d)
        if ok:
            count += 1
        d += timedelta(days=1)
    return count


def get_status(
    ticker: str,
    *,
    as_of: Optional[date] = None,
    post_window: int = 14,
    conn: Optional[sqlite3.Connection] = None,
    db_path: Optional[str] = None,
) -> dict:
    """
    Return suspension/post-suspension flags for `ticker` evaluated at `as_of`.
    Reads the most recent event from suspension_events. See spec §get_status.
    """
    if as_of is None:
        as_of = date.today()
    elif isinstance(as_of, str):
        as_of = date.fromisoformat(as_of)

    own_conn = conn is None
    if own_conn:
        conn = sqlite3.connect(db_path or _DEFAULT_DB_PATH)
    try:
        _ensure_schema(conn)
        row = conn.execute(
            "SELECT last_normal_date, resume_date, missing_td, gap_pct, classification, detected_at "
            "FROM suspension_events WHERE ticker = ? ORDER BY resume_date DESC LIMIT 1",
            (ticker,),
        ).fetchone()

        if not row:
            return {
                "ticker": ticker,
                "suspended_now": False,
                "post_suspension": False,
                "days_since_resume": None,
                "last_event": None,
            }

        last_normal = date.fromisoformat(row[0])
        resume = date.fromisoformat(row[1])
        last_event = {
            "last_normal_date": row[0],
            "resume_date": row[1],
            "missing_td": row[2],
            "gap_pct": row[3],
            "classification": row[4],
            "detected_at": row[5],
        }

        suspended_now = last_normal < as_of < resume

        if as_of < resume:
            days_since_resume = None
        else:
            days_since_resume = _trading_days_inclusive(resume, as_of) - 1

        is_suspension = row[4] == "suspension"
        post_suspension = bool(
            is_suspension
            and days_since_resume is not None
            and days_since_resume <= post_window
        )

        return {
            "ticker": ticker,
            "suspended_now": suspended_now,
            "post_suspension": post_suspension,
            "days_since_resume": days_since_resume,
            "last_event": last_event,
        }
    finally:
        if own_conn:
            conn.close()
```

- [x] **Step 4: Run tests**

Run: `pytest tests/test_suspension_detector.py -v`
Expected: PASS (14 tests).

- [x] **Step 5: Commit**

```bash
git add engine/suspension_detector.py tests/test_suspension_detector.py
git commit -m "feat(g2): get_status read API with post_window flag"
```

---

## Task 7: Wire `scan_all` into the daily fetch job

Adds one fail-soft call at the end of the successful branch of `fetch_latest()` in `scheduler.py`. A detector exception must never break the OHLCV fetch.

**Files:**
- Modify: `scheduler.py` (the `fetch_latest()` function, starts at line 50)

- [x] **Step 1: Show current contents of `fetch_latest()`**

Open `scheduler.py` and verify the function looks like this around lines 50-65 (re-read with `Read` if uncertain):

```python
def fetch_latest():
    """Fetch OHLCV terbaru untuk semua ticker (incremental batch)."""
    from data.fetcher import fetch_all_incremental, load_all_tickers
    now_str = datetime.now(WIB).strftime("%H:%M")
    tickers = load_all_tickers()
    print(f"[{now_str}] Incremental fetch {len(tickers)} tickers...")
    try:
        saved = fetch_all_incremental(category="ALL")
        print(f"[{datetime.now(WIB).strftime('%H:%M')}] Fetch selesai. {saved} bars saved.")
    except Exception as e:
        print(f"[{datetime.now(WIB).strftime('%H:%M')}] Fetch error: {e}")
        send_telegram(
            f"🔴 <b>OHLCV Fetch GAGAL</b>\n\n"
            f"<b>{len(tickers)} tickers</b> @ {now_str}\n"
            f"<code>{str(e)[:150]}</code>"
        )
```

- [x] **Step 2: Apply the edit**

Use `Edit` to replace the success-branch print with the success-print + suspension-scan block:

old_string:
```
        saved = fetch_all_incremental(category="ALL")
        print(f"[{datetime.now(WIB).strftime('%H:%M')}] Fetch selesai. {saved} bars saved.")
    except Exception as e:
```

new_string:
```
        saved = fetch_all_incremental(category="ALL")
        print(f"[{datetime.now(WIB).strftime('%H:%M')}] Fetch selesai. {saved} bars saved.")
        try:
            from engine.suspension_detector import scan_all as _scan_suspensions
            n_events = _scan_suspensions()
            print(f"[{datetime.now(WIB).strftime('%H:%M')}] Suspension scan: {n_events} events written.")
        except Exception as _scan_e:
            logging.exception("suspension scan failed (non-fatal): %s", _scan_e)
    except Exception as e:
```

- [x] **Step 3: Smoke-test the import path**

Run from repo root:
```bash
python -c "from engine.suspension_detector import scan_all; print('import ok')"
```
Expected output: `import ok`.

- [x] **Step 4: Re-run the unit tests to confirm nothing broke**

Run: `pytest tests/test_suspension_detector.py -v`
Expected: PASS (14 tests).

- [x] **Step 5: Commit**

```bash
git add scheduler.py
git commit -m "chore(g2): wire suspension scan into daily fetch_latest job (fail-soft)"
```

---

## Task 8: One-shot backfill against the live database

Runs `scan_all()` once against the real `data/walkforward.db` to populate historical events (BRPT, DEWA, BULL, and whatever else the universe surfaces). Read-mostly — only writes to the new `suspension_events` table.

**Files:**
- No code changes.

- [x] **Step 1: Run the backfill**

From repo root:

```bash
python -c "from engine.suspension_detector import scan_all; print(scan_all(), 'events written')"
```

Expected: a single integer count printed (likely small — handfuls to low hundreds across 972 tickers).

- [x] **Step 2: Spot-check the known suspensions**

```bash
sqlite3 data/walkforward.db "SELECT ticker, last_normal_date, resume_date, missing_td, ROUND(gap_pct,3) AS gap, classification FROM suspension_events WHERE ticker IN ('BRPT','DEWA','BULL') ORDER BY ticker, resume_date;"
```

Expected: at least one `suspension` row each for BRPT, DEWA, and BULL with `gap_pct` clearly negative (around -0.20 to -0.30) and `missing_td >= 4`. The exact `last_normal_date`/`resume_date` depend on what's in the OHLCV table.

If any of those three tickers is missing from the result, the suspension wasn't detected — investigate before declaring G2 done. Most likely cause: the price-jump threshold or the trading-day threshold needs tuning, or the OHLCV data doesn't show the gap (the fetcher may have backfilled across it).

- [x] **Step 3: Audit the classification breakdown**

```bash
sqlite3 data/walkforward.db "SELECT classification, COUNT(*) FROM suspension_events GROUP BY classification;"
```

Expected: a mix of `suspension` and `data_gap`. If `data_gap` dominates by 10x+, that's expected (yfinance is noisy) — it confirms the classifier is doing its job by *not* flagging those as suspensions.

- [x] **Step 4: No commit needed**

This task only writes to the new SQLite table inside `data/walkforward.db`, which is not under version control. No commit.

---

## Done criteria

- [x] `pytest tests/test_suspension_detector.py -v` is green (14 tests).
- [x] `from engine.suspension_detector import scan_all, get_status, GapEvent` succeeds from repo root.
- [x] `scheduler.py` `fetch_latest()` calls `scan_all()` fail-soft on the success branch.
- [x] `suspension_events` table is populated; BRPT, DEWA, BULL each have at least one `suspension` row.
- [x] No edits to `engine/strategies.py` (no indicator math touched), no Telegram code added, no `dive.html` changes. The follow-on tickets (G8 / G9 / R9) remain open.

---

## Self-review

**Spec coverage:**
- Module shape, three layers → Tasks 1, 2, 5, 6.
- `GapEvent` schema → Task 1 (dataclass) + Task 5 (table DDL).
- Detection algorithm (calendar-aware counter, threshold, price classifier) → Tasks 2, 3, 4.
- `_ensure_schema` inline DDL → Task 5.
- BRPT worked example (`missing_td=5`, suspension) → Task 2 test.
- `get_status` shape with `suspended_now` / `post_suspension` / `days_since_resume` / `last_event` → Task 6 (all three behaviors).
- Scheduler call site fail-soft → Task 7.
- Backfill → Task 8.
- Test fixture coverage (no gap / weekend / holiday cluster / suspension / data_gap / round-trip) → Tasks 1-6.
- Non-goals (no indicator edits, no Telegram, no dive.html) → enforced by Done criteria.

**Placeholders:** none — every code block is complete.

**Type / signature consistency:**
- `detect_gaps(df, *, threshold_days, price_jump_pct, detected_at)` — same signature in Tasks 2, 3, 4.
- `GapEvent` field order matches between dataclass (Task 1) and INSERT in `scan_all` (Task 5) and SELECT in `get_status` (Task 6).
- `scan_all` returns `int`; tests assert `n == 1`; backfill prints the int.
- `get_status` returns a dict with the same five keys across all four tests in Task 6.
