"""Phase E CLI (spec §3): record hypotheses/failures, run backfill, inspect the
knowledge base. Mirrors research/gatekeeper/cli.py argparse style."""
from __future__ import annotations

import argparse
import json
import sys

from data.db import connect
from research.knowledge import backfill, ingest, storage, trace
from research.knowledge.models import Hypothesis


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    p = argparse.ArgumentParser(prog="knowledge",
                                description="Phase E research knowledge base")
    p.add_argument("--db", default="walkforward.db", help="sqlite path")
    sub = p.add_subparsers(dest="cmd", required=True)

    rh = sub.add_parser("record-hypothesis")
    rh.add_argument("--id", required=True)
    rh.add_argument("--title", required=True)
    rh.add_argument("--rationale", default="")

    rf = sub.add_parser("record-failure")
    rf.add_argument("--id", default=None, help="hypothesis_id (optional)")
    rf.add_argument("--reason", required=True)

    tr = sub.add_parser("trace")
    tr.add_argument("--id", required=True)

    sub.add_parser("orphans")
    sub.add_parser("backfill")

    args = p.parse_args(argv)
    conn = connect(args.db)
    storage.ensure_knowledge_tables(conn)

    if args.cmd == "record-hypothesis":
        storage.record_hypothesis(conn, Hypothesis(hypothesis_id=args.id,
                                                   title=args.title,
                                                   rationale=args.rationale))
        print(f"recorded {args.id}")
    elif args.cmd == "record-failure":
        fid = ingest.record_failure(conn, args.id, args.reason)
        print(f"failure {fid}" if fid else "duplicate failure (no-op)")
    elif args.cmd == "trace":
        print(json.dumps(trace.trace(conn, args.id), indent=2, default=str))
    elif args.cmd == "orphans":
        print(json.dumps(trace.orphan_report(conn), indent=2))
    elif args.cmd == "backfill":
        print(json.dumps(backfill.seed_known_hypotheses(conn), indent=2))

    conn.close()
    return 0


if __name__ == "__main__":                              # pragma: no cover
    raise SystemExit(main())
