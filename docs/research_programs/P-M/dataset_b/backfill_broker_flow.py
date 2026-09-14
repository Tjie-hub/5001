"""Dataset B broker-flow historical backfill fetcher (limit=150).

Standalone capture script — deliberately does NOT import stockbit_fetcher.py
or any production module. It re-implements only the HTTP call (same
endpoint/headers/params/429-backoff shape already validated live in the
Stage-3 vendor probe and the Stage-5 one-month limit=150 trial) so this
script is structurally incapable of touching production code paths,
production DB writes, or the scheduler.

Writes ONLY to a dedicated, versioned SQLite store under
dataset_b/store/ — never to data/walkforward.db's `broker_flow` table.
Resumable/idempotent: every cell is keyed (ticker, session_date) in
capture_manifest; a rerun skips any cell already in a terminal state.

Cadence is fixed at 1.5s/request per the already-passed trial. This script
does not redesign or re-run that trial.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import sqlite3
import sys
import time
import uuid
from datetime import datetime, timezone

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
TOKEN_FILE = os.path.join(REPO_ROOT, ".stockbit_token")
ROSTER_ARTIFACT = os.path.join(HERE, "artifacts", "DATASET_B_PIT_ROSTER_v1.json")
STORE_DIR = os.path.join(HERE, "store")
STORE_DB = os.path.join(STORE_DIR, "DATASET_B_BROKER_FLOW_STORE_v1.sqlite")

STOCKBIT_BASE = "https://exodus.stockbit.com"
CAPTURE_VERSION = "v1"
LIMIT_PARAM = 150
CADENCE_S = 1.5
MAX_ATTEMPTS = 4
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS capture_manifest (
  ticker TEXT NOT NULL,
  session_date TEXT NOT NULL,
  status TEXT NOT NULL,
  http_status INTEGER,
  requested_from TEXT,
  requested_to TEXT,
  returned_from TEXT,
  returned_to TEXT,
  date_echo_match INTEGER,
  n_buy INTEGER,
  n_sell INTEGER,
  truncated_buy INTEGER,
  truncated_sell INTEGER,
  latency_ms REAL,
  retry_count INTEGER,
  error TEXT,
  captured_at_utc TEXT NOT NULL,
  capture_version TEXT NOT NULL,
  PRIMARY KEY (ticker, session_date)
);

CREATE TABLE IF NOT EXISTS broker_flow_b (
  ticker TEXT NOT NULL,
  trade_date TEXT NOT NULL,
  broker_code TEXT NOT NULL,
  side TEXT NOT NULL,
  lot INTEGER,
  lot_value INTEGER,
  value INTEGER,
  value_total INTEGER,
  avg_price REAL,
  freq INTEGER,
  investor_type TEXT,
  capture_version TEXT NOT NULL,
  PRIMARY KEY (ticker, trade_date, broker_code, side)
);

CREATE TABLE IF NOT EXISTS bandar_detector_b (
  ticker TEXT NOT NULL,
  trade_date TEXT NOT NULL,
  avg_price REAL,
  total_buyer INTEGER,
  total_seller INTEGER,
  net_broker_count INTEGER,
  broker_accdist REAL,
  value REAL,
  volume REAL,
  top1_accdist REAL,
  top3_accdist REAL,
  top5_accdist REAL,
  top10_accdist REAL,
  avg_accdist REAL,
  capture_version TEXT NOT NULL,
  captured_at_utc TEXT NOT NULL,
  PRIMARY KEY (ticker, trade_date)
);

CREATE TABLE IF NOT EXISTS raw_responses (
  ticker TEXT NOT NULL,
  session_date TEXT NOT NULL,
  http_status INTEGER,
  raw_json_gz BLOB,
  captured_at_utc TEXT NOT NULL,
  capture_version TEXT NOT NULL,
  PRIMARY KEY (ticker, session_date)
);

CREATE TABLE IF NOT EXISTS capture_run_log (
  run_id TEXT NOT NULL,
  started_at_utc TEXT,
  finished_at_utc TEXT,
  code_sha256 TEXT,
  roster_artifact_sha256 TEXT,
  cells_intended INTEGER,
  cells_attempted INTEGER,
  cells_success INTEGER,
  cells_empty INTEGER,
  cells_failed INTEGER,
  cadence_s REAL,
  limit_param INTEGER,
  host TEXT,
  note TEXT,
  PRIMARY KEY (run_id)
);
"""

