"""Tests for routes/v1/ticker_detail.py -- GET /api/v1/tickers/<symbol>
(Production Decision OS, Ticker workspace D4 slice 1) and
routes/v1/platform.py's GET /api/v1/platform/runtime (status-footer read
model).

The detail payload must be assembled from production tables only, with
optional sections degrading to null instead of erroring; unknown symbols
are a 404 TICKER_NOT_FOUND envelope, malformed ones a 400 INVALID_SYMBOL.
"""
import sqlite3
from datetime import date, timedelta

import pytest

from routes.v1 import api_v1_bp


def _bar(day_offset: int, close: float):
    d = (date(2026, 8, 1) + timedelta(days=day_offset)).isoformat()
    return ("TEST", d, 100.0, 105.0, 99.0, close, 1_000_000, 1)


@pytest.fixture
def env(tmp_path, monkeypatch):
    db = tmp_path / "wf.db"
    conn = sqlite3.connect(str(db))
    conn.executescript("""
        CREATE TABLE ohlcv (ticker TEXT, date TEXT, open REAL, high REAL,
            low REAL, close REAL, volume REAL, is_final INTEGER);
        CREATE TABLE idx_tickers (ticker TEXT PRIMARY KEY, status TEXT,
            in_idx30 INTEGER, in_lq45 INTEGER, in_idx80 INTEGER);
        CREATE TABLE stockbit_flow (ticker TEXT, trade_date TEXT,
            composite_score REAL, verdict TEXT, smart_money TEXT,
            net_value REAL, last_price REAL);
        CREATE TABLE broker_flow (ticker TEXT, trade_date TEXT,
            broker_code TEXT, side TEXT, lot REAL);
        CREATE TABLE scheduled_signals (id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_time TEXT, ticker TEXT, strategies TEXT, flow_score INTEGER,
            flow_verdict TEXT, smart_money TEXT, signal_reasons TEXT,
            signal_direction TEXT);
        CREATE TABLE watchlist_snapshot (date TEXT, strategy TEXT, ticker TEXT,
            rank INTEGER, confidence REAL, conviction REAL, confluence INTEGER,
            sources TEXT, PRIMARY KEY (date, strategy, ticker));
        CREATE TABLE agent_decisions (scan_time TEXT, ticker TEXT,
            strategy TEXT, decision TEXT, confidence REAL, size_hint REAL,
            rationale TEXT);
        CREATE TABLE paper_trades (id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT, strategy TEXT, entry_date TEXT, entry_price REAL,
            lots INTEGER, tp_price REAL, sl_price REAL, exit_date TEXT,
            exit_price REAL, exit_reason TEXT, pnl_pct REAL, status TEXT);
        CREATE TABLE vpin_scores (date TEXT, ticker TEXT, vpin REAL);
    """)
    # 75 rising bars so detect_regime/calc_adx warm up on TEST.
    conn.executemany(
        "INSERT INTO ohlcv VALUES (?,?,?,?,?,?,?,?)",
        [_bar(i, 100.0 + i) for i in range(75)],
    )
    conn.execute("INSERT INTO idx_tickers VALUES ('TEST','active',0,1,1)")
    conn.execute("INSERT INTO idx_tickers VALUES ('NOBARS','active',0,0,0)")
    conn.execute("INSERT INTO stockbit_flow VALUES "
                 "('TEST','2026-09-01',2.5,'ACCUMULATING','ACCUMULATION',"
                 "5.0e8, 174.0)")
    conn.execute("INSERT INTO broker_flow VALUES ('TEST','2026-09-01','BV','BUY',1000)")
    conn.execute("INSERT INTO scheduled_signals (scan_time, ticker, strategies, "
                 "flow_score, flow_verdict, signal_direction, signal_reasons) VALUES "
                 "('2026-08-29 14:35','TEST','distribution',-3,'BEARISH','SELL','test')")
    conn.execute("INSERT INTO watchlist_snapshot VALUES "
                 "('2026-09-01','eod','TEST',3,0.4,0.0,1,'[\"V\"]')")
    conn.execute("INSERT INTO agent_decisions VALUES "
                 "('2026-09-01 16:40','TEST','eod','approve',0.4,1.0,'ok')")
    conn.execute("INSERT INTO paper_trades (ticker, strategy, entry_date, "
                 "entry_price, lots, status) VALUES "
                 "('TEST','conservative','2026-08-28',150.0,10,'OPEN')")
    conn.commit()
    conn.close()

    import config
    monkeypatch.setattr(config, "DB_PATH", str(db))

    from flask import Flask
    app = Flask(__name__)
    app.register_blueprint(api_v1_bp)
    return app.test_client(), str(db)


