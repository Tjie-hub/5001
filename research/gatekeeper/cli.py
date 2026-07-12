"""Gatekeeper CLI (spec §3):

    python -m research.gatekeeper.cli evaluate --strategy "NR7 Breakout" \
        [--db path] [--config path] [--report path] [--universe AAA,BBB]

Thin glue over candidate.build_candidate + pipeline.run_gate; both are injectable so
the wiring is unit-testable without a corpus.
"""
from __future__ import annotations

import argparse
import sys

from data.db import connect
from research.gatekeeper import candidate as _candidate
from research.gatekeeper import pipeline as _pipeline
from research.gatekeeper.config import load_config


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="research.gatekeeper.cli",
                                description="Statistical Gatekeeper (Phase C)")
    sub = p.add_subparsers(dest="cmd", required=True)
    ev = sub.add_parser("evaluate", help="run the gate on a strategy")
    ev.add_argument("--strategy", required=True)
    ev.add_argument("--db", default=None)
    ev.add_argument("--config", default=None)
    ev.add_argument("--report", default=None)
    ev.add_argument("--universe", default=None,
                    help="comma-separated tickers; default = all in ohlcv")
    return p


def _default_universe(conn):
    return [r[0] for r in conn.execute(
        "SELECT DISTINCT ticker FROM ohlcv WHERE ticker != 'IHSG'")]


def evaluate(args, build_candidate_fn=None, run_gate_fn=None):
    build_candidate_fn = build_candidate_fn or _candidate.build_candidate
    run_gate_fn = run_gate_fn or _pipeline.run_gate
    config = load_config(args.config)
    conn = connect(args.db) if args.db else connect(_pipeline.DB_PATH)
    universe = (args.universe.split(",") if args.universe
                else _default_universe(conn))
    candidate = build_candidate_fn(conn, args.strategy, universe, config)
    conn.close()
    decision = run_gate_fn(candidate, config, db_path=args.db,
                           report_path=args.report)
    print(f"DECISION: {decision.final_state}"
          + (f" (failing: {decision.failing_stage})" if decision.failing_stage else ""))
    return decision


def main(argv=None):
    args = build_parser().parse_args(argv if argv is not None else sys.argv[1:])
    if args.cmd == "evaluate":
        evaluate(args)


if __name__ == "__main__":
    main()
