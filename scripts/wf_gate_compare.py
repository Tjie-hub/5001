"""Phase 2.3 — regime-gated allocation replay vs ungated baseline.

Replays the stored per-window metrics in backtest_windows under the
Daniel-Moskowitz panic gate: for each test window, determine the macro state
at the window's start (IHSG below 200-day MA AND 20-day realized vol above
the 75th percentile of the trailing year). In panic state the momentum
family contributes nothing (entries blocked); the counter-trend book always
contributes. Compares average per-traded-window return, gated vs ungated.

Acceptance: momentum family is OFF for windows starting Jan-Jun 2026, and
the gated book beats the ungated book on average return.

Usage: venv/bin/python scripts/wf_gate_compare.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import sqlite3
import statistics as st
from collections import defaultdict

import pandas as pd

from config import DB_PATH

MOMENTUM_FAMILY = {
    'momentum', 'Trend Following Breakout', 'Inside Bar Breakout',
    'NR7 Breakout', 'ORB', 'Swing Trend', 'conservative',
}
COUNTER_TREND = {'Crash Recovery', 'Panic Rebound'}


def build_panic_calendar(conn) -> pd.Series:
    """Daily panic-state flag for IHSG, computed point-in-time (no look-ahead:
    each day uses only data up to that day)."""
    df = pd.read_sql(
        "SELECT date, close FROM ohlcv WHERE ticker='IHSG' ORDER BY date", conn)
    closes = df['close'].astype(float)
    ma200 = closes.rolling(200).mean()
    rets = closes.pct_change()
    vol20 = rets.rolling(20).std()
    # 75th percentile of trailing 252-day vol, expanding-safe
    vol_p75 = vol20.rolling(252, min_periods=60).quantile(0.75)
    panic = (closes < ma200) & (vol20 > vol_p75)
    return pd.Series(panic.values, index=df['date'].values)


def main():
    conn = sqlite3.connect(DB_PATH)
    panic_cal = build_panic_calendar(conn)
    panic_dates = panic_cal[panic_cal].index
    cal_dates = list(panic_cal.index)

    def panic_fraction(start: str, end: str) -> float:
        """Fraction of trading days in [start, end] that were panic-state.
        The live gate flips daily, so a window straddling a regime break
        (e.g. windows starting early Jan-2026, crash on Jan 28) is partially
        gated — tagging by window start alone misses exactly the bleeding
        the gate exists to stop."""
        days = [d for d in cal_dates if start <= d <= end]
        if not days:
            return 0.0
        return sum(1 for d in days if bool(panic_cal[d])) / len(days)

    rows = conn.execute(
        "SELECT test_start, test_end, metrics_json FROM backtest_windows "
        "WHERE metrics_json IS NOT NULL").fetchall()
    conn.close()

    spans = sorted({(ts, te) for ts, te, _ in rows})
    frac_by_span = {(ts, te): panic_fraction(ts, te) for ts, te in spans}

    ungated, gated = [], []
    frac_by_q = defaultdict(list)

    for ts, te, mj in rows:
        try:
            d = json.loads(mj)
        except Exception:
            continue
        frac = frac_by_span[(ts, te)]
        frac_by_q[ts[:7]].append(frac)
        for strat, m in d.items():
            if not isinstance(m, dict):
                continue
            r = m.get('return', 0) or 0
            traded = (r != 0 or (m.get('win_rate', 0) or 0) != 0
                      or (m.get('profit_factor', 0) or 0) != 0)
            if not traded:
                continue
            ungated.append(r)
            if strat in MOMENTUM_FAMILY:
                # Daily gate blocks entries on panic days: the window's
                # contribution shrinks by the panic-day fraction.
                gated.append(r * (1.0 - frac))
            else:
                gated.append(r)

    print(f"IHSG panic-state days in calendar: {len(panic_dates)}")
    print("\navg panic-day fraction by window-start month:")
    for q in sorted(frac_by_q):
        f = st.mean(frac_by_q[q])
        state = 'OFF' if f > 0.66 else ('partial' if f > 0.05 else 'on')
        print(f"  {q}: panic_frac={f:5.2f}  momentum={state}")

    print(f"\n{'book':10} {'n':>6} {'avg':>7} {'med':>7} {'pos%':>6}")
    for name, rets in (('ungated', ungated), ('gated', gated)):
        pos = 100 * sum(1 for r in rets if r > 0) / len(rets)
        print(f"{name:10} {len(rets):6d} {st.mean(rets):7.3f} "
              f"{st.median(rets):7.3f} {pos:6.1f}")

    improved = st.mean(gated) > st.mean(ungated)
    print(f"\nacceptance: gated beats ungated on avg return — "
          f"{'PASS' if improved else 'FAIL'} "
          f"({st.mean(gated):.3f}% vs {st.mean(ungated):.3f}%)")


if __name__ == '__main__':
    main()
