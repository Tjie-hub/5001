#!/usr/bin/env python3
"""
Standalone coverage/quality check for the stockbit_flow dataset.

Applies the rules in docs/data/DATA_QUALITY_RULES.md against the contract in
docs/data/DATASET_CONTRACT_STOCKBIT_FLOW.md. Read-only: never writes to any
table, never imports scheduler/engine/research code, never changes ingestion
behavior. Safe to run at any time, including against production data.

Exit code policy (rule R8 — fail only on what can be classified with
certainty):
    0  no genuine integrity problems found (warnings may still be printed)
    1  at least one genuine integrity problem found:
         - a zero-row trading date inside the supported retention window (R6)
         - a duplicate (ticker, trade_date) primary key (R3)
    2  could not run the check at all (e.g. DB unreadable)

Partial-coverage dates and blank-trade_date rows are always reported but
never affect the exit code (R5, R2) — see DATA_QUALITY_RULES.md for why.

Usage:
    venv/bin/python3 tools/check_stockbit_flow_coverage.py [--db PATH] [--json]
"""
import argparse
import json
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
DEFAULT_DB = HERE / "data" / "walkforward.db"

# Established in docs/audit/STOCKBIT_FLOW_BACKFILL_FEASIBILITY.md by bisecting
# live requests to single-day precision: 2024-12-30 -> empty payload,
# 2025-01-02 -> real data. Fixed boundary, not a rolling window.
RETENTION_BOUNDARY = "2025-01-02"

# Mirrors the local-trailing-baseline heuristic already used in production by
# scheduler/jobs.py::check_flow_coverage — reimplemented standalone here
# rather than imported, to keep this tool independent of scheduler/engine
# code (task constraint: no production-engine dependency).
PARTIAL_LOOKBACK = 10
PARTIAL_HARD_FLOOR = 50


def _connect(db_path: Path) -> sqlite3.Connection:
    # Read-only: a dedicated, minimal connection — deliberately not routed
    # through data.db.connect() so this tool has zero import dependency on
    # the app's own code (task constraint: tooling only, no engine coupling).
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=30)
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


def trading_dates(conn: sqlite3.Connection) -> list[str]:
    return sorted(r[0] for r in conn.execute("SELECT DISTINCT date FROM ohlcv WHERE date != ''"))


def flow_dates_with_counts(conn: sqlite3.Connection) -> dict[str, int]:
    rows = conn.execute(
        "SELECT trade_date, COUNT(DISTINCT ticker) FROM stockbit_flow "
        "WHERE trade_date != '' GROUP BY trade_date"
    ).fetchall()
    return {d: c for d, c in rows}


