#!/usr/bin/env python3
"""Dataset B feature-level fingerprint v2 — sourced from the materialized broker-flow
store, not the live production `broker_flow`/`bandar_detector` tables. READ-ONLY.

WHY V2
------
v1 (fingerprint.py) fingerprinted broker_flow/bandar_detector straight out of
production — a table truncated to the vendor's top-25-brokers-per-side cap
(blocker B1) and continuously appended to by the live scheduler (blocker B2),
so re-running v1 later is not guaranteed to reproduce the same digest, and the
value it pins was never the full population anyway.

v2 pins broker_flow/bandar_detector from the dedicated, frozen, limit=150
Dataset B capture (store/DATASET_B_BROKER_FLOW_STORE_v1.sqlite) instead —
static once written, immune to the production scheduler's ongoing writes, and
carrying the full observed broker population rather than the top-25 slice.
ohlcv is unchanged from v1: it is read from production because it is a
settled table for this window, not subject to the truncation/live-write
concern that motivated this file.

v1 is NOT deleted or overwritten — this is a superseding artifact, per the
same append-only-versions discipline as the rest of Dataset B provenance.
"""
import hashlib, json, sqlite3, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import foundation as F
from fingerprint import BROKER_FLOW_COLUMNS, BANDAR_COLUMNS, OHLCV_COLUMNS, _fold

HERE = Path(__file__).resolve().parent
STORE_PATH = HERE / "store" / "DATASET_B_BROKER_FLOW_STORE_v1.sqlite"


def store_connect(path: Path = STORE_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.execute("PRAGMA query_only = ON")
    return conn


def fingerprint_v2(prod_conn, store_conn, roster, cal, quarantined=()) -> dict:
    q = set(quarantined)
    cells = {(t, d) for d, m in roster.session_members.items() for t in m if t not in q}
    tickers = sorted({t for t, _ in cells})
    ph = ",".join("?" * len(tickers))
    lo, hi = cal.sessions[0], cal.sessions[-1]

    per_ticker = {}

    bf = {}
    for row in store_conn.execute(
            f"SELECT ticker, trade_date, {', '.join(BROKER_FLOW_COLUMNS)} FROM broker_flow_b "
            f"WHERE ticker IN ({ph}) AND trade_date >= ? AND trade_date <= ? "
            f"AND capture_version='v1'",
            tickers + [lo, hi]):
        if (row[0], row[1]) in cells:
            bf.setdefault(row[0], []).append(row[1:])
    bd = {}
    for row in store_conn.execute(
            f"SELECT ticker, trade_date, {', '.join(BANDAR_COLUMNS)} FROM bandar_detector_b "
            f"WHERE ticker IN ({ph}) AND trade_date >= ? AND trade_date <= ? "
            f"AND capture_version='v1'",
            tickers + [lo, hi]):
        if (row[0], row[1]) in cells:
            bd.setdefault(row[0], []).append(row[1:])
    px = {}
    for row in prod_conn.execute(
            f"SELECT ticker, date, {', '.join(OHLCV_COLUMNS)} FROM ohlcv "
            f"WHERE ticker IN ({ph}) AND date >= ? AND date <= ?", tickers + [lo, hi]):
        if (row[0], row[1]) in cells:
            px.setdefault(row[0], []).append(row[1:])

    for t in tickers:
        per_ticker[t] = {
            "broker_flow": {"rows": len(bf.get(t, [])), "fold": _fold(bf.get(t, []))},
            "bandar_detector": {"rows": len(bd.get(t, [])), "fold": _fold(bd.get(t, []))},
            "ohlcv": {"rows": len(px.get(t, [])), "fold": _fold(px.get(t, []))},
        }

    capture_manifest_totals = dict(store_conn.execute(
        "SELECT status, COUNT(*) FROM capture_manifest GROUP BY status"
    ).fetchall())
    capture_run = store_conn.execute(
        "SELECT code_sha256, limit_param, cadence_s FROM capture_run_log ORDER BY finished_at_utc DESC LIMIT 1"
    ).fetchone()

    body = {
        "artifact": "DATASET_B_FINGERPRINT", "version": "v2",
        "method": "per-ticker commutative SHA-256 fold; order-independent, value-sensitive",
        "source": {
            "broker_flow": "materialized_store:store/DATASET_B_BROKER_FLOW_STORE_v1.sqlite#broker_flow_b (capture_version=v1, limit=150)",
            "bandar_detector": "materialized_store:store/DATASET_B_BROKER_FLOW_STORE_v1.sqlite#bandar_detector_b (capture_version=v1, limit=150)",
            "ohlcv": "production_live_table:data/walkforward.db#ohlcv (settled window, unchanged from v1)",
        },
        "columns": {"broker_flow": BROKER_FLOW_COLUMNS, "bandar_detector": BANDAR_COLUMNS,
                    "ohlcv": OHLCV_COLUMNS},
        "roster_artifact_sha256": roster.sha256,
        "calendar_artifact_sha256": cal.sha256,
        "window": {"start": lo, "end": hi},
        "cells_in_scope": len(cells), "tickers": len(tickers),
        "quarantined": sorted(q),
        "capture_manifest_totals": capture_manifest_totals,
        "capture_code_sha256": capture_run[0] if capture_run else None,
        "capture_limit_param": capture_run[1] if capture_run else None,
        "capture_cadence_s": capture_run[2] if capture_run else None,
        "per_ticker": per_ticker,
    }
    canon = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    body["dataset_fingerprint"] = hashlib.sha256(canon).hexdigest()
    return body


def main(write=False):
    prod_conn = F.ro_connect()
    store_conn = store_connect()
    cal = F.SessionCalendar.load("v2"); ros = F.PitRoster.load("v1")
    rep = F.vwap_ratio_report(prod_conn, ros.universe, cal.sessions)
    fp = fingerprint_v2(prod_conn, store_conn, ros, cal, quarantined=rep["flagged"])
    print("=== Dataset B fingerprint v2 (materialized-store-sourced) ===")
    print(f"  broker_flow source : {fp['source']['broker_flow']}")
    print(f"  cells in scope     : {fp['cells_in_scope']:,} over {fp['tickers']} tickers")
    print(f"  quarantined        : {fp['quarantined']}")
    print(f"  capture manifest   : {fp['capture_manifest_totals']}")
    print(f"  DATASET FINGERPRINT: {fp['dataset_fingerprint']}")
    if write:
        p = HERE / "artifacts" / "DATASET_B_FINGERPRINT_v2.json"
        p.write_text(json.dumps(fp, indent=1, sort_keys=True) + "\n")
        (HERE / "artifacts" / f"{p.name}.sha256").write_text(
            f"{fp['dataset_fingerprint']}  {p.name}\n")
        print(f"\nwrote {p.name}")
    prod_conn.close(); store_conn.close(); return fp


if __name__ == "__main__":
    main(write="--write" in sys.argv)
