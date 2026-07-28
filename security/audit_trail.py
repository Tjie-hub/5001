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