def blank_trade_date_count(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COUNT(*) FROM stockbit_flow WHERE trade_date = ''").fetchone()[0]


def duplicate_keys(conn: sqlite3.Connection) -> list[tuple[str, str, int]]:
    """Defense-in-depth: the PRIMARY KEY should make this impossible via normal
    INSERT OR REPLACE, but a validator should not assume the constraint was
    never bypassed (R3)."""
    rows = conn.execute(
        "SELECT ticker, trade_date, COUNT(*) c FROM stockbit_flow "
        "GROUP BY ticker, trade_date HAVING c > 1"
    ).fetchall()
    return rows


def find_partial_dates(counts_by_date: dict[str, int], in_window_dates: list[str]) -> list[dict]:
    """R5: flag dates whose ticker coverage sits far below their trailing local
    median. Informational only — never affects the exit code."""
    ordered = sorted(counts_by_date)
    partial = []
    for d in in_window_dates:
        count = counts_by_date.get(d, 0)
        if count == 0:
            continue  # zero-row dates are gaps (R6), reported separately
        prior = [counts_by_date[p] for p in ordered if p < d and counts_by_date[p] > 0][-PARTIAL_LOOKBACK:]
        if not prior:
            continue
        prior_sorted = sorted(prior)
        m = len(prior_sorted)
        baseline = prior_sorted[m // 2] if m % 2 else (prior_sorted[m // 2 - 1] + prior_sorted[m // 2]) // 2
        threshold = max(PARTIAL_HARD_FLOOR, int(0.5 * baseline))
        if count < threshold:
            partial.append({"date": d, "count": count, "baseline": baseline, "threshold": threshold})
    return partial


def run_check(db_path: Path) -> dict:
    conn = _connect(db_path)
    try:
        ohlcv_dates = trading_dates(conn)
        counts_by_date = flow_dates_with_counts(conn)
        blanks = blank_trade_date_count(conn)
        dupes = duplicate_keys(conn)
    finally:
        conn.close()

    flow_dates = set(counts_by_date)
    earliest_flow_date = min(flow_dates) if flow_dates else None

    in_window = [d for d in ohlcv_dates if d >= RETENTION_BOUNDARY]
    out_of_window = [d for d in ohlcv_dates if d < RETENTION_BOUNDARY]

    gaps_after_boundary = [d for d in in_window if d not in flow_dates]
    expected_absent_before_boundary = [d for d in out_of_window if d not in flow_dates]

    partial_dates = find_partial_dates(counts_by_date, in_window)

    earliest_before_boundary = bool(earliest_flow_date and earliest_flow_date < RETENTION_BOUNDARY)

    genuine_problems = bool(gaps_after_boundary or dupes)

    return {
        "retention_boundary": RETENTION_BOUNDARY,
        "ohlcv_trading_dates_total": len(ohlcv_dates),
        "stockbit_flow_distinct_dates": len(flow_dates),
        "earliest_flow_date": earliest_flow_date,
        "earliest_before_boundary_anomaly": earliest_before_boundary,
        "gaps_after_boundary": gaps_after_boundary,
        "gaps_after_boundary_count": len(gaps_after_boundary),
        "expected_absent_before_boundary_count": len(expected_absent_before_boundary),
        "partial_dates": partial_dates,
        "partial_dates_count": len(partial_dates),
        "duplicate_keys": [{"ticker": t, "trade_date": d, "count": c} for t, d, c in dupes],
        "duplicate_keys_count": len(dupes),
        "blank_trade_date_rows": blanks,
        "genuine_integrity_problems": genuine_problems,
    }


def print_report(result: dict) -> None:
    print("=== stockbit_flow coverage check ===")
    print(f"Retention boundary (contract): {result['retention_boundary']}")
    print(f"OHLCV trading dates (ground truth calendar): {result['ohlcv_trading_dates_total']}")
    print(f"stockbit_flow distinct dates: {result['stockbit_flow_distinct_dates']}")
    print(f"Earliest stockbit_flow date: {result['earliest_flow_date']}")
    if result["earliest_before_boundary_anomaly"]:
        print("  [WARN] earliest date is BEFORE the documented retention boundary — "
              "re-verify the contract, this is unexpected either way")
    print()
    print(f"Dates expected absent (before boundary, per contract R1): "
          f"{result['expected_absent_before_boundary_count']} — not a failure")
    print()
    gaps = result["gaps_after_boundary"]
    print(f"GENUINE GAPS after boundary (R6): {result['gaps_after_boundary_count']}")
    for d in gaps[:20]:
        print(f"  ✗ {d}")
    if len(gaps) > 20:
        print(f"  ... and {len(gaps) - 20} more")
    print()
    partial = result["partial_dates"]
    print(f"Partial-coverage dates (R5, informational only): {result['partial_dates_count']}")
    for p in partial[:20]:
        print(f"  ~ {p['date']}: {p['count']} tickers (baseline {p['baseline']}, threshold {p['threshold']})")
    if len(partial) > 20:
        print(f"  ... and {len(partial) - 20} more")
    print()
    dupes = result["duplicate_keys"]
    print(f"Duplicate (ticker, trade_date) keys (R3): {result['duplicate_keys_count']}")
    for d in dupes[:20]:
        print(f"  ✗ {d['ticker']} {d['trade_date']} x{d['count']}")
    print()
    print(f"Blank trade_date rows (R2, expected artifact): {result['blank_trade_date_rows']}")
    print()
    if result["genuine_integrity_problems"]:
        print("RESULT: genuine integrity problem(s) found.")
    else:
        print("RESULT: no genuine integrity problems. (Warnings above, if any, are informational.)")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", type=Path, default=DEFAULT_DB, help="Path to walkforward.db (default: data/walkforward.db)")
    ap.add_argument("--json", action="store_true", help="Emit machine-readable JSON instead of a text report")
    args = ap.parse_args()

    try:
        result = run_check(args.db)
    except Exception as e:
        print(f"ERROR: could not run coverage check: {e}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print_report(result)

    return 1 if result["genuine_integrity_problems"] else 0


if __name__ == "__main__":
    sys.exit(main())
