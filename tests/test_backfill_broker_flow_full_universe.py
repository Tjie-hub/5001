"""Tests for tools/backfill_broker_flow_full_universe.py — the full-universe,
single-date broker_flow driver. No network access: stockbit_fetcher.fetch_broker_flow
is always monkeypatched. Mirrors tests/test_backfill_broker_flow_idx80.py's
conventions/schema.
"""
import sqlite3

import pytest

import stockbit_fetcher as sf
import tools.backfill_broker_flow_full_universe as R


SCHEMA = """
CREATE TABLE idx_tickers (
    ticker TEXT PRIMARY KEY, status TEXT DEFAULT "active",
    in_idx30 INTEGER DEFAULT 0, in_lq45 INTEGER DEFAULT 0,
    in_idx80 INTEGER DEFAULT 0);
CREATE TABLE ohlcv (
    ticker TEXT, date TEXT, open REAL, high REAL, low REAL, close REAL,
    volume INTEGER);
CREATE TABLE trading_calendar (
    date TEXT PRIMARY KEY, source TEXT, updated_at TEXT);
CREATE TABLE broker_flow (
    ticker TEXT, trade_date TEXT, broker_code TEXT, side TEXT,
    lot INTEGER, lot_value INTEGER, value INTEGER, value_total INTEGER,
    avg_price REAL, freq INTEGER, investor_type TEXT,
    PRIMARY KEY (ticker, trade_date, broker_code, side));
CREATE TABLE bandar_detector (
    ticker TEXT, trade_date TEXT, avg_price REAL, total_buyer INTEGER,
    total_seller INTEGER, net_broker_count INTEGER, broker_accdist TEXT,
    value INTEGER, volume INTEGER, top1_accdist TEXT, top3_accdist TEXT,
    top5_accdist TEXT, top10_accdist TEXT, avg_accdist TEXT, updated_at TEXT,
    PRIMARY KEY (ticker, trade_date));
"""

FULL_UNIVERSE = ["AAAA", "BBCA", "BBRI", "CCCC", "DDDD"]


@pytest.fixture
def conn(tmp_path, monkeypatch):
    path = tmp_path / "test.db"
    c = sqlite3.connect(path)
    c.executescript(SCHEMA)
    for t in FULL_UNIVERSE:
        c.execute("INSERT INTO idx_tickers (ticker, status) VALUES (?, 'active')", (t,))
    for d in ("2025-01-02", "2025-01-03"):
        c.execute("INSERT INTO ohlcv (ticker, date) VALUES ('IHSG', ?)", (d,))
        c.execute("INSERT INTO trading_calendar (date, source) VALUES (?, 'IHSG')", (d,))
    c.commit()
    monkeypatch.setattr(R, "DB_PATH", path)
    monkeypatch.setattr(R.time, "sleep", lambda *a, **k: None)
    monkeypatch.setattr(R, "load_all_tickers", lambda: list(FULL_UNIVERSE))
    monkeypatch.setattr(R, "other_backfill_pids", lambda **kw: [])
    # The fixture's small fake universe is well below the real fail-closed
    # floor (sized for a ~900-ticker universe) -- lower it so happy-path
    # tests aren't tripped by the guard; the guard's own tests set an
    # even-smaller fake universe explicitly and don't rely on this override.
    monkeypatch.setattr(R, "FALLBACK_SIZE_FLOOR", 3)
    yield c
    c.close()


def _populated_result(ticker, trade_date, lot=1000):
    return {
        "broker_rows": [{
            "ticker": ticker, "trade_date": trade_date, "broker_code": "ZP",
            "side": "BUY", "lot": lot, "lot_value": 1, "value": 2,
            "value_total": 3, "avg_price": 9000.0, "freq": 4,
            "investor_type": "Asing",
        }],
        "bandar": {
            "ticker": ticker, "trade_date": trade_date, "avg_price": 9000.0,
            "total_buyer": 1, "total_seller": 1, "net_broker_count": 1,
            "broker_accdist": "ACC", "value": 100, "volume": 50,
            "top1_accdist": "ACC", "top3_accdist": "ACC", "top5_accdist": "ACC",
            "top10_accdist": "ACC", "avg_accdist": "ACC",
            "updated_at": "2025-01-02T00:00:00",
        },
        "trade_date": trade_date,
    }