TERMINAL_STATUSES = {"SUCCESS", "EMPTY"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_of_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def load_token() -> str:
    with open(TOKEN_FILE, "r") as f:
        return f.read().strip()


def load_cells() -> list[tuple[str, str]]:
    """Return the exact intended (ticker, session_date) cells from the frozen PIT roster."""
    with open(ROSTER_ARTIFACT, "r") as f:
        roster = json.load(f)
    cells = []
    for session, members in roster["session_members"].items():
        for ticker in members:
            cells.append((ticker, session))
    cells.sort(key=lambda c: (c[1], c[0]))
    return cells, roster["sha256"]


def init_store() -> sqlite3.Connection:
    os.makedirs(STORE_DIR, exist_ok=True)
    conn = sqlite3.connect(STORE_DB)
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 30000")
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


def already_done(conn: sqlite3.Connection) -> set[tuple[str, str]]:
    cur = conn.execute(
        "SELECT ticker, session_date FROM capture_manifest WHERE status IN ('SUCCESS','EMPTY')"
    )
    return {(r[0], r[1]) for r in cur.fetchall()}


def fetch_one(token: str, ticker: str, session_date: str) -> dict:
    """Fetch a single (ticker, session_date) cell at limit=150. Never substitutes a date."""
    params = {
        "transaction_type": "TRANSACTION_TYPE_NET",
        "market_board": "MARKET_BOARD_REGULER",
        "investor_type": "INVESTOR_TYPE_ALL",
        "limit": LIMIT_PARAM,
        "from": session_date,
        "to": session_date,
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": USER_AGENT,
        "Origin": "https://stockbit.com",
        "Referer": "https://stockbit.com/",
    }
    retry_count = 0
    t0 = time.monotonic()
    r = None
    err = None
    for attempt in range(MAX_ATTEMPTS):
        try:
            r = requests.get(
                f"{STOCKBIT_BASE}/marketdetectors/{ticker}",
                params=params, headers=headers, timeout=15,
            )
        except requests.RequestException as e:
            err = str(e)
            r = None
            retry_count = attempt + 1
            time.sleep(5 * (attempt + 1))
            continue
        if r.status_code == 200:
            break
        if r.status_code == 429:
            retry_count = attempt + 1
            wait = int(r.headers.get("Retry-After", 0)) or 20 * (attempt + 1)
            time.sleep(wait)
            continue
        # Non-200, non-429: don't retry further, record as HTTP_ERROR
        break
    latency_ms = (time.monotonic() - t0) * 1000.0

    if r is None:
        return {
            "status": "EXCEPTION", "http_status": None, "error": err,
            "retry_count": retry_count, "latency_ms": latency_ms,
            "requested_from": session_date, "requested_to": session_date,
        }
    if r.status_code == 429:
        return {
            "status": "RATE_LIMIT_EXCEEDED", "http_status": 429, "error": None,
            "retry_count": retry_count, "latency_ms": latency_ms,
            "requested_from": session_date, "requested_to": session_date,
        }
    if r.status_code != 200:
        return {
            "status": "HTTP_ERROR", "http_status": r.status_code,
            "error": r.text[:500] if r.text else None,
            "retry_count": retry_count, "latency_ms": latency_ms,
            "requested_from": session_date, "requested_to": session_date,
        }

    body = r.json()
    d = body.get("data", {}) or {}
    returned_from = d.get("from")
    returned_to = d.get("to")
    date_echo_match = (returned_to == session_date)

    bs = d.get("broker_summary", {}) or {}
    bd = d.get("bandar_detector", {}) or {}
    buys = bs.get("brokers_buy", []) or []
    sells = bs.get("brokers_sell", []) or []

    return {
        "status": "DATE_ECHO_MISMATCH" if not date_echo_match else (
            "EMPTY" if (not buys and not sells) else "SUCCESS"
        ),
        "http_status": 200, "error": None,
        "retry_count": retry_count, "latency_ms": latency_ms,
        "requested_from": session_date, "requested_to": session_date,
        "returned_from": returned_from, "returned_to": returned_to,
        "date_echo_match": date_echo_match,
        "n_buy": len(buys), "n_sell": len(sells),
        "truncated_buy": len(buys) >= LIMIT_PARAM,
        "truncated_sell": len(sells) >= LIMIT_PARAM,
        "raw_body": body,
        "buys": buys, "sells": sells, "bandar": bd,
    }


def persist(conn: sqlite3.Connection, ticker: str, session_date: str, result: dict) -> None:
    now = utc_now()
    conn.execute(
        """INSERT OR REPLACE INTO capture_manifest
           (ticker, session_date, status, http_status, requested_from, requested_to,
            returned_from, returned_to, date_echo_match, n_buy, n_sell,
            truncated_buy, truncated_sell, latency_ms, retry_count, error,
            captured_at_utc, capture_version)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            ticker, session_date, result["status"], result.get("http_status"),
            result.get("requested_from"), result.get("requested_to"),
            result.get("returned_from"), result.get("returned_to"),
            int(result["date_echo_match"]) if result.get("date_echo_match") is not None else None,
            result.get("n_buy"), result.get("n_sell"),
            int(result["truncated_buy"]) if result.get("truncated_buy") is not None else None,
            int(result["truncated_sell"]) if result.get("truncated_sell") is not None else None,
            result.get("latency_ms"), result.get("retry_count"), result.get("error"),
            now, CAPTURE_VERSION,
        ),
    )

    if result["status"] in ("SUCCESS", "EMPTY"):
        raw_gz = gzip.compress(json.dumps(result["raw_body"]).encode("utf-8"))
        conn.execute(
            """INSERT OR REPLACE INTO raw_responses
               (ticker, session_date, http_status, raw_json_gz, captured_at_utc, capture_version)
               VALUES (?,?,?,?,?,?)""",
            (ticker, session_date, result["http_status"], raw_gz, now, CAPTURE_VERSION),
        )

    if result["status"] == "SUCCESS":
        trade_date = result["returned_to"]
        for b in result["buys"]:
            conn.execute(
                """INSERT OR REPLACE INTO broker_flow_b
                   (ticker, trade_date, broker_code, side, lot, lot_value, value,
                    value_total, avg_price, freq, investor_type, capture_version)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    ticker, trade_date, b.get("netbs_broker_code", ""), "BUY",
                    int(float(b.get("blot", 0))), int(float(b.get("blotv", 0))),
                    int(float(b.get("bval", 0))), int(float(b.get("bvalv", 0))),
                    float(b.get("netbs_buy_avg_price", 0)), int(b.get("freq", 0)),
                    b.get("type", ""), CAPTURE_VERSION,
                ),
            )
        for b in result["sells"]:
            conn.execute(
                """INSERT OR REPLACE INTO broker_flow_b
                   (ticker, trade_date, broker_code, side, lot, lot_value, value,
                    value_total, avg_price, freq, investor_type, capture_version)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    ticker, trade_date, b.get("netbs_broker_code", ""), "SELL",
                    int(float(b.get("slot", 0))), int(float(b.get("slotv", 0))),
                    int(float(b.get("sval", 0))), int(float(b.get("svalv", 0))),
                    float(b.get("netbs_sell_avg_price", 0)), int(b.get("freq", 0)),
                    b.get("type", ""), CAPTURE_VERSION,
                ),
            )
        bd = result["bandar"]
        conn.execute(
            """INSERT OR REPLACE INTO bandar_detector_b
               (ticker, trade_date, avg_price, total_buyer, total_seller,
                net_broker_count, broker_accdist, value, volume,
                top1_accdist, top3_accdist, top5_accdist, top10_accdist, avg_accdist,
                capture_version, captured_at_utc)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                ticker, trade_date, bd.get("average"), bd.get("total_buyer"),
                bd.get("total_seller"), bd.get("number_broker_buysell"),
                bd.get("broker_accdist"), bd.get("value"), bd.get("volume"),
                (bd.get("top1") or {}).get("accdist"), (bd.get("top3") or {}).get("accdist"),
                (bd.get("top5") or {}).get("accdist"), (bd.get("top10") or {}).get("accdist"),
                (bd.get("avg") or {}).get("accdist"), CAPTURE_VERSION, now,
            ),
        )
    conn.commit()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit-cells", type=int, default=None,
                     help="Cap number of NEW cells this run (for smoke tests)")
    ap.add_argument("--dry-run", action="store_true",
                     help="Compute scope only, no network calls")
    args = ap.parse_args()

    cells, roster_sha = load_cells()
    conn = init_store()
    done = already_done(conn)
    pending = [c for c in cells if c not in done]

    print(f"[dataset_b backfill] intended={len(cells)} already_done={len(done)} pending={len(pending)}")
    if args.dry_run:
        conn.close()
        return

    token = load_token()
    code_sha = sha256_of_file(os.path.abspath(__file__))
    run_id = str(uuid.uuid4())
    started = utc_now()
    n_success = n_empty = n_failed = 0

    todo = pending if args.limit_cells is None else pending[: args.limit_cells]
    for i, (ticker, session) in enumerate(todo):
        result = fetch_one(token, ticker, session)
        persist(conn, ticker, session, result)
        if result["status"] == "SUCCESS":
            n_success += 1
        elif result["status"] == "EMPTY":
            n_empty += 1
        else:
            n_failed += 1
        if (i + 1) % 200 == 0 or (i + 1) == len(todo):
            print(f"[dataset_b backfill] {i+1}/{len(todo)} "
                  f"success={n_success} empty={n_empty} failed={n_failed} "
                  f"last={ticker}@{session}={result['status']}")
        time.sleep(CADENCE_S)

    finished = utc_now()
    conn.execute(
        """INSERT INTO capture_run_log
           (run_id, started_at_utc, finished_at_utc, code_sha256, roster_artifact_sha256,
            cells_intended, cells_attempted, cells_success, cells_empty, cells_failed,
            cadence_s, limit_param, host, note)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            run_id, started, finished, code_sha, roster_sha,
            len(cells), len(todo), n_success, n_empty, n_failed,
            CADENCE_S, LIMIT_PARAM, os.uname().nodename,
            "Stage-6 Dataset B broker-flow limit=150 historical backfill",
        ),
    )
    conn.commit()
    conn.close()
    print(f"[dataset_b backfill] DONE run_id={run_id} attempted={len(todo)} "
          f"success={n_success} empty={n_empty} failed={n_failed}")


if __name__ == "__main__":
    main()
