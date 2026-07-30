"""P0.E2.S3.T1 -- /metrics idx_market_risk_score column fix (L-1).

Audit L-1: the /metrics endpoint's SQL queried market_risk_log for columns
risk_score/computed_at; the table's real columns (engine/risk_alert.py's
_ensure_table) are score/created_at. Every query against the real table
silently failed (caught generically by app.py's _q() helper, which returns
None on any exception) -- the idx_market_risk_score gauge was permanently
NaN regardless of how much data market_risk_log actually held.
"""
import re
import sqlite3

import pytest


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db = tmp_path / "test.db"
    conn = sqlite3.connect(str(db))
    conn.execute("""
        CREATE TABLE market_risk_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_time TEXT,
            date TEXT,
            time TEXT,
            tier TEXT,
            score REAL,
            sent INTEGER DEFAULT 0,
            components TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
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


def _gauge_value(body: str, name: str) -> str:
    m = re.search(rf'^{re.escape(name)} (\S+)$', body, re.MULTILINE)
    assert m, f"gauge {name} not found in body:\n{body}"
    return m.group(1)


def test_metrics_returns_200(client):
    c, _ = client
    resp = c.get("/metrics")
    assert resp.status_code == 200


def test_idx_market_risk_score_is_nan_when_table_empty(client):
    """No rows -> no data, correctly NaN (not the bug -- this is the
    legitimate 'nothing scored yet' case, kept as a control)."""
    c, _ = client
    resp = c.get("/metrics")
    body = resp.data.decode()
    assert _gauge_value(body, "idx_market_risk_score") == "NaN"


def test_idx_market_risk_score_reflects_most_recent_score(client):
    """The regression case: real data present, using the table's actual
    columns (score/created_at) -- must NOT be NaN, and must reflect the
    most recently created row, not the highest score or insertion order
    coincidence."""
    c, db_path = client
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO market_risk_log (scan_time, date, time, tier, score, created_at) "
        "VALUES (?,?,?,?,?,?)",
        ("2026-07-29 09:00:00", "2026-07-29", "09:00", "ORANGE", 42.5, "2026-07-29 09:00:05"),
    )
    conn.execute(
        "INSERT INTO market_risk_log (scan_time, date, time, tier, score, created_at) "
        "VALUES (?,?,?,?,?,?)",
        ("2026-07-30 09:00:00", "2026-07-30", "09:00", "RED", 71.0, "2026-07-30 09:00:05"),
    )
    conn.commit()
    conn.close()

    resp = c.get("/metrics")
    body = resp.data.decode()
    assert _gauge_value(body, "idx_market_risk_score") == "71.0"