# --- fail-closed universe guard --------------------------------------------


def test_resolve_universe_returns_full_list_above_floor(monkeypatch):
    monkeypatch.setattr(R, "load_all_tickers", lambda: [f"T{i}" for i in range(900)])
    assert len(R.resolve_universe()) == 900


def test_resolve_universe_fails_closed_below_floor(monkeypatch):
    monkeypatch.setattr(R, "load_all_tickers", lambda: [f"T{i}" for i in range(79)])
    with pytest.raises(RuntimeError, match="fail-closed"):
        R.resolve_universe()


def test_run_raises_before_any_vendor_call_when_universe_collapsed(conn, monkeypatch):
    monkeypatch.setattr(R, "load_all_tickers", lambda: ["BBCA"])
    calls = []
    monkeypatch.setattr(sf, "fetch_broker_flow", lambda *a, **k: calls.append(1))
    with pytest.raises(RuntimeError):
        R.run("2025-01-02", conn=conn)
    assert calls == []


# --- trading-day guard -------------------------------------------------


def test_run_blocks_on_non_trading_date(conn, monkeypatch):
    monkeypatch.setattr(sf, "ensure_valid_token", lambda *a, **k: "tok")
    stats = R.run("2025-06-01", conn=conn)  # not in trading_calendar/ohlcv fixture
    assert stats["blocked_reason"] == "not_a_trading_day"
    assert stats["populated"] == 0


# --- dry run -----------------------------------------------------------


def test_dry_run_makes_no_vendor_calls_and_writes_nothing(conn, monkeypatch):
    calls = []
    monkeypatch.setattr(sf, "fetch_broker_flow", lambda *a, **k: calls.append(1))
    monkeypatch.setattr(sf, "ensure_valid_token", lambda *a, **k: "tok")
    stats = R.run("2025-01-02", conn=conn, dry_run=True)
    assert calls == []
    assert conn.execute("SELECT COUNT(*) FROM broker_flow").fetchone()[0] == 0
    assert stats["planned_cells"] == len(FULL_UNIVERSE)
    assert stats["universe_size"] == len(FULL_UNIVERSE)


# --- real run over the full universe ------------------------------------


def test_run_fetches_every_ticker_in_full_universe(conn, monkeypatch):
    calls = []

    def fake(token, ticker, date=None):
        calls.append(ticker)
        return _populated_result(ticker, date)

    monkeypatch.setattr(sf, "fetch_broker_flow", fake)
    monkeypatch.setattr(sf, "ensure_valid_token", lambda *a, **k: "tok")
    stats = R.run("2025-01-02", conn=conn)
    assert set(calls) == set(FULL_UNIVERSE)
    assert stats["populated"] == len(FULL_UNIVERSE)
    assert conn.execute("SELECT COUNT(*) FROM broker_flow").fetchone()[0] == len(FULL_UNIVERSE)


def test_run_skips_already_complete_cells(conn, monkeypatch):
    conn.execute(
        "INSERT INTO broker_flow (ticker, trade_date, broker_code, side) "
        "VALUES ('BBCA', '2025-01-02', 'ZP', 'BUY')"
    )
    conn.commit()
    calls = []

    def fake(token, ticker, date=None):
        calls.append(ticker)
        return _populated_result(ticker, date)

    monkeypatch.setattr(sf, "fetch_broker_flow", fake)
    monkeypatch.setattr(sf, "ensure_valid_token", lambda *a, **k: "tok")
    stats = R.run("2025-01-02", conn=conn)
    assert "BBCA" not in calls
    assert stats["skipped"] == 1
    assert stats["populated"] == len(FULL_UNIVERSE) - 1


def test_auth_failure_makes_no_vendor_calls(conn, monkeypatch):
    calls = []
    monkeypatch.setattr(sf, "fetch_broker_flow", lambda *a, **k: calls.append(1))
    monkeypatch.setattr(sf, "ensure_valid_token", lambda *a, **k: None)
    stats = R.run("2025-01-02", conn=conn)
    assert stats["auth_failed"] is True
    assert calls == []


