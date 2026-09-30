"""Tests for research/fq_snapshot.py — append-only FQ keystats capture.

No network, no real DB: universe selection runs on an in-memory sqlite fixture, fetching is
a stub, and rate-limit sleeps are counted via a fake sleep_fn.
"""
import json
import sqlite3

import pytest

from research import fq_snapshot as fq


# ---------------------------------------------------------------- universe fixture
@pytest.fixture
def uni_conn():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE ohlcv (ticker TEXT, date TEXT, close REAL, volume REAL,"
                 " is_final INTEGER)")
    rows = []
    # AAA: 70 sessions of strong liquidity (ADV60 = 3.0bn) ending mid-August 2026
    for i in range(70):
        rows.append(("AAA", f"2026-{6 + i // 30:02d}-{(i % 28) + 1:02d}", 50.0, 6.0e7, 1))
    # BBB: lower liquidity than AAA (ADV60 = 2.4bn) — a 500-failure in the run() test
    for i in range(70):
        rows.append(("BBB", f"2026-{6 + i // 30:02d}-{(i % 28) + 1:02d}", 60.0, 4.0e7, 1))
    # CCC: liquid but its last August bar is a frozen carry-forward (volume=0) -> C1 excludes
    for i in range(69):
        rows.append(("CCC", f"2026-{6 + i // 30:02d}-{(i % 28) + 1:02d}", 70.0, 5.0e7, 1))
    rows.append(("CCC", "2026-08-29", 70.0, 0.0, 1))
    # DDD: below the ADV floor
    for i in range(70):
        rows.append(("DDD", f"2026-{6 + i // 30:02d}-{(i % 28) + 1:02d}", 50.0, 1.0e6, 1))
    # EEE: not final yet
    for i in range(70):
        rows.append(("EEE", f"2026-{6 + i // 30:02d}-{(i % 28) + 1:02d}", 50.0, 6.0e7, 0))
    # FFF: valid liquid name (drives the auth-abort path in the run() test)
    for i in range(70):
        rows.append(("FFF", f"2026-{6 + i // 30:02d}-{(i % 28) + 1:02d}", 55.0, 4.0e7, 1))
    conn.executemany("INSERT INTO ohlcv VALUES (?,?,?,?,?)", rows)
    conn.commit()
    return conn


def test_universe_ranks_by_adv60_and_enforces_c1(uni_conn):
    got = fq.select_universe(uni_conn, top_n=10)
    # CCC's frozen 2026-08-29 bar is filtered out by volume>0, so its snapshot point is its
    # last REAL print (still a valid C1 entry) and its ADV60 (3.5bn) ranks it first;
    # DDD is under the ADV floor; EEE is not final.
    assert "DDD" not in got and "EEE" not in got
    assert got[0] == "CCC" and got[1] == "AAA" and "BBB" in got


def test_universe_limit(uni_conn):
    assert len(fq.select_universe(uni_conn, top_n=1)) == 1


# ---------------------------------------------------------------- parse
def test_parse_keystats_known_shape():
    payload = {"data": {"valuation": {"pbv": 1.5, "per": 12.0},
                        "profitability": {"roe": 0.18},
                        "eps": 250.0, "market_cap": 1.2e14,
                        "shares_outstanding": 1.0e11,
                        "noise": "text-here"}}
    out = fq.parse_keystats(payload)
    assert out["pbv"] == 1.5 and out["pe_ttm"] == 12.0
    assert out["roe"] == 0.18 and out["eps_ttm"] == 250.0
    assert out["market_cap"] == 1.2e14 and out["shares"] == 1.0e11
    assert json.loads(out["raw_json"]) == payload


def test_parse_keystats_unknown_shape_still_keeps_raw():
    out = fq.parse_keystats({"weird": {"structure": True}})
    assert out["raw_json"] == json.dumps({"weird": {"structure": True}})
    assert out["pbv"] is None and out["market_cap"] is None


# ---------------------------------------------------------------- append-only storage
def test_insert_is_append_only():
    conn = sqlite3.connect(":memory:")
    fq.init_table(conn)
    stats = {"pe_ttm": 10.0, "pbv": 1.0, "roe": 0.1, "eps_ttm": 100.0,
             "market_cap": 1e12, "shares": 1e9, "raw_json": "{}"}
    fq.insert_snapshot(conn, "AAA", stats, snapshot_month="2026-09")
    fq.insert_snapshot(conn, "AAA", stats, snapshot_month="2026-09")  # same month again
    n, = conn.execute("SELECT COUNT(*) FROM fq_keystats_snapshot").fetchone()
    assert n == 2  # both rows kept: capture history is never overwritten


# ---------------------------------------------------------------- run() behaviour
class _Resp:
    def __init__(self, status=200, payload=None):
        self.status_code = status
        self._payload = payload or {"data": {"pbv": 2.0}}

    def json(self):
        return self._payload


def test_run_continues_past_failures_and_aborts_on_auth(uni_conn):
    rconn = sqlite3.connect(":memory:")
    fq.init_table(rconn)
    calls = []

    class FakeSession:
        def get(self, url, headers=None, timeout=None):
            calls.append(url)
            tkr = url.rsplit("/", 1)[-1]
            if tkr in ("AAA", "CCC"):
                return _Resp(200, {"data": {"pbv": 3.0}})
            if tkr == "BBB":
                return _Resp(500)
            return _Resp(401)  # FFF -> auth failure aborts the batch

    sleeps = []
    out = fq.run(limit=5, universe_size=10, token="dummy", sleep_fn=sleeps.append,
                 session=FakeSession(), universe_conn=uni_conn, research_conn=rconn)
    assert out["captured"] == ["CCC", "AAA"]
    assert any(t == "BBB" for t, _ in out["failed"])
    assert out["failed"][-1][1] == "auth"  # batch aborted on the auth failure
    assert len(sleeps) == len(calls) - 1   # interval sleep between, not before first
    n, = rconn.execute("SELECT COUNT(*) FROM fq_keystats_snapshot").fetchone()
    assert n == 2  # only successes are written


def test_run_without_token_file_raises(uni_conn, tmp_path, monkeypatch):
    monkeypatch.setattr(fq, "TOKEN_FILE", str(tmp_path / "absent.token"))
    with pytest.raises(fq.KeystatsAuthError):
        fq.run(limit=1, universe_size=10, universe_conn=uni_conn,
               research_conn=sqlite3.connect(":memory:"))
