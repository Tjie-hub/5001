"""IHSG Stockbit fallback in repair_provisional_bars (brief 2026-10-23 F1).

^JKSE lacked 2026-10-21 outright (it jumps 10-20 -> 10-22 while every stock had
a final 10-21 bar), so the stranded provisional IHSG bar had no yfinance value
to repair from. The fallback: ONE Stockbit historical-summary GET per stranded
IHSG session, written only after the two feeds agree on the nearest session
both serve. Stocks never take this path (their split basis is yfinance-derived).
"""
import importlib.util
import json
import sys
from pathlib import Path

from data.db import connect

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "repair_provisional_bars", ROOT / "scripts" / "repair_provisional_bars.py")
rpb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rpb)

FIXTURE = ROOT / "tests" / "fixtures" / "stockbit_ihsg_summary_window.json"

# 2026-10-20..22 exactly as Stockbit served them (the owner's manual-fix source;
# captured live 2026-10-23). yfinance's 10-22 close was 5,387.90 — 0.001% away.
SB_1020 = {"open": 4980.163, "high": 5278.888, "low": 4980.163,
           "close": 5278.888, "volume": 534990700.0}
SB_1021 = {"open": 5310.848, "high": 5328.36, "low": 5185.36,
           "close": 5328.36, "volume": 299973450.0}
SB_1022 = {"open": 5247.979, "high": 5422.587, "low": 5185.527,
           "close": 5387.905, "volume": 364468067.0}

_IHSG_1020 = ("IHSG", "2026-10-20", 4980.163, 5278.888, 4980.163, 5278.888, 534990700.0, 1)
_IHSG_1021_PROV = ("IHSG", "2026-10-21", 5297.0, 5300.0, 5290.0, 5297.77, 0.0, 0)
_IHSG_1022_PROV = ("IHSG", "2026-10-22", 5219.0, 5225.0, 5200.0, 5219.4, 0.0, 0)


class _Resp:
    def __init__(self, status_code, body=None):
        self.status_code = status_code
        self._body = body

    def json(self):
        if self._body is None:
            raise ValueError("not json")
        return self._body


def _run(monkeypatch, tmp_path, capsys, rows, *, date="2026-10-21", yf_window=None,
         sb_window="UNSET", requests_get=None, with_source_col=False):
    """main() against a fixture DB with yfinance/Stockbit fully mocked.

    rows: full (ticker, date, open, high, low, close, volume, is_final) tuples.
    db_connect, fetch_window and the Stockbit read are all patched, so nothing
    here can touch the live DB, the token or the network.
    """
    conn = connect(str(tmp_path / "r.db"))
    conn.execute("CREATE TABLE ohlcv (ticker TEXT, date TEXT, open REAL, high REAL, "
                 "low REAL, close REAL, volume REAL, is_final INT)")
    conn.executemany("INSERT INTO ohlcv VALUES (?,?,?,?,?,?,?,?)", rows)
    if with_source_col:
        conn.execute("ALTER TABLE ohlcv ADD COLUMN source TEXT")
    conn.commit()

    monkeypatch.setattr(rpb, "db_connect", lambda *a, **k: conn)
    monkeypatch.setattr(rpb, "wib_today", lambda: "2026-10-23")
    argv = ["repair_provisional_bars.py", "--apply"] + (["--date", date] if date else [])
    monkeypatch.setattr(sys, "argv", argv)
    monkeypatch.setattr(rpb, "fetch_window",
                        lambda tickers, d: yf_window if yf_window is not None else {})
    if sb_window != "UNSET":
        fn = sb_window if callable(sb_window) else (lambda d: sb_window)
        monkeypatch.setattr(rpb, "stockbit_ihsg_window", fn)
    if requests_get is not None:
        monkeypatch.setattr("requests.get", requests_get)
        (tmp_path / "tok").write_text("test-token")
        monkeypatch.setattr(rpb, "TOKEN_FILE", str(tmp_path / "tok"))
    rc = rpb.main()
    return rc, capsys.readouterr().out, conn


def test_ihsg_fallback_repairs_when_feeds_agree(monkeypatch, tmp_path, capsys):
    # the incident: ^JKSE jumps 10-20 -> 10-22, so the stranded 10-21 bar has no
    # yfinance value; Stockbit agrees with yfinance on 10-22 (0.001%) -> written
    rc, out, conn = _run(
        monkeypatch, tmp_path, capsys, [_IHSG_1020, _IHSG_1021_PROV],
        yf_window={"IHSG": {"2026-10-20": {"close": 5278.888},
                            "2026-10-22": {"close": 5387.90}}},
        sb_window={"2026-10-20": SB_1020, "2026-10-21": SB_1021, "2026-10-22": SB_1022})
    assert rc == 0
    row = conn.execute("SELECT open, high, low, close, volume, is_final FROM ohlcv "
                       "WHERE ticker=? AND date=?", ("IHSG", "2026-10-21")).fetchone()
    assert row == (5310.848, 5328.36, 5185.36, 5328.36, 299973450.0, 1)
    assert "source: stockbit" in out
    assert "no source column" in out          # labelling is output-only (no such column)


