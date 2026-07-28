# Security & Release Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the two remaining High-risk institutional-audit findings (unauthenticated routes, working-tree deployment) with token auth + RBAC, secret hygiene, immutable versioned releases with atomic rollback, startup validation, and an audit trail — with zero behavior change until the operator opts in.

**Architecture:** A new `security/` package provides (a) env-configured token→role resolution, (b) a rule-keyed route policy covering every registered endpoint (fail-closed default = admin), (c) one `before_request` middleware enforcing it under `AUTH_MODE=off|shadow|enforce` (default `off` = backward compatible, matching the project's established mode pattern), and (d) an `audit_events` table (separate from `provider_events`). Release management is two bash scripts (`git archive` → immutable dir + manifest + atomic symlink flip; rollback = flip back). `config.validate_config()` grows auth/DB/provider/release/permission checks and keeps its abort-on-failure semantics.

**Tech Stack:** Flask before_request middleware, hmac.compare_digest, sqlite3 via `data.db.connect`, bash + `git archive` + `ln -sfn`/`mv -T`, pytest.

**Hard constraints:** No trading-logic, strategy, provider-architecture, LangGraph, or DB redesign changes. Backward compatible: with no new env vars set, every request behaves exactly as today. Do NOT restart the production service or install the systemd unit — prepare files + docs; cutover is an operator decision.

---

### Task 1: Token auth + role model (`security/auth.py`)

**Files:**
- Create: `security/__init__.py` (empty)
- Create: `security/auth.py`
- Test: `tests/security/__init__.py` (empty), `tests/security/test_auth.py`

- [ ] **Step 1: Write failing tests**

```python
"""tests/security/test_auth.py — token→role resolution, mode parsing, rank checks."""
import pytest
from security import auth


def test_auth_mode_default_off(monkeypatch):
    monkeypatch.delenv("AUTH_MODE", raising=False)
    assert auth.auth_mode() == "off"


def test_auth_mode_values(monkeypatch):
    for v in ("off", "shadow", "enforce", " ENFORCE "):
        monkeypatch.setenv("AUTH_MODE", v)
        assert auth.auth_mode() == v.strip().lower()


def test_auth_mode_unknown_fails_closed(monkeypatch):
    monkeypatch.setenv("AUTH_MODE", "banana")
    assert auth.auth_mode() == "enforce"


def test_resolve_role_from_env(monkeypatch):
    monkeypatch.setenv("AUTH_TOKEN_ADMIN", "adm-token-0123456789")
    monkeypatch.setenv("AUTH_TOKEN_VIEWER", "view-a-0123456789, view-b-0123456789")
    assert auth.resolve_role("adm-token-0123456789") == "admin"
    assert auth.resolve_role("view-b-0123456789") == "viewer"
    assert auth.resolve_role("wrong") is None
    assert auth.resolve_role(None) is None
    assert auth.resolve_role("") is None


def test_role_ranks_and_access():
    assert auth.has_access("admin", "viewer")
    assert auth.has_access("admin", "admin")
    assert auth.has_access("operator", "operator")
    assert auth.has_access("scheduler", "operator")   # internal scheduler == operator rank
    assert not auth.has_access("viewer", "operator")
    assert not auth.has_access("operator", "admin")
    assert not auth.has_access(None, "viewer")
    assert auth.has_access(None, "public")
    assert not auth.has_access("viewer", "not-a-real-level")  # unknown requirement fails closed


def test_token_fingerprint_stable_and_short():
    fp = auth.token_fingerprint("adm-token-0123456789")
    assert fp == auth.token_fingerprint("adm-token-0123456789")
    assert len(fp) == 12
    assert "adm" not in fp
    assert auth.token_fingerprint(None) == "-"
```

- [ ] **Step 2: Run to verify failure** — `pytest tests/security/test_auth.py -q` → import error (module missing).
- [ ] **Step 3: Implement `security/auth.py`**

```python
"""Token authentication + role model (security hardening Phases 1-2).

AUTH_MODE (env):
  off     — no checks; legacy behavior (default, backward compatible)
  shadow  — credentials evaluated and audit-logged; requests never blocked
  enforce — unauthenticated/unauthorized requests rejected (fail closed)
Unknown values fail closed to `enforce`; validate_config rejects them at boot.

Tokens live only in env vars (comma-separated lists, one var per role):
  AUTH_TOKEN_ADMIN, AUTH_TOKEN_OPERATOR, AUTH_TOKEN_VIEWER, AUTH_TOKEN_SCHEDULER
Comparisons are constant-time; logs only ever see a sha256[:12] fingerprint.
"""
import hashlib
import hmac
import os

PUBLIC = "public"
VIEWER = "viewer"
OPERATOR = "operator"
SCHEDULER = "scheduler"
ADMIN = "admin"

ROLE_RANK = {VIEWER: 1, SCHEDULER: 2, OPERATOR: 2, ADMIN: 3}

_ROLE_ENV = {
    ADMIN: "AUTH_TOKEN_ADMIN",
    OPERATOR: "AUTH_TOKEN_OPERATOR",
    VIEWER: "AUTH_TOKEN_VIEWER",
    SCHEDULER: "AUTH_TOKEN_SCHEDULER",
}

VALID_MODES = ("off", "shadow", "enforce")


def auth_mode() -> str:
    mode = os.getenv("AUTH_MODE", "off").strip().lower()
    return mode if mode in VALID_MODES else "enforce"


def configured_tokens() -> dict:
    """token -> role, read fresh from env each call (tests monkeypatch)."""
    out = {}
    for role, var in _ROLE_ENV.items():
        for tok in (t.strip() for t in os.getenv(var, "").split(",")):
            if tok:
                out[tok] = role
    return out


def resolve_role(token):
    if not token:
        return None
    match = None
    for candidate, role in configured_tokens().items():
        if hmac.compare_digest(candidate, token):
            match = role
    return match


def token_fingerprint(token) -> str:
    if not token:
        return "-"
    return hashlib.sha256(token.encode()).hexdigest()[:12]


def has_access(role, required) -> bool:
    if required == PUBLIC:
        return True
    if role is None:
        return False
    return ROLE_RANK.get(role, 0) >= ROLE_RANK.get(required, 99)
```

- [ ] **Step 4: Run tests → PASS.**
- [ ] **Step 5: Commit** — `git commit -m "feat(security): token auth + role model (audit §7-1)"`

---

### Task 2: Route policy — every endpoint classified (`security/route_policy.py`)

**Files:**
- Create: `security/route_policy.py`
- Test: `tests/security/test_route_policy.py`

Policy is keyed by the **URL rule string** exactly as registered in `app.url_map` (method-split where the same rule has different GET/POST handlers). Anything not in the map is treated as `admin` at request time (fail closed), and the guard test makes an unclassified route a CI failure.

- [ ] **Step 1: Write failing guard test**

```python
"""tests/security/test_route_policy.py — every registered route must be classified."""
import importlib


def _app():
    import app as app_module
    importlib.reload(app_module)
    return app_module.app


def test_every_route_classified():
    from security.route_policy import POLICY
    app = _app()
    rules = {r.rule for r in app.url_map.iter_rules()}
    unclassified = rules - set(POLICY)
    assert not unclassified, f"routes missing from security policy: {sorted(unclassified)}"


def test_no_stale_policy_entries():
    from security.route_policy import POLICY
    app = _app()
    rules = {r.rule for r in app.url_map.iter_rules()}
    stale = set(POLICY) - rules
    assert not stale, f"policy entries for routes that no longer exist: {sorted(stale)}"


def test_policy_values_valid():
    from security.route_policy import POLICY, required_level
    from security.auth import PUBLIC, VIEWER, OPERATOR, ADMIN
    valid = {PUBLIC, VIEWER, OPERATOR, ADMIN}
    for rule, spec in POLICY.items():
        levels = spec.values() if isinstance(spec, dict) else [spec]
        for lv in levels:
            assert lv in valid, f"{rule}: bad level {lv!r}"
    assert required_level("/api/paper/config", "GET") == VIEWER
    assert required_level("/api/paper/config", "POST") == ADMIN
    assert required_level("/does/not/exist", "GET") == ADMIN  # fail closed
```

- [ ] **Step 2: Run to verify failure.**
- [ ] **Step 3: Implement the policy** — full classified table (verify against live `url_map` while implementing; the guard tests catch any drift):

```python
"""Route → minimum-role policy (security hardening Phases 1-2).

Keyed by url_map rule string. Value is a level, or {method: level} when
GET/POST semantics differ. Unlisted rules require ADMIN (fail closed).

  public   — no credential (health probe, telegram webhook w/ own HMAC, login)
  viewer   — read-only data/UI
  operator — manual scans, backtests, paper-trade actions (state-changing ops)
  admin    — configuration, provider/agent controls, maintenance
The internal-scheduler role ranks with operator (see security.auth.ROLE_RANK).
"""
from security.auth import PUBLIC, VIEWER, OPERATOR, ADMIN

POLICY = {
    # --- core app ---
    "/health": PUBLIC,
    "/static/<path:filename>": PUBLIC,
    "/": VIEWER, "/backtest/multi": VIEWER, "/screener": VIEWER,
    "/signal-scanner": VIEWER, "/portfolio": VIEWER, "/dashboard": VIEWER,
    "/sector": VIEWER, "/dive/<ticker>": VIEWER, "/metrics": VIEWER,
    # --- auth (Task 3) ---
    "/auth/login": PUBLIC, "/auth/logout": PUBLIC, "/auth/whoami": PUBLIC,
    # --- telegram ---
    "/telegram/updates": PUBLIC,          # protected by its own HMAC secret
    "/telegram/status": VIEWER,
    "/telegram/setup": ADMIN, "/telegram/start-polling": ADMIN,
    "/telegram/stop-polling": ADMIN, "/telegram/poll-updates": ADMIN,
    # --- backtest / signals / paper ---
    "/api/backtest/scan_all": OPERATOR, "/api/backtest/quick_scan": OPERATOR,
    "/api/backtest/precompute": OPERATOR, "/api/backtest/multi_quick_scan": OPERATOR,
    "/api/backtest/roll": OPERATOR, "/api/backtest/multi": OPERATOR,
    "/api/backtest/walkforward": OPERATOR, "/api/backtest/equity": OPERATOR,
    "/api/backtest/trades/<ticker>/<strategy_name>": VIEWER,
    "/api/signals/today": VIEWER, "/api/signals/scheduled": VIEWER,
    "/api/signals/custom": OPERATOR,
    "/api/agent/status": VIEWER, "/api/agent/audit": VIEWER,
    "/api/agent/config": ADMIN,
    "/api/scheduler/run": OPERATOR,
    "/api/paper/config": {"GET": VIEWER, "POST": ADMIN},
    "/api/paper/open": OPERATOR, "/api/paper/close": OPERATOR,
    "/api/paper/clear_history": ADMIN, "/api/paper/summary": VIEWER,
    "/api/paper/report-telegram": OPERATOR,
    "/api/paper/premover_mode": {"GET": VIEWER, "POST": ADMIN},
    "/api/optimizer/run": OPERATOR,
    "/api/optimizer/result/<ticker>/<strategy>": VIEWER,
    "/api/scanner/adaptive_strategy/<ticker>": VIEWER,
    # --- portfolio ---
    "/api/portfolio/sectors": VIEWER, "/api/portfolio/backtest": OPERATOR,
    # --- screener blueprint (/api/screener prefix) ---
    "/api/screener/run": OPERATOR, "/api/screener/status": VIEWER,
    "/api/screener/results": VIEWER, "/api/screener/ticks": VIEWER,
    "/api/screener/cumdelta": VIEWER, "/api/screener/vpin": VIEWER,
    "/api/screener/vpin/multi": VIEWER, "/api/screener/vpin/scan": VIEWER,
    "/api/screener/lq45": VIEWER, "/api/screener/run_log": VIEWER,
    "/api/screener/columns": VIEWER, "/api/screener/presets": VIEWER,
    "/api/screener/fundamental": VIEWER,
    "/api/screener/stockbit/templates": VIEWER,
    "/api/screener/stockbit/run": OPERATOR,
    "/api/screener/brpt_filter": VIEWER,
    # --- screener_main blueprint ---
    "/api/screener/swing_onset": OPERATOR,
    "/api/sector/rotation": VIEWER, "/api/calendar/status": VIEWER,
    "/api/calendar/events": VIEWER, "/api/fastmover/summary": VIEWER,
    "/api/fastmover/run": OPERATOR,
    "/api/ticker/<ticker>/full": VIEWER, "/api/ticker/<ticker>/broker": VIEWER,
    "/api/strategy/list": VIEWER,
    "/api/strategy/markers/<path:strategy>/<ticker>": VIEWER,
    "/api/ticker/<ticker>/ohlcv": VIEWER,
    "/api/premover/watchlist": VIEWER, "/api/premover/run": OPERATOR,
    "/api/screener/reversal": VIEWER,
    # --- flow / market / dashboard ---
    "/api/flow/monitor": VIEWER, "/api/flow/check": OPERATOR,
    "/api/broker-flow/<ticker>": VIEWER, "/api/broker-flow/dates/<ticker>": VIEWER,
    "/api/market/accdist": VIEWER, "/api/market/vpin": VIEWER,
    "/api/market/technicals": VIEWER, "/api/market/breadth": VIEWER,
    "/api/market/risk": VIEWER,
    "/api/dashboard/risk": VIEWER, "/api/dashboard/signals": VIEWER,
    "/api/dashboard/strategy_pnl": VIEWER, "/api/dashboard/watchlist": VIEWER,
    "/api/dashboard/unified-watchlist": VIEWER, "/api/dashboard/checklist": VIEWER,
    "/api/liquidity/impact": VIEWER, "/api/liquidity/ticker/<ticker>": VIEWER,
    "/api/ticker/<ticker>/ohlcv/<freq>": VIEWER,
    # --- chart ---
    "/api/chart/<ticker>/indicators": VIEWER, "/api/chart/<ticker>/delta": VIEWER,
    "/api/chart/tv/sync": OPERATOR, "/api/chart/tv/status": VIEWER,
}


def required_level(rule, method) -> str:
    spec = POLICY.get(rule, ADMIN)   # unknown rule -> fail closed
    if isinstance(spec, dict):
        return spec.get(method, ADMIN)
    return spec
```

- [ ] **Step 4: Run tests; reconcile any rule-string mismatches against the real `url_map` (print `sorted(r.rule for r in app.url_map.iter_rules())` if needed) → PASS.**
- [ ] **Step 5: Commit** — `git commit -m "feat(security): full route classification policy, fail-closed default"`

---

### Task 3: Enforcement middleware + `/auth` endpoints, wired into app.py

**Files:**
- Create: `security/middleware.py`, `security/routes.py`
- Modify: `app.py` (register `auth_bp`, call `init_security(app)` after blueprints)
- Test: `tests/security/test_middleware.py`

- [ ] **Step 1: Write failing tests** (fixture mirrors `tests/test_health_endpoint.py`: tmp DB + `importlib.reload(app)`)

```python
"""tests/security/test_middleware.py — off/shadow/enforce behavior end-to-end."""
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
    conn.commit(); conn.close()
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
    assert c.post("/api/scheduler/run").status_code in (200, 500)  # not 401/403


def test_login_sets_session(make_client):
    c = make_client("enforce")
    r = c.post("/auth/login", json={"token": VIEW_TOK})
    assert r.status_code == 200 and r.get_json()["role"] == "viewer"
    assert c.get("/api/signals/today").status_code == 200          # session cookie carries auth
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
```

- [ ] **Step 2: Run → fails (no middleware, /auth 404).**
- [ ] **Step 3: Implement `security/middleware.py`**

```python
"""Authorization middleware (security hardening Phases 1-2).

One before_request hook enforces security.route_policy for every request.
Fail-closed: unknown rules require admin; unknown AUTH_MODE == enforce.
AUTH_MODE=off short-circuits after credential resolution, so behavior is
byte-identical to the pre-hardening app until the operator opts in.
"""
import logging
from flask import g, jsonify, request, session

from security import auth
from security.route_policy import required_level

log = logging.getLogger("security")


def _extract_token():
    hdr = request.headers.get("Authorization", "")
    if hdr.startswith("Bearer "):
        return hdr[7:].strip()
    if request.headers.get("X-API-Key"):
        return request.headers["X-API-Key"].strip()
    if request.args.get("api_key"):
        return request.args["api_key"].strip()
    return session.get("api_token")


def init_security(app):
    @app.before_request
    def _authorize():
        token = _extract_token()
        role = auth.resolve_role(token)
        g.auth_role = role
        g.auth_fp = auth.token_fingerprint(token)
        mode = auth.auth_mode()
        g.auth_mode = mode

        rule = request.url_rule.rule if request.url_rule else None
        if rule is None:            # no matching route -> Flask 404s, nothing to protect
            return None
        required = required_level(rule, request.method)
        g.auth_required = required
        if auth.has_access(role, required):
            return None
        if mode == "off":
            return None
        # denial path: audit it, block only in enforce
        from security.audit_trail import record_audit_event
        record_audit_event(
            "auth_failure", actor_role=role, actor_fingerprint=g.auth_fp,
            resource=rule, method=request.method,
            outcome="blocked" if mode == "enforce" else "shadow_allowed",
            ip=request.remote_addr,
            detail=f"required={required}",
        )
        if mode == "shadow":
            log.warning("shadow-auth: %s %s would be denied (role=%s required=%s)",
                        request.method, rule, role, required)
            return None
        status = 401 if role is None else 403
        return jsonify({"error": "unauthorized" if status == 401 else "forbidden",
                        "required": required}), status
```

- [ ] **Step 4: Implement `security/routes.py`**

```python
"""Session login endpoints so a browser can use the UI under AUTH_MODE=enforce
without frontend changes (backend-only migration path)."""
from flask import Blueprint, g, jsonify, request, session

from security import auth

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/auth/login", methods=["POST"])
def login():
    token = (request.get_json(silent=True) or {}).get("token", "")
    role = auth.resolve_role(token)
    if role is None:
        from security.audit_trail import record_audit_event
        record_audit_event("auth_failure", resource="/auth/login", method="POST",
                           outcome="blocked", ip=request.remote_addr,
                           detail="invalid login token")
        return jsonify({"error": "invalid token"}), 401
    session["api_token"] = token
    return jsonify({"ok": True, "role": role})


@auth_bp.route("/auth/logout", methods=["POST"])
def logout():
    session.pop("api_token", None)
    return jsonify({"ok": True})


@auth_bp.route("/auth/whoami", methods=["GET"])
def whoami():
    return jsonify({"mode": auth.auth_mode(),
                    "role": g.get("auth_role"),
                    "fingerprint": g.get("auth_fp")})
```

- [ ] **Step 5: Wire into `app.py`** — after the last `register_blueprint`:

```python
from security.routes import auth_bp
from security.middleware import init_security
app.register_blueprint(auth_bp)
init_security(app)
```

- [ ] **Step 6: Run tests + full-suite spot check (`pytest tests/security tests/test_health_endpoint.py tests/test_chart_routes.py -q`) → PASS (proves off-mode backward compat).**
- [ ] **Step 7: Commit** — `git commit -m "feat(security): auth middleware + session login, AUTH_MODE off/shadow/enforce"`

---

### Task 4: Audit trail (`security/audit_trail.py` + wiring)

**Files:**
- Create: `security/audit_trail.py`
- Modify: `security/middleware.py` (record successful protected mutations via after_request), `engine/agent_firm/providers/alerts.py` (one best-effort audit call at the provider-transition alert site — additive only, no provider redesign)
- Test: `tests/security/test_audit_trail.py`

- [ ] **Step 1: Write failing tests**

```python
"""tests/security/test_audit_trail.py"""
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
    record_audit_event("x", db_path=str(tmp_path / "no" / "such" / "dir" / "a.db"))  # must not raise


def test_separate_from_provider_events(tmp_path):
    db = str(tmp_path / "a.db")
    sqlite3.connect(db).close()
    record_audit_event("config_change", db_path=db)
    tables = {r[0] for r in sqlite3.connect(db).execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    assert "audit_events" in tables and "provider_events" not in tables


def test_middleware_audits_protected_mutations(tmp_path, monkeypatch):
    # enforce mode, operator POST to /api/scheduler/run -> one action row
    import importlib, sqlite3 as s
    db = tmp_path / "t.db"
    conn = s.connect(str(db))
    conn.execute("CREATE TABLE scheduled_signals (scan_time TEXT)")
    conn.execute("CREATE TABLE paper_trades (ticker TEXT, status TEXT)")
    conn.commit(); conn.close()
    monkeypatch.setenv("DB_PATH", str(db))
    monkeypatch.setenv("AUTH_MODE", "enforce")
    monkeypatch.setenv("AUTH_TOKEN_OPERATOR", "operator-token-0123456789abcdef")
    import app as app_module
    importlib.reload(app_module)
    app_module.app.config["TESTING"] = True
    c = app_module.app.test_client()
    c.post("/api/scheduler/run", headers={"X-API-Key": "operator-token-0123456789abcdef"})
    rows = s.connect(str(db)).execute(
        "SELECT action, resource FROM audit_events WHERE action='operational_action'").fetchall()
    assert ("operational_action", "/api/scheduler/run") in rows
```

- [ ] **Step 2: Run → fails.**
- [ ] **Step 3: Implement `security/audit_trail.py`**

```python
"""Operational audit trail (security hardening Phase 6).

audit_events is a dedicated table (deliberately separate from provider_events).
Writes are best-effort and never raise: an audit failure must not take down
the request path or the scheduler.
"""
import logging
import os

log = logging.getLogger("audit")

_SCHEMA = """CREATE TABLE IF NOT EXISTS audit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL DEFAULT (datetime('now')),
    action TEXT NOT NULL,
    actor_role TEXT,
    actor_fingerprint TEXT,
    resource TEXT,
    method TEXT,
    outcome TEXT,
    ip TEXT,
    detail TEXT
)"""


def record_audit_event(action, *, actor_role=None, actor_fingerprint=None,
                       resource=None, method=None, outcome=None, ip=None,
                       detail=None, db_path=None):
    try:
        from data.db import connect
        import config
        path = db_path or os.getenv("DB_PATH", config.DB_PATH)
        conn = connect(path)
        try:
            conn.execute(_SCHEMA)
            conn.execute(
                "INSERT INTO audit_events (action, actor_role, actor_fingerprint,"
                " resource, method, outcome, ip, detail) VALUES (?,?,?,?,?,?,?,?)",
                (action, actor_role, actor_fingerprint, resource, method,
                 outcome, ip, detail),
            )
            conn.commit()
        finally:
            conn.close()
    except Exception as e:
        log.warning("audit write failed (%s): %s", action, e)
```

- [ ] **Step 4: Extend middleware** — in `init_security(app)` add an `after_request` hook: if `g.auth_required` in ("operator", "admin") and `request.method` in ("POST", "PUT", "DELETE") and response status < 400 and mode != "off", record `operational_action` (admin-level rules get action `admin_action`; `/api/*/config` rules get `config_change`).
- [ ] **Step 5: Provider-switch hook** — in `engine/agent_firm/providers/alerts.py`, inside the existing transition-alert function, add a guarded `record_audit_event("provider_switch", resource=<provider>, outcome=<new state>, detail=<alert text>)` in try/except. Read the module first; touch nothing else in it.
- [ ] **Step 6: Run tests (`pytest tests/security tests/agent_firm/providers/test_alerts.py -q`) → PASS.**
- [ ] **Step 7: Commit** — `git commit -m "feat(security): audit_events trail — auth failures, ops actions, provider switches"`

---

### Task 5: Secret hygiene (Phase 3)

**Files:**
- Modify: `utils/logging_config.py` (redaction filter), `app.py` (generic 500 handler)
- Test: `tests/security/test_secret_hygiene.py`

- [ ] **Step 1: Write failing tests**

```python
"""tests/security/test_secret_hygiene.py"""
import logging
import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SECRET_ENV_VARS = ["TELEGRAM_TOKEN", "ZAI_API_KEY", "DEEPSEEK_API_KEY",
                   "TAVILY_API_KEY", "FLASK_SECRET_KEY", "STOCKBIT_PASSWORD",
                   "AUTH_TOKEN_ADMIN", "AUTH_TOKEN_OPERATOR",
                   "AUTH_TOKEN_VIEWER", "AUTH_TOKEN_SCHEDULER",
                   "TELEGRAM_WEBHOOK_SECRET"]


def test_env_files_not_tracked_by_git():
    out = subprocess.run(["git", "ls-files", ".env", ".stockbit_token"],
                         cwd=REPO, capture_output=True, text=True).stdout.strip()
    assert out == ""


def test_no_hardcoded_secret_literals():
    # assignments like TELEGRAM_TOKEN = "1234:AA..." with a real-looking literal
    pat = re.compile(
        r'(TOKEN|API_KEY|SECRET|PASSWORD)\s*[=:]\s*["\'][A-Za-z0-9_\-:./+]{16,}["\']')
    offenders = []
    for py in REPO.rglob("*.py"):
        rel = py.relative_to(REPO).as_posix()
        if rel.startswith(("venv/", "tests/", "_archive/", "scratchpad/", "research_reports/")):
            continue
        for i, line in enumerate(py.read_text(errors="ignore").splitlines(), 1):
            m = pat.search(line)
            if m and "getenv" not in line and "example" not in line.lower() \
                    and "your_" not in line and "os.environ" not in line:
                offenders.append(f"{rel}:{i}: {line.strip()[:80]}")
    assert not offenders, "possible hardcoded secrets:\n" + "\n".join(offenders)


def test_logging_redacts_secret_values(monkeypatch):
    monkeypatch.setenv("TELEGRAM_TOKEN", "1234567890:SECRETSECRETSECRET")
    from utils.logging_config import SecretRedactionFilter
    f = SecretRedactionFilter()
    rec = logging.LogRecord("x", logging.INFO, "f", 1,
                            "posting to bot 1234567890:SECRETSECRETSECRET now", (), None)
    assert f.filter(rec)
    assert "SECRETSECRET" not in rec.getMessage()
    assert "[REDACTED]" in rec.getMessage()


def test_500_response_has_no_traceback(tmp_path, monkeypatch):
    import importlib, sqlite3
    db = tmp_path / "t.db"
    conn = sqlite3.connect(str(db))
    conn.execute("CREATE TABLE scheduled_signals (scan_time TEXT)")
    conn.execute("CREATE TABLE paper_trades (ticker TEXT, status TEXT)")
    conn.commit(); conn.close()
    monkeypatch.setenv("DB_PATH", str(db))
    import app as app_module
    importlib.reload(app_module)
    app_module.app.config["TESTING"] = False   # exercise the real error handler

    @app_module.app.route("/_boom_test")
    def _boom():
        raise RuntimeError("kaboom SECRETVALUE")

    c = app_module.app.test_client()
    r = c.get("/_boom_test")
    assert r.status_code == 500
    body = r.get_data(as_text=True)
    assert "Traceback" not in body and "kaboom" not in body
```

- [ ] **Step 2: Run → fails on redaction filter + 500 handler (source-scan and git tests may already pass — fine, they're regression fences).**
- [ ] **Step 3: Implement `SecretRedactionFilter` in `utils/logging_config.py`** — reads `SECRET_ENV_VARS` values from env at filter time; replaces any occurrence (len ≥ 8) in `record.msg`/`record.args`-rendered message with `[REDACTED]`; attach to root logger handlers inside `setup_logging()`.

```python
_SECRET_VARS = ("TELEGRAM_TOKEN", "ZAI_API_KEY", "DEEPSEEK_API_KEY",
                "TAVILY_API_KEY", "FLASK_SECRET_KEY", "STOCKBIT_PASSWORD",
                "AUTH_TOKEN_ADMIN", "AUTH_TOKEN_OPERATOR", "AUTH_TOKEN_VIEWER",
                "AUTH_TOKEN_SCHEDULER", "TELEGRAM_WEBHOOK_SECRET")


class SecretRedactionFilter(logging.Filter):
    """Masks configured secret values if they ever reach a log line."""
    def filter(self, record):
        msg = record.getMessage()
        dirty = False
        for var in _SECRET_VARS:
            for val in (v.strip() for v in os.getenv(var, "").split(",")):
                if len(val) >= 8 and val in msg:
                    msg = msg.replace(val, "[REDACTED]")
                    dirty = True
        if dirty:
            record.msg = msg
            record.args = ()
        return True
```

- [ ] **Step 4: Add 500 handler in `app.py`**

```python
@app.errorhandler(500)
def _internal_error(e):
    logging.getLogger("app").exception("unhandled error (request_id=%s)",
                                       g.get("correlation_id", ""))
    return jsonify({"error": "internal server error",
                    "request_id": g.get("correlation_id", "")}), 500
```

Also register the same handler for uncaught `Exception` so non-HTTP errors return JSON, while `app.config["TESTING"]`/`app.debug` still propagate in existing tests (`if app.config.get("TESTING"): raise` guard NOT needed — Flask propagates before handlers when TESTING; the new test sets TESTING=False deliberately).

- [ ] **Step 5: Run `pytest tests/security -q` and the logging tests → PASS. Verify `.env`/`.stockbit_token` are mode 600 (`ls -la`) — already done in prior hardening; record in report.**
- [ ] **Step 6: Commit** — `git commit -m "feat(security): secret redaction filter, generic 500 handler, secret-scan fence"`

---

### Task 6: Startup validation extensions (Phase 5)

**Files:**
- Modify: `config.py` (`validate_config`)
- Test: extend `tests/test_config_validation.py` (new test functions; existing ones must keep passing)

- [ ] **Step 1: Write failing tests** (same monkeypatch style as the existing file — read it first and match its fixtures)

```python
def test_enforce_without_tokens_aborts(monkeypatch, valid_env):
    monkeypatch.setenv("AUTH_MODE", "enforce")
    for v in ("AUTH_TOKEN_ADMIN", "AUTH_TOKEN_OPERATOR", "AUTH_TOKEN_VIEWER",
              "AUTH_TOKEN_SCHEDULER"):
        monkeypatch.delenv(v, raising=False)
    with pytest.raises(ConfigError, match="AUTH_MODE=enforce"):
        validate_config()


def test_short_token_rejected(monkeypatch, valid_env):
    monkeypatch.setenv("AUTH_MODE", "enforce")
    monkeypatch.setenv("AUTH_TOKEN_ADMIN", "short")
    with pytest.raises(ConfigError, match="16"):
        validate_config()


def test_unknown_auth_mode_rejected(monkeypatch, valid_env):
    monkeypatch.setenv("AUTH_MODE", "banana")
    with pytest.raises(ConfigError, match="AUTH_MODE"):
        validate_config()


def test_db_missing_required_table_aborts(monkeypatch, tmp_path, valid_env):
    empty = tmp_path / "empty.db"
    sqlite3.connect(str(empty)).close()
    monkeypatch.setenv("DB_PATH", str(empty))
    with pytest.raises(ConfigError, match="required table"):
        validate_config()


def test_invalid_release_manifest_aborts(monkeypatch, valid_env, tmp_path): ...
    # write a release.json missing "version" next to a copied config base; assert ConfigError
```

- [ ] **Step 2: Run → fails.**
- [ ] **Step 3: Extend `validate_config()`** — append after existing checks (keep the collect-all-problems style):

```python
    # --- security hardening Phase 5: auth config ---
    mode = os.getenv("AUTH_MODE", "off").strip().lower()
    if mode not in ("off", "shadow", "enforce"):
        problems.append(f"AUTH_MODE invalid: {mode!r} (off|shadow|enforce)")
    token_vars = ("AUTH_TOKEN_ADMIN", "AUTH_TOKEN_OPERATOR",
                  "AUTH_TOKEN_VIEWER", "AUTH_TOKEN_SCHEDULER")
    tokens = [t.strip() for v in token_vars
              for t in os.getenv(v, "").split(",") if t.strip()]
    if mode == "enforce" and not tokens:
        problems.append("AUTH_MODE=enforce but no AUTH_TOKEN_* configured "
                        "(would lock everyone out of protected routes)")
    for t in tokens:
        if len(t) < 16:
            problems.append("an AUTH_TOKEN_* value is shorter than 16 chars")
            break

    # --- DB compatibility: required tables must exist ---
    if Path(db_path).exists():
        try:
            import sqlite3 as _sq
            with _sq.connect(db_path) as _c:
                have = {r[0] for r in _c.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'")}
            for tbl in ("scheduled_signals", "paper_trades"):
                if tbl not in have:
                    problems.append(f"DB missing required table: {tbl}")
        except Exception as e:
            problems.append(f"DB compatibility check failed: {e}")

    # --- provider compatibility ---
    if os.getenv("AGENT_FIRM_ENABLED", "").strip().lower() in ("1", "true", "yes"):
        if "claude" in order and shutil.which("claude") is None:
            problems.append("provider order includes claude but the claude CLI "
                            "is not on PATH")

    # --- secret file permissions (fail closed on world/group access) ---
    for name in (".env", ".stockbit_token"):
        p = _BASE / name
        if p.exists() and (p.stat().st_mode & 0o077):
            problems.append(f"{name} is group/world accessible — chmod 600 it")

    # --- release manifest (when running from a built release) ---
    manifest = _BASE / "release.json"
    if manifest.exists():
        try:
            import json as _json
            meta = _json.loads(manifest.read_text())
            for key in ("version", "git_sha", "built_at"):
                if key not in meta:
                    problems.append(f"release.json missing key: {key}")
        except Exception as e:
            problems.append(f"release.json unreadable: {e}")
```

(`shutil` import at top; `order` already computed in the existing agent-firm block — hoist it so both checks share it.)

- [ ] **Step 4: Run `pytest tests/test_config_validation.py -q` → all old + new PASS.**
- [ ] **Step 5: Commit** — `git commit -m "feat(config): startup validation — auth, DB tables, provider CLI, secret perms, release manifest"`

---

### Task 7: Release version metadata (`utils/release.py` + /health)

**Files:**
- Create: `utils/release.py`
- Modify: `app.py` `/health` (add `"version"`), `init_runtime()` (log version at boot)
- Test: `tests/security/test_release_info.py`

- [ ] **Step 1: Write failing tests**

```python
from utils.release import release_info


def test_working_tree_fallback():
    info = release_info()
    assert info["version"].startswith("dev-") or "version" in info


def test_manifest_wins(tmp_path, monkeypatch):
    (tmp_path / "release.json").write_text(
        '{"version": "20260711-abc1234", "git_sha": "abc", "built_at": "t"}')
    monkeypatch.setattr("utils.release._BASE", tmp_path)
    assert release_info()["version"] == "20260711-abc1234"


def test_health_includes_version(...):  # reuse the health fixture pattern
    ...
    assert "version" in resp.get_json()
```

- [ ] **Step 2: Run → fails.**
- [ ] **Step 3: Implement**

```python
"""utils/release.py — which build is running (security hardening Phase 4)."""
import json
import subprocess
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent


def release_info() -> dict:
    manifest = _BASE / "release.json"
    if manifest.exists():
        try:
            return json.loads(manifest.read_text())
        except Exception:
            return {"version": "invalid-manifest", "source": "release"}
    try:
        sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                             cwd=_BASE, capture_output=True, text=True,
                             timeout=5).stdout.strip()
        return {"version": f"dev-{sha or 'unknown'}", "source": "working-tree"}
    except Exception:
        return {"version": "dev-unknown", "source": "working-tree"}
```

`/health`: `result["version"] = release_info().get("version")`. `init_runtime()`: log it.

- [ ] **Step 4: Run → PASS. Step 5: Commit** — `git commit -m "feat(release): version metadata in /health + boot log"`

---

### Task 8: Release + rollback scripts, systemd unit (Phase 4)

**Files:**
- Create: `scripts/release.sh`, `scripts/rollback.sh` (both `chmod +x`)
- Modify: `deploy/idx-walkforward.service` (point at `%h/idx-walkforward-current`) — **file only, do not install**
- Test: `tests/security/test_release_scripts.py`

- [ ] **Step 1: Write failing tests** (build a throwaway git repo in tmp_path, run the scripts via subprocess with env overrides)

```python
import json
import os
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def _mk_repo(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "hello.py").write_text("print('hi')\n")
    for cmd in (["git", "init", "-q"], ["git", "add", "."],
                ["git", "-c", "user.email=t@t", "-c", "user.name=t",
                 "commit", "-qm", "init"]):
        subprocess.run(cmd, cwd=src, check=True)
    return src


def _env(tmp_path, src):
    env = dict(os.environ)
    env.update(RELEASES_DIR=str(tmp_path / "releases"),
               CURRENT_LINK=str(tmp_path / "current"),
               PROJECT_DIR=str(src), SHARED_PATHS="")
    return env


def test_release_creates_immutable_versioned_dir_with_manifest(tmp_path):
    src = _mk_repo(tmp_path)
    env = _env(tmp_path, src)
    subprocess.run([str(REPO / "scripts" / "release.sh")], env=env, check=True)
    releases = list((tmp_path / "releases").iterdir())
    assert len(releases) == 1
    rel = releases[0]
    meta = json.loads((rel / "release.json").read_text())
    assert {"version", "git_sha", "branch", "built_at"} <= set(meta)
    assert (tmp_path / "current").resolve() == rel.resolve()
    assert not os.access(rel / "hello.py", os.W_OK)      # immutable code


def test_release_switch_is_atomic_and_rollback_restores(tmp_path):
    src = _mk_repo(tmp_path)
    env = _env(tmp_path, src)
    subprocess.run([str(REPO / "scripts" / "release.sh")], env=env, check=True)
    first = (tmp_path / "current").resolve()
    (src / "hello.py").chmod(0o644)
    (src / "hello.py").write_text("print('v2')\n")
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
                    "commit", "-aqm", "v2"], cwd=src, check=True)
    subprocess.run([str(REPO / "scripts" / "release.sh")], env=env, check=True)
    second = (tmp_path / "current").resolve()
    assert second != first
    subprocess.run([str(REPO / "scripts" / "rollback.sh")], env=env, check=True)
    assert (tmp_path / "current").resolve() == first


def test_rollback_to_named_version(tmp_path):
    ...  # release twice, rollback.sh <first-version>, assert link


def test_rollback_list(tmp_path):
    ...  # rollback.sh --list prints both versions, marks current with '*'
```

- [ ] **Step 2: Run → fails (scripts missing).**
- [ ] **Step 3: Implement `scripts/release.sh`**

```bash
#!/bin/bash
# Build an immutable, versioned release from git HEAD and atomically switch
# the `current` symlink (security hardening Phase 4). Prod never runs from a
# mutable working tree again.
#
#   RELEASES_DIR  (default ~/releases/idx-walkforward)   release store
#   CURRENT_LINK  (default ~/idx-walkforward-current)    symlink systemd runs
#   PROJECT_DIR   (default: repo containing this script) source checkout
#   SHARED_PATHS  space-separated mutable paths symlinked into each release
#                 (default: ".env venv data logs walkforward.db flow.db
#                  idx_data.db .stockbit_token")
#
# The service is NOT restarted; print the command instead (operator decision).
set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
RELEASES_DIR="${RELEASES_DIR:-$HOME/releases/idx-walkforward}"
CURRENT_LINK="${CURRENT_LINK:-$HOME/idx-walkforward-current}"
SHARED_PATHS="${SHARED_PATHS-.env venv data logs walkforward.db flow.db idx_data.db .stockbit_token}"

cd "$PROJECT_DIR"
GIT_SHA=$(git rev-parse HEAD)
SHORT_SHA=$(git rev-parse --short HEAD)
BRANCH=$(git rev-parse --abbrev-ref HEAD)
VERSION="$(date +%Y%m%d-%H%M%S)-${SHORT_SHA}"
DEST="$RELEASES_DIR/$VERSION"

if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
    echo "WARNING: uncommitted tracked changes exist; the release is built from HEAD only." >&2
fi

mkdir -p "$DEST"
git archive HEAD | tar -x -C "$DEST"

cat > "$DEST/release.json" <<EOF
{
  "version": "$VERSION",
  "git_sha": "$GIT_SHA",
  "branch": "$BRANCH",
  "built_at": "$(date -Is)",
  "built_by": "$(whoami)@$(hostname)"
}
EOF

# freeze the code (recursion ignores symlinks; shared state stays writable)
chmod -R a-w "$DEST"
chmod u+w "$DEST"    # so the shared-path symlinks below can be created

for p in $SHARED_PATHS; do
    if [ -e "$PROJECT_DIR/$p" ] && [ ! -e "$DEST/$p" ]; then
        ln -s "$PROJECT_DIR/$p" "$DEST/$p"
    fi
done
chmod u-w "$DEST"

# atomic switch: build the link aside, then rename over
ln -sfn "$DEST" "${CURRENT_LINK}.tmp"
mv -Tf "${CURRENT_LINK}.tmp" "$CURRENT_LINK"

echo "released $VERSION"
echo "current -> $DEST"
echo "activate with: systemctl --user restart idx-walkforward"
```

- [ ] **Step 4: Implement `scripts/rollback.sh`**

```bash
#!/bin/bash
# Roll the `current` symlink back to a previous release (security hardening
# Phase 4). Usage:
#   rollback.sh              -> newest release older than the current one
#   rollback.sh <version>    -> that exact release
#   rollback.sh --list       -> list releases, '*' marks current
set -euo pipefail

RELEASES_DIR="${RELEASES_DIR:-$HOME/releases/idx-walkforward}"
CURRENT_LINK="${CURRENT_LINK:-$HOME/idx-walkforward-current}"

current_target=""
[ -L "$CURRENT_LINK" ] && current_target=$(readlink -f "$CURRENT_LINK")
current_version=$(basename "${current_target:-none}")

if [ "${1:-}" = "--list" ]; then
    for d in $(ls -1 "$RELEASES_DIR" | sort); do
        marker=" "
        [ "$d" = "$current_version" ] && marker="*"
        echo "$marker $d"
    done
    exit 0
fi

if [ -n "${1:-}" ]; then
    TARGET="$1"
else
    TARGET=$(ls -1 "$RELEASES_DIR" | sort | awk -v cur="$current_version" \
        '$0 == cur {exit} {prev=$0} END {print prev}')
fi

if [ -z "$TARGET" ] || [ ! -d "$RELEASES_DIR/$TARGET" ]; then
    echo "ERROR: no release to roll back to (target: '${TARGET:-}')" >&2
    exit 1
fi

ln -sfn "$RELEASES_DIR/$TARGET" "${CURRENT_LINK}.tmp"
mv -Tf "${CURRENT_LINK}.tmp" "$CURRENT_LINK"
echo "rolled back: current -> $TARGET (was $current_version)"
echo "activate with: systemctl --user restart idx-walkforward"
```

- [ ] **Step 5: Update `deploy/idx-walkforward.service`** — `WorkingDirectory=/home/tjiesar/idx-walkforward-current`, ExecStart/ExecStartPost paths likewise; add a comment block describing release-based cutover and that installing it is a manual operator step. **Do not copy it into `~/.config/systemd/user/` and do not restart anything.**
- [ ] **Step 6: `chmod +x scripts/release.sh scripts/rollback.sh`; run `pytest tests/security/test_release_scripts.py -q` → PASS.**
- [ ] **Step 7: Smoke-build a real release into `~/releases/idx-walkforward/` from the repo (uses defaults; does NOT touch the running service since the live unit still points at the old path). Verify manifest + read-only code + shared symlinks. Note: HEAD ≠ working tree — the uncommitted provider-resilience work won't be in this smoke release; that's expected and stated in the report.**
- [ ] **Step 8: Commit** — `git commit -m "feat(deploy): immutable versioned releases + atomic rollback (audit §14)"`

---

### Task 9: Env documentation (`.env.example`)

**Files:**
- Modify: `.env.example`

- [ ] **Step 1: Append**

```bash
# --- Route authentication (security hardening) ---
# off (default, legacy) | shadow (log-only) | enforce (fail closed)
AUTH_MODE=off
# Comma-separated token lists per role; >=16 chars each. Generate with:
#   python3 -c "import secrets; print(secrets.token_urlsafe(32))"
AUTH_TOKEN_ADMIN=
AUTH_TOKEN_OPERATOR=
AUTH_TOKEN_VIEWER=
AUTH_TOKEN_SCHEDULER=

# --- Release deployment (scripts/release.sh / rollback.sh) ---
# RELEASES_DIR=~/releases/idx-walkforward
# CURRENT_LINK=~/idx-walkforward-current
```

- [ ] **Step 2: Commit** — `git commit -m "docs(env): auth + release settings in .env.example"`

---

### Task 10: Documentation (Phase "Docs")

**Files:**
- Create: `docs/SECURITY.md` — roles table, token generation, off→shadow→enforce migration path, curl examples (`Authorization: Bearer`, `X-API-Key`, `?api_key=`, `/auth/login` session flow), audit-trail query examples (`SELECT * FROM audit_events ORDER BY ts DESC LIMIT 20`), secret checklist (env-only secrets, 600 perms, redaction filter, no tracked secrets, rotation = edit .env + restart).
- Modify: `docs/OPERATIONS.md` — new sections: **Authentication** (pointer to SECURITY.md + enforce cutover runbook), **Release procedure** (`scripts/release.sh`, what the manifest contains, shared-path model), **Rollback** (`scripts/rollback.sh --list` / `rollback.sh <version>` + restart), **Startup validation** (what aborts boot and how to read the ConfigError list), **Audit trail** (where events live, what is recorded).

- [ ] **Step 1: Write both docs.** Content must match implemented behavior exactly (env var names, script paths, table schema).
- [ ] **Step 2: Commit** — `git commit -m "docs(security): auth, release, rollback, audit-trail operator guide"`

---

### Task 11: Full suite + deliverable report

- [ ] **Step 1: Run the complete test suite** — `venv/bin/python -m pytest -q`. Expected: previous 1284 green + all new security tests green, 0 failures. Fix anything broken (auth default off must not disturb any existing test).
- [ ] **Step 2: Write `Audit/SECURITY_RELEASE_HARDENING_2026-07-11.md`** — files modified, tests added, test results, remaining security risks (e.g., tokens are static bearer secrets — no expiry/rotation automation; UI under enforce needs `/auth/login`; TLS not terminated by the app; SQLite audit trail is same-disk), remaining operational risks (cutover to release-based systemd unit not yet executed; uncommitted branch state), updated production-readiness score with justification.
- [ ] **Step 3: Commit** — `git commit -m "docs(audit): security & release hardening completion report"`

---

## Self-Review

- **Spec coverage:** Phase 1 (route audit + classification + token auth + env secrets + fail closed + middleware + migration path) → Tasks 1–3, 9. Phase 2 (4 roles, protected op/config/provider/db/maintenance endpoints, read-only = authorized viewers) → Tasks 1–3 policy table. Phase 3 (credential audit, env vars, file perms, hardcoded secrets, log/stack-trace leakage) → Tasks 5, 6. Phase 4 (immutable dir, versioned, atomic symlink, rollback command, manifest, version metadata, never run from working tree) → Tasks 7, 8. Phase 5 (release/config/DB/provider validation, abort on failure) → Task 6 (+ manifest check). Phase 6 (manual scans, config changes, provider switches, auth failures, admin actions; separate from provider events) → Task 4. Phase 7 (auth/authz/invalid creds/permission/rollback/startup-validation tests + full suite) → per-task tests + Task 11. Docs → Task 10. Deliverable report → Task 11. "Expired credentials" from Phase 7: static tokens have no expiry by design — the invalid-credential tests cover the rejection path; noted as a remaining risk in the report.
- **Placeholder scan:** Task 8 tests contain two `...` stubs for named-rollback/list tests — implementer must write them following the two complete tests above them (same fixture helpers, given). Task 6 manifest test sketched — follow the shown monkeypatch style. Acceptable: fixtures fully defined adjacent.
- **Type consistency:** `record_audit_event` signature identical in Tasks 3, 4; `required_level(rule, method)` used by middleware matches Task 2; role constants imported from `security.auth` everywhere.
