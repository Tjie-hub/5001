"""End-to-end off/shadow/enforce behavior through the real Flask app."""
import importlib
import sqlite3
import pytest

ADMIN_TOK = "admin-token-0123456789abcdef"
VIEW_TOK = "viewer-token-0123456789abcdef"
OP_TOK = "operator-token-0123456789abcdef"


@pytest.fixture()
def make_client(tmp_path, monkeypatch):
    db = tmp_path / "t.db"
    conn = sqlite3.connect(str(db))
    conn.execute("CREATE TABLE scheduled_signals (scan_time TEXT, signal_direction TEXT)")
    conn.execute("CREATE TABLE paper_trades (ticker TEXT, status TEXT)")
    conn.commit()
    conn.close()
    monkeypatch.setenv("DB_PATH", str(db))
    monkeypatch.setenv("AUTH_TOKEN_ADMIN", ADMIN_TOK)
    monkeypatch.setenv("AUTH_TOKEN_VIEWER", VIEW_TOK)
    monkeypatch.setenv("AUTH_TOKEN_OPERATOR", OP_TOK)

    def _make(mode):
        monkeypatch.setenv("AUTH_MODE", mode)
        import app as app_module
        importlib.reload(app_module)
        app_module.app.config["TESTING"] = True
        return app_module.app.test_client()
    return _make


def test_mode_off_everything_open(make_client):
    c = make_client("off")
    assert c.get("/api/signals/today").status_code == 200
    assert c.get("/dashboard").status_code == 200


def test_enforce_blocks_anonymous(make_client):
    c = make_client("enforce")
    assert c.get("/api/signals/today").status_code == 401
    assert c.get("/health").status_code == 200            # public stays public


def test_enforce_viewer_can_read_not_operate(make_client):
    c = make_client("enforce")
    h = {"Authorization": f"Bearer {VIEW_TOK}"}
    assert c.get("/api/signals/today", headers=h).status_code == 200
    assert c.post("/api/scheduler/run", headers=h).status_code == 403


def test_enforce_admin_everywhere_viewer_config_split(make_client):
    c = make_client("enforce")
    admin = {"X-API-Key": ADMIN_TOK}
    assert c.get("/api/paper/config", headers=admin).status_code == 200
    viewer = {"X-API-Key": VIEW_TOK}
    assert c.get("/api/paper/config", headers=viewer).status_code == 200
    r = c.post("/api/paper/config", headers=viewer, json={})
    assert r.status_code == 403


def test_enforce_bad_token_401(make_client):
    c = make_client("enforce")
    r = c.get("/api/signals/today", headers={"Authorization": "Bearer nope"})
    assert r.status_code == 401


def test_query_param_token_accepted(make_client):
    c = make_client("enforce")
    assert c.get(f"/api/signals/today?api_key={VIEW_TOK}").status_code == 200


def test_shadow_never_blocks(make_client):
    c = make_client("shadow")
    assert c.get("/api/signals/today").status_code == 200
    assert c.post("/api/scheduler/run").status_code not in (401, 403)


def test_login_sets_session(make_client):
    c = make_client("enforce")
    r = c.post("/auth/login", json={"token": VIEW_TOK})
    assert r.status_code == 200 and r.get_json()["role"] == "viewer"
    assert c.get("/api/signals/today").status_code == 200          # session carries auth
    c.post("/auth/logout")
    assert c.get("/api/signals/today").status_code == 401


def test_login_wrong_token_401(make_client):
    c = make_client("enforce")
    assert c.post("/auth/login", json={"token": "bad"}).status_code == 401


def test_whoami(make_client):
    c = make_client("enforce")
    r = c.get("/auth/whoami", headers={"X-API-Key": OP_TOK})
    body = r.get_json()
    assert body["role"] == "operator" and body["mode"] == "enforce"
