#!/usr/bin/env python3
"""Research CLI (spec §10-M3): the batch jobs that used to run on the
production scheduler. Cron-able; never imported by production.

Usage:
  python -m research.cli wf-refresh      # walk-forward scores + wf_edge (was Fri 16:00)
  python -m research.cli backtest-cache  # dashboard/quality-gate cache (was daily 08:30)
  python -m research.cli roller          # monthly window roller (was Sun 10:00)
  python -m research.cli wf-parity       # walk-forward under the PRODUCTION rule
                                         # (weekly MTF gate applied) -> wf_edge_rule
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main(argv=None):
    p = argparse.ArgumentParser(prog="research.cli")
    p.add_argument("job", choices=["wf-refresh", "backtest-cache", "roller",
                                   "wf-parity"])
    p.add_argument("--tickers", default="", help="wf-parity: restrict universe (csv)")
    p.add_argument("--strategies", default="", help="wf-parity: restrict roster (csv)")
    p.add_argument("--lock-job", default="", help="wf-parity: alternate lock name")
    p.add_argument("--restart", action="store_true",
                   help="wf-parity: ignore checkpoints and recompute every ticker")
    p.add_argument("--checkpoint-every", type=int, default=1,
                   help="wf-parity: tickers per persisted transaction (default 1)")
    args = p.parse_args(argv)
    from research import jobs
    if args.job == "wf-parity":
        tk = [t for t in args.tickers.split(",") if t.strip()] or None
        st = [x.strip() for x in args.strategies.split(",") if x.strip()] or None
        jobs.refresh_wf_edge_rule(tickers=tk, only_strategies=st,
                                  lock_job=args.lock_job or None,
                                  restart=args.restart,
                                  checkpoint_every=args.checkpoint_every)
    else:
        {"wf-refresh": jobs.refresh_wf_scores,
         "backtest-cache": jobs._refresh_backtest_cache,
         "roller": jobs.run_backtest_roller}[args.job]()
    return 0


if __name__ == "__main__":
    sys.exit(main())
