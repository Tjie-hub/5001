"""R-5 Tier-1 physical DB split -- one-shot cutover runbook (NOT a cron job).

    python -m scripts.migrate_r5_tier1                          # dry run (default)
    python -m scripts.migrate_r5_tier1 --apply                  # actually migrate + drop

Before running --apply against the real data/walkforward.db:
  1. Take a fresh backup: python -m scripts.db_backup
  2. Stop any cron jobs that might be mid-write to a Tier-1 table (wf-refresh,
     backtest-cache, roller, gatekeeper/regime/knowledge CLIs) -- the migration
     itself briefly holds a write lock on the source for each table's DROP.
  3. Run this script with --apply.
  4. Verify: python -m research.regime.cli query <some strategy> against the
     new data/research.db should succeed; check docs/superpowers/plans/
     2026-07-21-r5-tier1-physical-db-split.md Task 10 Step 5 for the full
     verification checklist.

See docs/superpowers/specs/2026-07-14-r5-physical-db-split-scope.md for the
full design rationale.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from data.db import DB_PATH as DEFAULT_PROD_DB
from research.db import RESEARCH_DB_PATH as DEFAULT_RESEARCH_DB
from research.db_migration import migrate_tier1


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    ap = argparse.ArgumentParser(prog="migrate_r5_tier1")
    ap.add_argument("--prod-db", type=Path, default=Path(DEFAULT_PROD_DB))
    ap.add_argument("--research-db", type=Path, default=Path(DEFAULT_RESEARCH_DB))
    ap.add_argument("--apply", action="store_true",
                    help="actually perform the migration (default: dry run, no writes)")
    args = ap.parse_args(argv)

    if not args.apply:
        print("DRY RUN -- no files will be modified. Pass --apply to execute.")
        print(f"  source (prod):     {args.prod_db}")
        print(f"  destination:       {args.research_db}")
        if not args.prod_db.exists():
            print(f"  NOTE: {args.prod_db} does not exist -- nothing to migrate yet")
            return 0
        import sqlite3
        from research.db import TIER1_TABLES
        conn = sqlite3.connect(f"file:{args.prod_db}?mode=ro", uri=True)
        for table in TIER1_TABLES:
            row = conn.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?",
                (table,)).fetchone()
            if row[0]:
                count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                print(f"  would migrate: {table} ({count} rows)")
            else:
                print(f"  already migrated (absent from source): {table}")
        conn.close()
        return 0

    report = migrate_tier1(str(args.prod_db), str(args.research_db))
    for table, info in report.items():
        status = "migrated+dropped" if info["dropped"] else "skipped (already migrated)"
        print(f"  {table}: {status} ({info['copied']} rows)")
    print(f"done -- {args.research_db} now holds the Tier-1 tables")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
