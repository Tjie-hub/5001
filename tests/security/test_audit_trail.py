"""Audit trail: table self-creation, never-raise contract, middleware wiring."""
import importlib
import sqlite3

from security.audit_trail import record_audit_event


def test_record_creates_table_and_row(tmp_path):
    db = str(tmp_path / "a.db")
    sqlite3.connect(db).close()
    record_audit_event("manual_scan", actor_role="operator", actor_fingerprint="abc123",
                       resource="/api/scheduler/run", method="POST", outcome="ok",
                       ip="127.0.0.1", detail="job=eod", db_path=db)
    rows = sqlite3.connect(db).execute(
        "SELECT action, actor_role, resource, outcome FROM audit_events").fetchall()
    assert rows == [("manual_scan", "operator", "/api/scheduler/run", "ok")]


def test_record_never_raises(tmp_path):
    # unwritable path: must log a warning, not raise
    record_audit_event("x", db_path=str(tmp_path / "no" / "such" / "dir" / "a.db"))


def test_separate_from_provider_events(tmp_path):
    db = str(tmp_path / "a.db")
    sqlite3.connect(db).close()
    record_audit_event("config_change", db_path=db)
    tables = {r[0] for r in sqlite3.connect(db).execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    assert "audit_events" in tables and "provider_events" not in tables


def test_middleware_audits_protected_mutations(tmp_path, monkeypatch):
    db = tmp_path / "t.db"
    conn = sqlite3.connect(str(db))
    conn.execute("CREATE TABLE scheduled_signals (scan_time TEXT)")
    conn.execute("CREATE TABLE paper_trades (ticker TEXT, status TEXT)")
    conn.commit()
    conn.close()
    monkeypatch.setenv("DB_PATH", str(db))
    monkeypatch.setenv("AUTH_MODE", "enforce")
    monkeypatch.setenv("AUTH_TOKEN_OPERATOR", "operator-token-0123456789abcdef")
    import app as app_module
    importlib.reload(app_module)
    app_module.app.config["TESTING"] = True
    c = app_module.app.test_client()
    c.post("/api/scheduler/run",
           headers={"X-API-Key": "operator-token-0123456789abcdef"})
    rows = sqlite3.connect(str(db)).execute(
        "SELECT action, resource FROM audit_events").fetchall()
    assert ("operational_action", "/api/scheduler/run") in rows


def test_middleware_audits_auth_failures(tmp_path, monkeypatch):
    db = tmp_path / "t.db"
    conn = sqlite3.connect(str(db))
    conn.execute("CREATE TABLE scheduled_signals (scan_time TEXT)")
    conn.execute("CREATE TABLE paper_trades (ticker TEXT, status TEXT)")
    conn.commit()
    conn.close()
    monkeypatch.setenv("DB_PATH", str(db))
    monkeypatch.setenv("AUTH_MODE", "enforce")
    monkeypatch.setenv("AUTH_TOKEN_OPERATOR", "operator-token-0123456789abcdef")
    import app as app_module
    importlib.reload(app_module)
    app_module.app.config["TESTING"] = True
    c = app_module.app.test_client()
    assert c.get("/api/signals/today").status_code == 401
    rows = sqlite3.connect(str(db)).execute(
        "SELECT action, resource, outcome FROM audit_events").fetchall()
    assert ("auth_failure", "/api/signals/today", "blocked") in rows


def test_provider_switch_recorded(tmp_path, monkeypatch):
    db = str(tmp_path / "p.db")
    sqlite3.connect(db).close()
    monkeypatch.setenv("DB_PATH", db)
    from engine.agent_firm.providers import alerts
    alerts.reset_state()
    monkeypatch.setattr(alerts, "send_telegram", lambda msg: None)
    alerts.session_limit_alert("claude", None)
    alerts.provider_restored_alert("claude")
    rows = sqlite3.connect(db).execute(
        "SELECT action, resource, outcome FROM audit_events").fetchall()
    assert ("provider_switch", "claude", "held") in rows
    assert ("provider_switch", "claude", "restored") in rows
