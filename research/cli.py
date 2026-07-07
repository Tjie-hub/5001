#!/usr/bin/env python3
"""Research CLI (spec §10-M3): the batch jobs that used to run on the
production scheduler. Cron-able; never imported by production.

Usage:
  python -m research.cli wf-refresh      # walk-forward scores + wf_edge (was Fri 16:00)
  python -m research.cli backtest-cache  # dashboard/quality-gate cache (was daily 08:30)
  python -m research.cli roller          # monthly window roller (was Sun 10:00)
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main(argv=None):
    p = argparse.ArgumentParser(prog="research.cli")
    p.add_argument("job", choices=["wf-refresh", "backtest-cache", "roller"])
    args = p.parse_args(argv)
    from research import jobs
    {"wf-refresh": jobs.refresh_wf_scores,
     "backtest-cache": jobs._refresh_backtest_cache,
     "roller": jobs.run_backtest_roller}[args.job]()
    return 0


if __name__ == "__main__":
    sys.exit(main())
