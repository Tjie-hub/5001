"""Tests for GET /health endpoint."""
import json
import sqlite3
import tempfile
import os
import pytest


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db = tmp_path / "test.db"
    conn = sqlite3.connect(str(db))
    conn.execute(
        "CREATE TABLE scheduled_signals "
        "(scan_time TEXT, ticker TEXT, strategies TEXT, flow_score REAL, "
        "flow_verdict TEXT, smart_money TEXT, signal_reasons TEXT)"
    )
    conn.execute(
        "CREATE TABLE paper_trades (ticker TEXT, status TEXT)"
    )
    conn.commit()
    conn.close()

    monkeypatch.setenv("DB_PATH", str(db))
    # Prevent scheduler import side-effects from firing
    monkeypatch.setattr("scheduler.start_scheduler", lambda: None, raising=False)

    import importlib
    import app as app_module
    importlib.reload(app_module)
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as c:
        yield c, str(db)


def test_health_returns_200(client):
    c, _ = client
    resp = c.get("/health")
    assert resp.status_code == 200


def test_health_status_ok_when_db_reachable(client):
    c, _ = client
    resp = c.get("/health")
    data = json.loads(resp.data)
    assert data["status"] == "ok"


def test_health_db_field_is_ok_when_reachable(client):
    c, _ = client
    resp = c.get("/health")
    data = json.loads(resp.data)
    assert data["db"] == "ok"


def test_health_last_scan_is_none_when_no_signals(client):
    c, _ = client
    resp = c.get("/health")
    data = json.loads(resp.data)
    assert data["last_scan"] is None


def test_health_last_scan_returns_most_recent(client):
    c, db_path = client
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO scheduled_signals VALUES (?,?,?,?,?,?,?)",
        ("2026-05-29 09:05:00", "BBCA", "[]", 0.0, "NEUTRAL", "{}", "[]"),
    )
    conn.execute(
        "INSERT INTO scheduled_signals VALUES (?,?,?,?,?,?,?)",
        ("2026-05-29 10:05:00", "TLKM", "[]", 0.0, "NEUTRAL", "{}", "[]"),
    )
    conn.commit()
    conn.close()
    resp = c.get("/health")
    data = json.loads(resp.data)
    assert data["last_scan"] == "2026-05-29 10:05:00"


def test_health_open_trades_count(client):
    c, db_path = client
    conn = sqlite3.connect(db_path)
    conn.execute("INSERT INTO paper_trades VALUES ('BBCA', 'OPEN')")
    conn.execute("INSERT INTO paper_trades VALUES ('TLKM', 'OPEN')")
    conn.execute("INSERT INTO paper_trades VALUES ('GOTO', 'CLOSED')")
    conn.commit()
    conn.close()
    resp = c.get("/health")
    data = json.loads(resp.data)
    assert data["open_trades"] == 2


def test_health_open_trades_zero_when_none(client):
    c, _ = client
    resp = c.get("/health")
    data = json.loads(resp.data)
    assert data["open_trades"] == 0
