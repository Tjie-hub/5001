import sqlite3
import pytest

from engine.unified_watchlist import build_unified_watchlist


def _make_db(path, *, reversal=(), premover=(), bear=(), with_tables=("rev", "prem", "bear")):
    conn = sqlite3.connect(path)
    if "rev" in with_tables:
        conn.execute("""CREATE TABLE reversal_watchlist (
            scan_date TEXT, ticker TEXT, direction TEXT, conviction REAL,
            close INTEGER, smart_money TEXT, verdict TEXT, net_value INTEGER,
            reasons TEXT, created_at TEXT, PRIMARY KEY(scan_date,ticker))""")
        conn.executemany(
            "INSERT INTO reversal_watchlist(scan_date,ticker,direction,conviction,close,smart_money,verdict)"
            " VALUES(?,?,?,?,?,?,?)", reversal)
    if "prem" in with_tables:
        conn.execute("""CREATE TABLE watchlist_premover (
            id INTEGER PRIMARY KEY AUTOINCREMENT, ticker TEXT, detected_at TEXT,
            score REAL, close_price INTEGER, pattern_type TEXT)""")
        conn.executemany(
            "INSERT INTO watchlist_premover(ticker,detected_at,score,close_price,pattern_type)"
            " VALUES(?,?,?,?,?)", premover)
    if "bear" in with_tables:
        conn.execute("""CREATE TABLE regime_watchlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT, ticker TEXT, status TEXT, bt_win_rate REAL)""")
        conn.executemany(
            "INSERT INTO regime_watchlist(ticker,status,bt_win_rate) VALUES(?,?,?)", bear)
    conn.commit()
    conn.close()


def test_single_source_passthrough(tmp_path):
    db = str(tmp_path / "wl.db")
    _make_db(db, reversal=[("2026-06-10", "BRPT", "short", 74.4, 1760, "MORNING_TRAP", "BEARISH")])
    items = build_unified_watchlist(db, "2026-06-10")
    assert len(items) == 1
    r = items[0]
    assert r["ticker"] == "BRPT"
    assert r["direction"] == "short"
    assert r["strength"] == 74.4
    assert r["sources"] == ["REVERSAL"]
    assert r["confluence"] is False
    assert r["conflict"] is False
    assert r["close"] == 1760
    assert r["detail"]["reversal"]["smart_money"] == "MORNING_TRAP"


def test_confluence_boost_same_direction(tmp_path):
    db = str(tmp_path / "wl.db")
    # INTP long in premover (60) and bear dip-scout (promoted -> 65); both LONG
    _make_db(db,
             premover=[("INTP", "2026-06-10", 60.0, 4000, "CONTINUATION")],
             bear=[("INTP", "promoted", 55.0)])
    items = build_unified_watchlist(db, "2026-06-10")
    assert len(items) == 1
    r = items[0]
    assert r["direction"] == "long"
    assert r["confluence"] is True
    # max single strength = 65 (bear promoted) + 15 confluence = 80
    assert r["strength"] == 80.0
    assert set(r["sources"]) == {"PREMOVER", "BEAR_DIP"}


def test_conflict_flagged_not_merged(tmp_path):
    db = str(tmp_path / "wl.db")
    _make_db(db,
             reversal=[("2026-06-10", "ABCD", "short", 74.0, 1000, "STRONG_SELL", "BEARISH")],
             premover=[("ABCD", "2026-06-10", 60.0, 1000, "REVERSAL_BREAKOUT")])
    items = build_unified_watchlist(db, "2026-06-10")
    assert len(items) == 1
    r = items[0]
    assert r["direction"] == "short"          # higher-strength source wins
    assert r["conflict"] is True
    assert r["confluence"] is False
    assert r["strength"] == 74.0              # no merge bonus on conflict


def test_premover_floor_excludes_low_score(tmp_path):
    db = str(tmp_path / "wl.db")
    _make_db(db, premover=[("LOWS", "2026-06-10", 50.0, 100, "CONTINUATION")])
    items = build_unified_watchlist(db, "2026-06-10")
    assert items == []


def test_dedupe_one_row_per_ticker(tmp_path):
    db = str(tmp_path / "wl.db")
    _make_db(db,
             reversal=[("2026-06-10", "XYZ", "long", 70.0, 500, "ACCUMULATION", "BULLISH")],
             premover=[("XYZ", "2026-06-10", 60.0, 500, "CONTINUATION")],
             bear=[("XYZ", "active", 52.0)])
    items = build_unified_watchlist(db, "2026-06-10")
    assert len(items) == 1
    assert set(items[0]["sources"]) == {"REVERSAL", "PREMOVER", "BEAR_DIP"}


def test_missing_source_table_is_resilient(tmp_path):
    db = str(tmp_path / "wl.db")
    # only reversal table exists; premover + regime tables absent
    _make_db(db, reversal=[("2026-06-10", "BRPT", "short", 74.4, 1760, "X", "BEARISH")],
             with_tables=("rev",))
    items = build_unified_watchlist(db, "2026-06-10")
    assert len(items) == 1
    assert items[0]["ticker"] == "BRPT"


def test_latest_date_default_when_none(tmp_path):
    db = str(tmp_path / "wl.db")
    _make_db(db, reversal=[
        ("2026-06-09", "OLD", "long", 90.0, 100, "X", "BULLISH"),
        ("2026-06-10", "NEW", "long", 60.0, 200, "Y", "BULLISH"),
    ])
    items = build_unified_watchlist(db, None)   # None -> latest scan_date
    assert [r["ticker"] for r in items] == ["NEW"]


def test_conflict_blocks_confluence_bonus(tmp_path):
    db = str(tmp_path / "wl.db")
    _make_db(db,
             reversal=[("2026-06-10", "XYZ", "short", 50.0, 100, "STRONG_SELL", "BEARISH")],
             premover=[("XYZ", "2026-06-10", 60.0, 100, "CONTINUATION")],
             bear=[("XYZ", "promoted", 65.0)])
    items = build_unified_watchlist(db, "2026-06-10")
    r = items[0]
    assert r["direction"] == "long"     # dominant (65) wins
    assert r["conflict"] is True
    assert r["confluence"] is True      # 2 long sources agree
    assert r["strength"] == 65.0       # NO bonus because a conflict exists


def test_premover_floor_includes_at_threshold(tmp_path):
    db = str(tmp_path / "wl.db")
    _make_db(db, premover=[("EDGE", "2026-06-10", 55.0, 100, "CONTINUATION")])
    items = build_unified_watchlist(db, "2026-06-10")
    assert len(items) == 1
    assert items[0]["ticker"] == "EDGE"


def test_endpoint_shape(tmp_path, monkeypatch):
    db = str(tmp_path / "wl.db")
    _make_db(db, reversal=[("2026-06-10", "BRPT", "short", 74.4, 1760, "MT", "BEARISH")])
    import config
    monkeypatch.setattr(config, "DB_PATH", db, raising=False)
    import routes.flow as flowmod
    monkeypatch.setattr(flowmod, "DB_PATH", db, raising=False)
    from flask import Flask
    app = Flask(__name__)
    app.register_blueprint(flowmod.flow_bp)
    client = app.test_client()
    resp = client.get("/api/dashboard/unified-watchlist?date=2026-06-10")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["count"] == 1
    assert data["items"][0]["ticker"] == "BRPT"
