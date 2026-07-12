"""Phase D CLI: build/persist a strategy's regime profile, or query the latest.

Usage:
  DB_PATH=<db> python -m research.regime.cli build  nr7_breakout
  DB_PATH=<db> python -m research.regime.cli query  nr7_breakout
"""
from __future__ import annotations

import sys

from data.db import connect as db_connect
from research.regime.config import load_config
from research.regime.profile import build_profile
from research.regime.storage import (ensure_profile_tables, persist_profile,
                                      load_latest_profile)


def _build(strategy_fn: str) -> None:
    from research.regime.collect import collect_tagged_trades, corpus_fingerprint
    cfg = load_config()
    with db_connect() as conn:
        ensure_profile_tables(conn)
        trades = collect_tagged_trades(conn, strategy_fn, cfg)
        fp = corpus_fingerprint(trades)
        prof = build_profile(strategy_fn, trades, cfg, corpus_fingerprint=fp)
        pid = persist_profile(conn, prof)
    print(f"persisted profile {pid} for {strategy_fn}")
    for c in prof["cells"]:
        print(f"  {c['regime']:9} {c['verdict']:9} n={c['n_trades']:4} "
              f"CI[{c['ci_low']:+.3f},{c['ci_high']:+.3f}] "
              f"vol_decl={c['vol_axis_declared']} liq_decl={c['liq_axis_declared']}")


def _query(strategy_fn: str) -> None:
    with db_connect() as conn:
        ensure_profile_tables(conn)
        prof = load_latest_profile(conn, strategy_fn)
    if prof is None:
        print(f"no profile for {strategy_fn}")
        return
    print(f"profile {prof['profile_id']} ({prof['created_at']})")
    for regime, c in prof["cells"].items():
        print(f"  {regime:9} {c['verdict']:9} n={c['n_trades']}")


def main(argv=None) -> int:
    argv = argv or sys.argv[1:]
    if len(argv) != 2 or argv[0] not in ("build", "query"):
        print(__doc__)
        return 2
    (_build if argv[0] == "build" else _query)(argv[1])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
