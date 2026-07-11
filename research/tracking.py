"""Experiment tracking + dataset fingerprinting (audit R-4, Phase A).

research_runs is an APPEND-ONLY ledger: one row per research batch run,
carrying run_id, git commit, dataset fingerprint, params, timings, status and
metrics. Starting a run INSERTs; finalizing UPDATEs only that run's own row
(fills finish fields). Rows are never replaced or deleted — history survives.

The dataset fingerprint identifies the research input exactly: the settled
ohlcv corpus AND the corporate_actions table that adjusts it. Integer-sum
per-ticker checksums keep it order-independent and cheap (~1s on the 1M-row
corpus).
"""
import hashlib
import json
import os
import subprocess
import time
import uuid
from contextlib import contextmanager
from datetime import datetime

from data.db import connect as db_connect

DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "data", "walkforward.db"))

RESEARCH_RUNS_DDL = """
CREATE TABLE IF NOT EXISTS research_runs (
    run_id              TEXT PRIMARY KEY,
    kind                TEXT NOT NULL,
    git_commit          TEXT,
    dataset_fingerprint TEXT,
    params_json         TEXT,
    started_at          TEXT NOT NULL,
    finished_at         TEXT,
    duration_s          REAL,
    status              TEXT NOT NULL,
    metrics_json        TEXT,
    error               TEXT
)
"""


def ensure_research_runs_table(conn) -> None:
    conn.execute(RESEARCH_RUNS_DDL)


def git_commit():
    """Current HEAD hash, or None outside a repo / without git. Fail-soft."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=os.path.dirname(os.path.abspath(__file__)),
            capture_output=True, text=True, timeout=5)
        if out.returncode == 0:
            return out.stdout.strip()
    except Exception:
        pass
    return None


def dataset_fingerprint(conn) -> dict:
    """{'max_date','total_rows','sha256'} for the settled research corpus.

    Per-ticker (count, min/max date, integer close+volume sums) lines hashed
    together with the corporate_actions summary. Integer sums are
    order-independent, so the value is stable for identical data regardless
    of query plan.
    """
    per_ticker = ("SELECT ticker, COUNT(*), MIN(date), MAX(date), "
                  "SUM(CAST(close AS INTEGER)), SUM(CAST(volume AS INTEGER)) "
                  "FROM ohlcv {where}GROUP BY ticker ORDER BY ticker")
    try:
        rows = conn.execute(per_ticker.format(
            where="WHERE COALESCE(is_final, 1) = 1 ")).fetchall()
    except Exception:   # pre-migration DB without is_final
        rows = conn.execute(per_ticker.format(where="")).fetchall()
    try:
        ca = conn.execute(
            "SELECT COUNT(*), COALESCE(MAX(date), ''), "
            "COALESCE(SUM(CAST(value * 10000 AS INTEGER)), 0) "
            "FROM corporate_actions").fetchone()
    except Exception:
        ca = (0, "", 0)
    h = hashlib.sha256()
    for r in rows:
        h.update("|".join(str(x) for x in r).encode())
        h.update(b"\n")
    h.update(f"corporate_actions|{ca[0]}|{ca[1]}|{ca[2]}".encode())
    total_rows = sum(r[1] for r in rows)
    max_date = max((r[3] for r in rows), default=None)
    return {"max_date": max_date, "total_rows": total_rows,
            "sha256": h.hexdigest()}


class RunHandle:
    """Mutate .metrics inside the `with track_run(...)` block; they are
    persisted on exit."""

    def __init__(self, run_id: str):
        self.run_id = run_id
        self.metrics = {}


@contextmanager
def track_run(kind: str, params: dict = None, db_path: str = None):
    """Record one research run in research_runs (append-only).

    INSERTs a RUNNING row up front (fingerprint + git commit captured before
    the work), yields a RunHandle, and finalizes to DONE/ERROR on exit.
    Exceptions propagate after being recorded.
    """
    db_path = db_path or DB_PATH
    run = RunHandle(uuid.uuid4().hex)
    started = time.monotonic()
    conn = db_connect(db_path)
    try:
        ensure_research_runs_table(conn)
        fp = dataset_fingerprint(conn)
        conn.execute(
            "INSERT INTO research_runs (run_id, kind, git_commit, "
            "dataset_fingerprint, params_json, started_at, status) "
            "VALUES (?,?,?,?,?,?, 'RUNNING')",
            (run.run_id, kind, git_commit(), fp["sha256"],
             json.dumps(params or {}),
             datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
    finally:
        conn.close()

    def _finalize(status, error=None):
        conn = db_connect(db_path)
        try:
            conn.execute(
                "UPDATE research_runs SET finished_at=?, duration_s=?, "
                "status=?, metrics_json=?, error=? WHERE run_id=?",
                (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                 round(time.monotonic() - started, 3), status,
                 json.dumps(run.metrics), error, run.run_id))
            conn.commit()
        finally:
            conn.close()

    try:
        yield run
    except BaseException as e:
        _finalize("ERROR", error=str(e))
        raise
    _finalize("DONE")


def ensure_column(conn, table: str, column: str, decl: str = "TEXT") -> None:
    """Idempotent ALTER TABLE ADD COLUMN — backward-compatible run_id stamping
    on pre-existing research output tables."""
    cols = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
    if cols and column not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")