@pytest.fixture
def client(env):
    c, _ = env
    return c


def _seed_flow_date(db, ticker, trade_date):
    conn = sqlite3.connect(db)
    conn.execute("INSERT INTO broker_flow VALUES (?,?,?,?,?)",
                 (ticker, trade_date, 'BV', 'BUY', 100))
    conn.commit()
    conn.close()


def test_detail_ok_envelope_with_real_sections(client):
    resp = client.get("/api/v1/tickers/TEST")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["ok"] is True
    data = body["data"]
    assert data["symbol"] == "TEST"

    assert data["identity"] == {"status": "active", "in_idx30": False,
                                "in_lq45": True, "in_idx80": True,
                                "sector": data["identity"]["sector"]}
    assert data["price"]["close"] == 174.0
    assert data["price"]["date"] == _bar(74, 0)[1]

    assert data["regime"] is not None
    assert data["regime"]["regime"] in ("BULL", "BEAR", "SIDEWAYS", "UNKNOWN")
    assert data["regime"]["band"] in ("BULL_MODERATE", "BULL_STRONG", "BEAR",
                                      "SIDEWAYS", "UNKNOWN")

    # admission replays the scan chain: every regime-map candidate has a
    # verdict with an observable stage; nothing invented as admitted.
    pa = data["production_admission"]
    assert pa is not None and len(pa["candidates"]) > 0
    assert set(pa["admitted"]) <= set(pa["candidates"])
    for v in pa["verdicts"]:
        assert v["admitted"] is (v["stage"] == "admitted")
        assert v["stage"] in ("disabled", "registry", "rule_parity",
                              "oos_evidence", "evidence_staleness", "admitted")

    assert data["signals"][0]["direction"] == "SELL"
    assert data["flow"]["latest"]["verdict"] == "ACCUMULATING"
    assert data["watchlist_membership"][0]["rank"] == 3
    assert data["agent_decisions"][0]["decision"] == "approve"
    assert data["position"]["entry_price"] == 150.0

    kinds = {e["kind"] for e in data["timeline"]}
    assert {"scan_signal", "watchlist_membership", "agent_decision",
            "paper_open"} <= kinds
    for e in data["timeline"]:
        assert len(e["at"]) > 0

    assert data["data_freshness"]["ohlcv"] == _bar(74, 0)[1]
    assert data["data_freshness"]["stockbit_flow"] == "2026-09-01"
    assert "as_of" in data


def test_detail_ticker_without_bars_still_serves_from_registry(client):
    """An idx_tickers row with no ohlcv must not 404 — identity + null
    sections is the honest payload (zero-trade/suspended tickers exist)."""
    resp = client.get("/api/v1/tickers/NOBARS")
    assert resp.status_code == 200
    data = resp.get_json()["data"]
    assert data["identity"]["status"] == "active"
    assert data["price"] is None
    assert data["regime"] is None


def test_unknown_symbol_404_envelope(client):
    resp = client.get("/api/v1/tickers/ZZZZ")
    assert resp.status_code == 404
    body = resp.get_json()
    assert body["ok"] is False
    assert body["error"]["code"] == "TICKER_NOT_FOUND"


def test_malformed_symbol_400(client):
    resp = client.get("/api/v1/tickers/BAD%20SYMBOL")
    assert resp.status_code == 400
    assert resp.get_json()["error"]["code"] == "INVALID_SYMBOL"


def test_lowercase_symbol_normalised(client):
    resp = client.get("/api/v1/tickers/test")
    assert resp.status_code == 200
    assert resp.get_json()["data"]["symbol"] == "TEST"


def test_platform_runtime_footer_model(client, env):
    _, db = env
    _seed_flow_date(db, "TEST", "2026-09-01")
    resp = client.get("/api/v1/runtime")
    assert resp.status_code == 200
    data = resp.get_json()["data"]
    # environment is derived, never a hardcoded env name
    assert data["environment"] in ("dev", "release")
    assert data["release_source"] in ("working-tree", "release")
    assert data["version"]
    assert data["timezone"] == "WIB (UTC+7)"
    # snapshot = the latest watchlist_snapshot row actually written
    assert data["snapshot"] == {"date": "2026-09-01", "strategy": "eod"}
    assert data["freshness"]["ohlcv"] == _bar(74, 0)[1]
    assert "database" in data["components"]
    assert data["overall"] in ("healthy", "degraded", "unavailable")
