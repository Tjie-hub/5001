"""Tests for new fields added to GET /api/ticker/<ticker>/full."""
import json
import sqlite3
import tempfile
import os
import pytest
import pandas as pd
import numpy as np


def _make_ohlcv_rows(n=75):
    """Return list of (date, open, high, low, close, volume) tuples."""
    import datetime
    start = datetime.date(2025, 9, 1)
    rows = []
    for i in range(n):
        d = start + datetime.timedelta(days=i)
        rows.append((d.isoformat(), 100.0, 102.0, 98.0, 101.0, 1_000_000))
    return rows


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db = tmp_path / "test.db"
    conn = sqlite3.connect(str(db))

    # ohlcv — 75 rows so detect_regime() / calc_adx() / score_ticker() all warm up
    conn.execute(
        "CREATE TABLE ohlcv "
        "(date TEXT, ticker TEXT, open REAL, high REAL, low REAL, close REAL, volume REAL)"
    )
    for row in _make_ohlcv_rows(75):
        conn.execute(
            "INSERT INTO ohlcv VALUES (?, 'TEST', ?, ?, ?, ?, ?)", row
        )

    # suspension_events
    conn.execute("""
        CREATE TABLE suspension_events (
            ticker TEXT,
            last_normal_date TEXT,
            resume_date TEXT,
            missing_td INTEGER,
            gap_pct REAL,
            classification TEXT,
            detected_at TEXT,
            PRIMARY KEY (ticker, last_normal_date, resume_date)
        )
    """)
    conn.execute(
        "INSERT INTO suspension_events VALUES "
        "('TEST','2026-01-10','2026-01-15',3,-0.123456,'suspension','2026-01-15T09:00:00')"
    )
    conn.execute(
        "INSERT INTO suspension_events VALUES "
        "('TEST','2026-01-20','2026-01-22',1,-0.05,'data_gap','2026-01-22T09:00:00')"
    )

    # stockbit_keystats
    conn.execute("""
        CREATE TABLE stockbit_keystats (
            ticker TEXT, fetch_date TEXT,
            pe_ttm REAL, pe_ann REAL, pe_forward REAL, pbv REAL,
            ps_ttm REAL, eps_ttm REAL, bvps REAL, earnings_yield REAL,
            pcf_ttm REAL, pfcf_ttm REAL, ev_ebit REAL, ev_ebitda REAL,
            peg_ratio REAL, fcf_per_share REAL, cash_per_share REAL,
            revenue_per_share REAL, current_ratio REAL, quick_ratio REAL,
            roe REAL, roa REAL, market_cap REAL,
            der REAL, npm REAL, div_yield REAL, rev_growth REAL,
            earn_growth REAL, updated_at TEXT,
            PRIMARY KEY (ticker, fetch_date)
        )
    """)

    # tables needed by other parts of api_ticker_full
    conn.execute(
        "CREATE TABLE wf_scores "
        "(ticker TEXT, strategy TEXT, consistency_pct REAL, "
        "avg_return_pct REAL, avg_sharpe REAL, weighted_score REAL)"
    )
    conn.execute(
        "CREATE TABLE stockbit_flow "
        "(ticker TEXT, trade_date TEXT, net_lot REAL, net_value REAL, "
        "composite_score REAL, verdict TEXT, smart_money TEXT, last_price REAL)"
    )
    conn.execute(
        "CREATE TABLE broker_flow "
        "(ticker TEXT, trade_date TEXT, broker_code TEXT, side TEXT, lot REAL, value REAL)"
    )

    conn.commit()
    conn.close()

    monkeypatch.setenv("DB_PATH", str(db))
    monkeypatch.setattr("scheduler.start_scheduler", lambda: None, raising=False)

    from flask import Flask
    from routes.screener import screener_main_bp
    app = Flask(__name__, template_folder="../templates")
    app.register_blueprint(screener_main_bp)
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c, str(db)


def _get_full(client):
    c, _ = client
    resp = c.get("/api/ticker/TEST/full")
    assert resp.status_code == 200
    return json.loads(resp.data)


# ── G9: suspensions ────────────────────────────────────────────────────────


def test_full_includes_suspensions_key(client):
    d = _get_full(client)
    assert "suspensions" in d


def test_suspensions_only_includes_suspension_classification(client):
    d = _get_full(client)
    # data_gap row must be excluded
    assert len(d["suspensions"]) == 1
    assert d["suspensions"][0]["missing_td"] == 3


def test_suspensions_has_correct_fields(client):
    d = _get_full(client)
    s = d["suspensions"][0]
    assert s["last_normal_date"] == "2026-01-10"
    assert s["resume_date"] == "2026-01-15"
    assert s["missing_td"] == 3
    assert s["gap_pct"] == -0.1235   # -0.123456 rounded to 4dp