def test_sustained_failure_aborts_before_full_universe(conn, monkeypatch):
    monkeypatch.setattr(sf, "fetch_broker_flow",
                        lambda *a, **k: (_ for _ in ()).throw(Exception("boom")))
    monkeypatch.setattr(sf, "ensure_valid_token", lambda *a, **k: "tok")
    monkeypatch.setattr(R, "SUSTAINED_FAIL_LIMIT", 2)
    stats = R.run("2025-01-02", conn=conn)
    assert stats["sustained_abort"] is True
    assert conn.execute("SELECT COUNT(*) FROM broker_flow").fetchone()[0] == 0


def test_budget_stop_leaves_remaining_cells_for_resume(conn, monkeypatch):
    calls = []

    def fake(token, ticker, date=None):
        calls.append(ticker)
        return _populated_result(ticker, date)

    monkeypatch.setattr(sf, "fetch_broker_flow", fake)
    monkeypatch.setattr(sf, "ensure_valid_token", lambda *a, **k: "tok")

    real_time = R.time.time()
    call_count = {"n": 0}

    def fake_time():
        call_count["n"] += 1
        # Let the first cell through, then report budget exceeded.
        return real_time if call_count["n"] <= 2 else real_time + 9999

    monkeypatch.setattr(R.time, "time", fake_time)
    stats = R.run("2025-01-02", conn=conn, budget_s=1)
    assert len(calls) < len(FULL_UNIVERSE)


# --- concurrency guard ---------------------------------------------------


def test_check_no_concurrent_writer_reports_conflicts(monkeypatch):
    def fake_pids(marker, exclude=frozenset()):
        return [123] if marker == "tools/backfill_broker_flow_idx80.py" else []

    monkeypatch.setattr(R, "other_backfill_pids", fake_pids)
    conflicts = R.check_no_concurrent_writer()
    assert conflicts == [("tools/backfill_broker_flow_idx80.py", 123)]


def test_check_no_concurrent_writer_clear_when_nothing_running(monkeypatch):
    monkeypatch.setattr(R, "other_backfill_pids", lambda **kw: [])
    assert R.check_no_concurrent_writer() == []


# --- CLI safety gates ------------------------------------------------------


def test_main_blocks_real_run_without_confirmation_flag(monkeypatch, tmp_path):
    monkeypatch.setattr(R, "LOG_PATH", tmp_path / "log.txt")
    rc = R.main(["--date", "2025-01-02"])
    assert rc == R.EXIT_BLOCKED


def test_main_dry_run_with_real_db(conn, monkeypatch, tmp_path):
    db_path = R.DB_PATH  # already monkeypatched to the fixture's tmp_path db by `conn`
    log_path = tmp_path / "log.txt"
    monkeypatch.setattr(R, "LOG_PATH", log_path)
    lock_path = tmp_path / "test.lock"
    rc = R.main(["--date", "2025-01-02", "--dry-run", "--db", str(db_path),
                 "--lock-file", str(lock_path)])
    assert rc == R.EXIT_OK


def test_main_blocked_when_lock_already_held(conn, monkeypatch, tmp_path):
    log_path = tmp_path / "log.txt"
    monkeypatch.setattr(R, "LOG_PATH", log_path)
    lock_path = tmp_path / "held.lock"
    holder = R.AgentLock(lock_path)
    assert holder.acquire()
    try:
        rc = R.main(["--date", "2025-01-02", "--dry-run", "--db", str(R.DB_PATH),
                     "--lock-file", str(lock_path)])
        assert rc == R.EXIT_BLOCKED
    finally:
        holder.release()


def test_main_blocked_when_universe_collapsed(conn, monkeypatch, tmp_path):
    log_path = tmp_path / "log.txt"
    monkeypatch.setattr(R, "LOG_PATH", log_path)
    lock_path = tmp_path / "test2.lock"
    monkeypatch.setattr(R, "load_all_tickers", lambda: ["BBCA"])
    rc = R.main(["--date", "2025-01-02", "--dry-run", "--db", str(R.DB_PATH),
                 "--lock-file", str(lock_path)])
    assert rc == R.EXIT_BLOCKED