def test_ihsg_fallback_disagreement_leaves_provisional(monkeypatch, tmp_path, capsys):
    bad_sb = {"2026-10-21": SB_1021, "2026-10-22": {**SB_1022, "close": 5200.0}}  # 3.5% off
    rc, out, conn = _run(
        monkeypatch, tmp_path, capsys, [_IHSG_1020, _IHSG_1021_PROV],
        yf_window={"IHSG": {"2026-10-20": {"close": 5278.888},
                            "2026-10-22": {"close": 5387.90}}},
        sb_window=bad_sb)
    assert rc == 0
    kept = conn.execute("SELECT close, is_final FROM ohlcv WHERE ticker=? AND date=?",
                        ("IHSG", "2026-10-21")).fetchone()
    assert kept == (5297.77, 0)               # untouched, still provisional
    assert rpb.FB_DISAGREE_REASON in out


def test_ihsg_fallback_no_common_session_leaves_provisional(monkeypatch, tmp_path, capsys):
    # yfinance returns nothing at all: IHSG must still reach the fallback (and
    # fail its agreement check loudly), not vanish into the whole-date skip
    rc, out, conn = _run(
        monkeypatch, tmp_path, capsys, [_IHSG_1020, _IHSG_1021_PROV],
        yf_window={}, sb_window={"2026-10-21": SB_1021, "2026-10-22": SB_1022})
    assert rc == 0
    assert "no settled data returned" not in out
    assert rpb.FB_DISAGREE_REASON in out
    assert conn.execute("SELECT is_final FROM ohlcv WHERE ticker=? AND date=?",
                        ("IHSG", "2026-10-21")).fetchone()[0] == 0


def test_stockbit_401_stops_cleanly_without_retry(monkeypatch, tmp_path, capsys):
    calls = []

    def fake_get(url, headers=None, timeout=None):
        calls.append(url)
        return _Resp(401)

    rc, out, conn = _run(
        monkeypatch, tmp_path, capsys, [_IHSG_1020, _IHSG_1021_PROV, _IHSG_1022_PROV],
        date=None, yf_window={"IHSG": {"2026-10-20": {"close": 5278.888}}},
        requests_get=fake_get)
    assert rc == 0                             # clean exit: reported, not crashed
    assert len(calls) == 1                     # one rejection stops all further GETs
    assert "[stop]" in out and "401" in out
    left = conn.execute("SELECT is_final FROM ohlcv WHERE ticker=? AND date IN (?,?)",
                        ("IHSG", "2026-10-21", "2026-10-22")).fetchall()
    assert left == [(0,), (0,)]


def test_stocks_never_take_the_stockbit_path(monkeypatch, tmp_path, capsys):
    def boom(d):
        raise AssertionError("stocks must never hit the Stockbit fallback")

    rows = [("BTEL", "2026-10-20", 100.0, 101.0, 99.0, 100.5, 1000.0, 1),
            ("BTEL", "2026-10-21", 100.0, 101.0, 99.0, 100.5, 500.0, 0)]
    rc, out, conn = _run(monkeypatch, tmp_path, capsys, rows,
                         yf_window={"BTEL": {"2026-10-20": {"close": 100.5}}},
                         sb_window=boom)
    assert rc == 0
    assert "no settled bar for the session" in out
    assert conn.execute("SELECT is_final FROM ohlcv WHERE ticker=? AND date=?",
                        ("BTEL", "2026-10-21")).fetchone()[0] == 0


def test_fallback_sets_source_column_when_one_exists(monkeypatch, tmp_path, capsys):
    rc, out, conn = _run(
        monkeypatch, tmp_path, capsys, [_IHSG_1020, _IHSG_1021_PROV],
        yf_window={"IHSG": {"2026-10-20": {"close": 5278.888},
                            "2026-10-22": {"close": 5387.90}}},
        sb_window={"2026-10-20": SB_1020, "2026-10-21": SB_1021, "2026-10-22": SB_1022},
        with_source_col=True)
    assert rc == 0
    assert conn.execute("SELECT source FROM ohlcv WHERE ticker=? AND date=?",
                        ("IHSG", "2026-10-21")).fetchone()[0] == "stockbit"
    assert conn.execute("SELECT source FROM ohlcv WHERE ticker=? AND date=?",
                        ("IHSG", "2026-10-20")).fetchone()[0] is None
    assert "no source column" not in out


def test_stockbit_window_parses_the_live_response_shape(monkeypatch, tmp_path):
    body = json.loads(FIXTURE.read_text())
    seen = {}

    def fake_get(url, headers=None, timeout=None):
        seen["url"], seen["auth"] = url, headers["Authorization"]
        return _Resp(200, body)

    monkeypatch.setattr("requests.get", fake_get)
    (tmp_path / "tok").write_text("tok123")
    monkeypatch.setattr(rpb, "TOKEN_FILE", str(tmp_path / "tok"))
    bars = rpb.stockbit_ihsg_window("2026-10-21")
    assert bars["2026-10-21"] == {"open": 5310.848, "high": 5328.36, "low": 5185.36,
                                  "close": 5328.36, "volume": 299973450.0}
    assert bars["2026-10-22"]["close"] == 5387.905
    assert "summary/IHSG" in seen["url"]
    assert "start_date=2026-10-09" in seen["url"] and "end_date=2026-11-02" in seen["url"]
    assert seen["auth"] == "Bearer tok123"
