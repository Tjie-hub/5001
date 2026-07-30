#!/usr/bin/env python3
"""Phase 5 GO/NO-GO tracker (spec 2026-07-08). Research reads the production
ledger (the architecture's allowed direction) and reports realized NR7
performance against the PRE-REGISTERED rule. The rule is frozen — do not edit
after trades accumulate."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from data.db import connect as db_connect
from config import DB_PATH

RULE = {'min_n': 15, 'go_exp': 0.50, 'nogo_exp': 0.0,
        'extend_n': 10, 'timebox_months': 6, 'start_date': '2026-07-08'}
BACKTEST_REF = {'exp_net_pct': 1.18, 'n': 346, 'win_pct': 54.0}


def verdict(n: int, exp: float) -> str:
    if n < RULE['min_n']:
        return 'INSUFFICIENT'
    if exp >= RULE['go_exp']:
        return 'GO'
    if exp <= RULE['nogo_exp']:
        return 'NO-GO'
    return 'EXTEND'


def run():
    conn = db_connect(DB_PATH)
    rows = conn.execute(
        "SELECT pnl_pct, exit_reason FROM paper_trades "
        "WHERE strategy='NR7 Breakout' AND status='CLOSED'").fetchall()
    conn.close()
    n = len(rows)
    exp = sum(r[0] for r in rows) / n if n else 0.0
    wins = sum(1 for r in rows if r[0] > 0)
    print(f"PHASE 5 — NR7 live ledger (start {RULE['start_date']})")
    if n:
        print(f"closed trades: {n} | realized net exp: {exp:+.2f}%/trade | "
              f"win: {100 * wins / n:.0f}%")
    else:
        print("closed trades: 0 — waiting for BULL regimes")
    print(f"backtest ref: {BACKTEST_REF['exp_net_pct']:+.2f}% "
          f"(N={BACKTEST_REF['n']}, win {BACKTEST_REF['win_pct']:.0f}%)")
    print(f"rule: N>={RULE['min_n']}, GO>=+{RULE['go_exp']}%, "
          f"NO-GO<={RULE['nogo_exp']}%, timebox {RULE['timebox_months']}mo")
    print(f"VERDICT: {verdict(n, exp)}")


if __name__ == '__main__':
    run()
