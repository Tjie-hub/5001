#!/usr/bin/env python3
"""Migrate the Investment Dashboard (port 5003) ledger into the Production OS.

Reads a 5003 snapshot JSON ({txns, CEQ, mfOpen, CMF, divs, eqPrices}) and
imports it into the canonical inv_* tables in walkforward.db via
data.investments.import_snapshot (idempotent — re-running adds nothing).

Usage:
    # dry run against the archived snapshot (default input)
    python3 scripts/migrate_investment_dashboard_5003.py

    # actually write
    python3 scripts/migrate_investment_dashboard_5003.py --apply

    # fetch a fresh snapshot from the Google Sheets backend first
    # (URL comes from INVESTMENT_DASHBOARD_SHEETS_URL; never hardcoded)
    INVESTMENT_DASHBOARD_SHEETS_URL=https://script.google.com/.../exec \
        python3 scripts/migrate_investment_dashboard_5003.py --fetch --apply
"""
import argparse
import json
import os
import sqlite3
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BASE))

from config import DB_PATH  # noqa: E402
from data import investments  # noqa: E402

DEFAULT_INPUT = _BASE / "backups" / "migration_5003_20260903" / "investment_dashboard_sheets_snapshot_20260903.json"


def fetch_sheets_snapshot(url):
    """Follow the Apps Script two-hop GET (exec -> user-content echo) and
    return the parsed snapshot. The URL is operator-supplied via env; no
    credentials are involved (the deployment is public, as it was for 5003)."""
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname != "script.google.com":
        raise SystemExit("refusing to fetch: url must be https://script.google.com/...")
    req = urllib.request.Request(url, headers={"User-Agent": "idx-walkforward-migration/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        if resp.status in (301, 302, 303, 307, 308):
            with urllib.request.urlopen(resp.headers["Location"], timeout=30) as final:
                return json.loads(final.read().decode("utf-8", "replace"))
        return json.loads(resp.read().decode("utf-8", "replace"))


def preview_counts(db_path):
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    counts = {}
    for table in ("inv_transactions", "inv_closed_equity", "inv_fund_positions",
                  "inv_dividends", "inv_prices"):
        counts[table] = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    conn.close()
    return counts


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", type=Path, default=DEFAULT_INPUT,
                    help="snapshot JSON path (default: archived migration snapshot)")
    ap.add_argument("--fetch", action="store_true",
                    help="fetch a fresh snapshot from $INVESTMENT_DASHBOARD_SHEETS_URL first")
    ap.add_argument("--apply", action="store_true",
                    help="write to the database (default: dry run)")
    ap.add_argument("--db", type=Path, default=None, help="override DB path (default config.DB_PATH)")
    args = ap.parse_args()

    if args.fetch:
        url = os.environ.get("INVESTMENT_DASHBOARD_SHEETS_URL", "").strip()
        if not url:
            ap.error("--fetch requires INVESTMENT_DASHBOARD_SHEETS_URL in the environment")
        print("fetching fresh snapshot from Google Sheets ...")
        snapshot = fetch_sheets_snapshot(url)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out = args.input.with_name(f"{args.input.stem}_fetched_{stamp}{args.input.suffix}")
        out.write_text(json.dumps(snapshot))
        print(f"  saved copy to {out}")
    else:
        if not args.input.exists():
            ap.error(f"snapshot not found: {args.input} (use --fetch or provide --input)")
        snapshot = json.loads(args.input.read_text())

    shape = {k: (len(v) if isinstance(v, list) else v) for k, v in snapshot.items()}
    print(f"snapshot shape: {shape}")

    db_path = str(args.db or DB_PATH)
    investments.init_investment_tables(db_path)
    before = preview_counts(db_path)
    print(f"before: {before}")

    if not args.apply:
        print("dry run — no rows written (pass --apply to import)")
        return

    counts = investments.import_snapshot(snapshot, db_path=db_path)
    after = preview_counts(db_path)
    print(f"imported: {counts}")
    print(f"after:  {after}")


if __name__ == "__main__":
    main()
