"""
TFB exit-aware re-run — the decisive test from docs/review.md.

THE QUESTION
------------
A starvation test found TFB's 6 gates appear to select LOSERS: of 94 raw
Donchian-20 breakouts, the 25 that PASSED the gates averaged -8.0% while the
69 BLOCKED ones averaged +1.1% (naive +5-day hold). That contradicts the WF
out-of-sample record, which says the gates lifted avg P&L/trade +0.95%->+4.63%.

The contradiction is almost certainly a MEASUREMENT artifact: a naive fixed-
horizon hold is the wrong yardstick for a stop-managed breakout (it lets
stopped-out losers bleed to -9.7% instead of exiting at the trail). This
script settles it by scoring the SAME cohort with the strategy's ACTUAL exit
logic.

WHAT IT DOES
------------
For each raw breakout signal bar (close > prior 20-bar high) across a universe
over a trailing window:
  1. Compute the 6 TFB gates (breakout / volume>1.8x / atr-expansion /
     regime close>MA50 / ma20_slope>0.5 / no-climax volume<4x).
  2. Split into GATED (all 6 hold) vs BLOCKED (breakout holds, >=1 gate fails).
  3. Score EVERY signal three ways:
       - naive +5d forward return  (reproduces the starvation table)
       - naive +10d / +20d         (right-skew sanity check)
       - REAL EXIT                 (the strategy's actual path: entry at next
                                    open, ATR trailing stop ratcheting up,
                                    MA20-break exit, apply_costs on both sides)
  4. Print Blocked-vs-Gated under naive-hold vs real-exit, side by side.

DECISION RULE
-------------
If GATED beats BLOCKED under real exits (and gated avg > 0), the WF result
holds -> KEEP the gates; the starvation finding was a metric artifact.
If GATED still underperforms BLOCKED under real exits, the gates are genuinely
inverted -> investigate the volume (46%) and slope (39%) thresholds.

Faithfulness: every indicator and cost matches engine/strategies.py
`strategy_trend_following_breakout` exactly — calc_atr, calc_ma_slope, and
apply_costs (0.25% buy / 0.35% sell) are imported from the engine, not
reimplemented.

Usage:
    venv/bin/python scripts/tfb_exit_aware_rerun.py
    venv/bin/python scripts/tfb_exit_aware_rerun.py --universe idx80 --window 120
"""
import sys
import os
import argparse
import sqlite3
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np

from config import DB_PATH
from engine.indicators import calc_atr, calc_ma_slope   # exact fns the strategy uses
from engine.strategies import apply_costs               # exact cost model

STRATEGY = 'Trend Following Breakout'
MIN_BARS = 65          # strategy needs MA50 + 60-bar ATR median + 5-bar slope

UNIVERSE_FLAGS = {'idx30': 'in_idx30', 'lq45': 'in_lq45', 'idx80': 'in_idx80'}


# ─────────────────────────────────────────────────────────────────────────────
# Universe + data
# ─────────────────────────────────────────────────────────────────────────────
def load_universe(name):
    flag = UNIVERSE_FLAGS[name]
    conn = sqlite3.connect(DB_PATH)
    tickers = [r[0] for r in conn.execute(
        f"SELECT ticker FROM idx_tickers WHERE {flag}=1 ORDER BY ticker").fetchall()]
    conn.close()
    return tickers


def load_ohlcv(ticker):
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql(
        "SELECT date, open, high, low, close, volume FROM ohlcv "
        "WHERE ticker=? ORDER BY date ASC", conn, params=(ticker,))
    conn.close()
    df['date'] = pd.to_datetime(df['date'])
    for c in ('open', 'high', 'low', 'close', 'volume'):
        df[c] = pd.to_numeric(df[c], errors='coerce')
    return df.dropna(subset=['open', 'high', 'low', 'close', 'volume']).reset_index(drop=True)


# ─────────────────────────────────────────────────────────────────────────────
# Indicators + gates — computed identically to strategy_trend_following_breakout
# ─────────────────────────────────────────────────────────────────────────────
def compute_indicators(df):
    return dict(
        close=df['close'], high=df['high'], low=df['low'], volume=df['volume'],
        ma20=df['close'].rolling(20).mean(),
        ma50=df['close'].rolling(50).mean(),
        atr=calc_atr(df, 14),
        avg_vol=df['volume'].rolling(20).mean(),
        donchian20=df['high'].rolling(20).max().shift(1),    # prior 20-bar high
        atr60_med=calc_atr(df, 14).rolling(60).median(),
        ma20_slope=calc_ma_slope(df, 20, 5),                 # % rise of MA20 over 5 bars
        vol_ratio=df['volume'] / df['volume'].rolling(20).mean(),
    )


def _b(x):
    """NaN-safe bool: NaN comparisons must be False, as pandas does in the strategy."""
    return bool(x) and not pd.isna(x)


def gate_flags(ind, i):
    """The 6 boolean gate conditions at bar i (mirrors the strategy's `signal`)."""
    return {
        'breakout':  _b(ind['close'].iloc[i] > ind['donchian20'].iloc[i]),
        'volume':    _b(ind['volume'].iloc[i] > 1.8 * ind['avg_vol'].iloc[i]),
        'atr_exp':   _b(ind['atr'].iloc[i] > 0.5 * ind['atr60_med'].iloc[i]),
        'regime':    _b(ind['close'].iloc[i] > ind['ma50'].iloc[i]),
        'slope':     _b(ind['ma20_slope'].iloc[i] > 0.5),
        'no_climax': _b(ind['vol_ratio'].iloc[i] < 4.0),
    }


# ─────────────────────────────────────────────────────────────────────────────
# The actual exit logic — single-signal form of the strategy's trade loop
# ─────────────────────────────────────────────────────────────────────────────
def simulate_real_exit(df, ind, sig_i, atr_mult=2.5, use_ma20=True):
    """Trade ONE signal with the strategy's real exits.

    Entry: next bar's open (sig_i+1), costs applied (matches strategy).
    SL distance: atr_mult x ATR at the SIGNAL bar (shipped value = 2.5).
    Trailing stop: max(prev_stop, close[j] - atr_mult*ATR[j]) — ratchets up only.
    Exit: low <= trail (TRAIL_SL) | close < MA20 (MA20_BREAK, if use_ma20) |
          end of data (CLIPPED).

    atr_mult / use_ma20 parameterize the exit for trailing-stop tuning; the
    defaults reproduce the shipped strategy exactly.

    Each signal is traded INDEPENDENTLY (overlaps allowed) — that is the right
    frame for 'do the gates pick winners per-signal', which is what the
    starvation test measured. The live strategy skips overlapping re-entries,
    but per-signal quality is unaffected by that portfolio rule.

    Returns (pnl_pct, exit_reason, bars_held) or (None, 'NO_FWD', 0) if the
    signal is too close to the end of data to evaluate.
    """
    n = len(df)
    entry_i = sig_i + 1
    if entry_i >= n:
        return None, 'NO_FWD', 0

    sig_atr = ind['atr'].iloc[sig_i]
    if pd.isna(sig_atr) or sig_atr <= 0:
        return None, 'BAD_ATR', 0

    entry_price = apply_costs(df['open'].iloc[entry_i], 'BUY')
    sl_dist = atr_mult * sig_atr
    trail_stop = entry_price - sl_dist

    exit_price, exit_reason, j = None, None, entry_i
    last_j = n - 1
    for j in range(entry_i, n):
        hi = ind['high'].iloc[j]
        lo = ind['low'].iloc[j]
        cl = ind['close'].iloc[j]
        cur_atr = ind['atr'].iloc[j]
        cur_ma20 = ind['ma20'].iloc[j]

        new_stop = cl - atr_mult * cur_atr if not pd.isna(cur_atr) else trail_stop
        if new_stop > trail_stop:
            trail_stop = new_stop

        if lo <= trail_stop:
            exit_price, exit_reason = apply_costs(trail_stop, 'SELL'), 'TRAIL_SL'
            break
        if use_ma20 and (not pd.isna(cur_ma20)) and cl < cur_ma20:
            exit_price, exit_reason = apply_costs(cl, 'SELL'), 'MA20_BREAK'
            break
        if j == last_j:
            exit_price, exit_reason = apply_costs(cl, 'SELL'), 'CLIPPED'
            break

    pnl_pct = (exit_price - entry_price) / entry_price * 100.0
    bars_held = j - entry_i + 1
    return pnl_pct, exit_reason, bars_held


def naive_fwd(df, sig_i, days):
    """Naive forward return: entry at next open, exit at close `days` bars later."""
    n = len(df)
    entry_i = sig_i + 1
    exit_i = sig_i + days          # `days` bars after the signal bar
    if exit_i >= n:
        return None
    entry = df['open'].iloc[entry_i]
    exitp = df['close'].iloc[exit_i]
    return (exitp - entry) / entry * 100.0


# ─────────────────────────────────────────────────────────────────────────────
# Cohort stats
# ─────────────────────────────────────────────────────────────────────────────
GATE_NAMES = ['breakout', 'volume', 'atr_exp', 'regime', 'slope', 'no_climax']
CONTEXT_GATES = ['volume', 'atr_exp', 'regime', 'slope', 'no_climax']


def stats(values):
    values = [v for v in values if v is not None and not np.isnan(v)]
    if not values:
        return dict(n=0, avg=np.nan, med=np.nan, pos=np.nan,
                    strong=np.nan, severe=np.nan, pf=np.nan)
    arr = np.array(values)
    wins = arr[arr > 0].sum()
    loss = abs(arr[arr < 0].sum())
    pf = wins / loss if loss > 0 else np.inf
    return dict(
        n=len(arr),
        avg=arr.mean(),
        med=np.median(arr),
        pos=100.0 * (arr > 0).mean(),
        strong=100.0 * (arr > 5).mean(),
        severe=100.0 * (arr < -5).mean(),
        pf=pf,
    )


def fmt_row(label, s):
    if s['n'] == 0:
        return f"{label:18} {s['n']:>5}   (no signals)"
    return (f"{label:18} {s['n']:>5} {s['avg']:>7.2f} {s['med']:>7.2f} "
            f"{s['pos']:>6.1f} {s['strong']:>7.1f} {s['severe']:>7.1f}")


# ─────────────────────────────────────────────────────────────────────────────
# Trailing-stop + MA20-exit tuning sweep
# ─────────────────────────────────────────────────────────────────────────────
def run_tune(args):
    """Sweep ATR trailing-stop multiplier x MA20-exit on/off over the cohort.

    Scores the GATED cohort (what the live strategy actually trades) under real
    exits for each config, plus blocked avg as a reference. The shipped strategy
    is mult=2.5 / MA20=on. Goal: see if loosening the exit recovers positive
    real-exit P&L (the ~4.7pt drag the decisive run flagged).
    """
    tickers = load_universe(args.universe)
    W, MIN_FWD = args.window, args.min_fwd
    print(f"=== TFB trailing-stop + MA20-exit TUNE ===")
    print(f"universe={args.universe} ({len(tickers)} tickers)  window={W} bars  "
          f"min_fwd={MIN_FWD}\n")

    # Collect raw breakout signals once; reuse df/ind across configs.
    sigs = []  # (df, ind, sig_i, gated)
    checks = 0
    for tk in tickers:
        df = load_ohlcv(tk)
        if len(df) < MIN_BARS + MIN_FWD:
            continue
        ind = compute_indicators(df)
        n = len(df)
        first_sig = max(MIN_BARS, n - W - MIN_FWD)
        last_sig = n - 1 - MIN_FWD
        for s in range(first_sig, last_sig + 1):
            checks += 1
            gf = gate_flags(ind, s)
            if not gf['breakout']:
                continue
            sigs.append((df, ind, s, all(gf[g] for g in GATE_NAMES)))

    n_raw = len(sigs)
    n_gated = sum(1 for _, _, _, g in sigs if g)
    if n_raw == 0:
        print("No raw breakout signals in window.")
        return
    print(f"raw breakouts: {n_raw}   gated: {n_gated}   blocked: {n_raw - n_gated}"
          f"   ({checks} checks)\n")

    MULTS = [1.5, 2.0, 2.5, 3.0, 3.5, 4.0]
    configs = [(m, ma) for m in MULTS for ma in (True, False)]

    print("GATED cohort real-exit P&L by exit config  (blocked avg shown for reference):")
    print(f"{'mult':>5} {'ma20':>5} {'n':>5} {'avg':>7} {'med':>7} {'pos%':>6} "
          f"{'PF':>6} {'trail%':>7} {'blk_avg':>8}")
    rows = []
    best = None
    for m, ma in configs:
        pnls_g, reasons, pnls_b = [], [], []
        for df, ind, s, gated in sigs:
            p, r, _ = simulate_real_exit(df, ind, s, atr_mult=m, use_ma20=ma)
            if p is None or r == 'CLIPPED':
                continue
            (pnls_g if gated else pnls_b).append(p)
            if gated:
                reasons.append(r)
        gs = stats(pnls_g)
        trail_frac = 100.0 * sum(1 for r in reasons if r == 'TRAIL_SL') / max(len(reasons), 1)
        blk_avg = stats(pnls_b)['avg']
        mark = '  <- shipped' if (abs(m - 2.5) < 1e-9 and ma) else ''
        if gs['n']:
            print(f"{m:>5.1f} {('on' if ma else 'off'):>5} {gs['n']:>5} {gs['avg']:>+7.2f} "
                  f"{gs['med']:>+7.2f} {gs['pos']:>6.1f} {gs['pf']:>6.2f} {trail_frac:>7.1f} "
                  f"{blk_avg:>+8.2f}{mark}")
        else:
            print(f"{m:>5.1f} {('on' if ma else 'off'):>5} {gs['n']:>5}  (no closed trades){mark}")
        rows.append((m, ma, gs, blk_avg))
        if gs['n'] > 0 and (best is None or gs['avg'] > best[2]['avg']):
            best = (m, ma, gs, blk_avg)

    print()
    shipped = next(r for r in rows if abs(r[0] - 2.5) < 1e-9 and r[1])
    s_avg = shipped[2]['avg']
    print(f"shipped  (2.5 / ma20 on): gated avg {s_avg:+.2f}%  med {shipped[2]['med']:+.2f}%  "
          f"PF {shipped[2]['pf']:.2f}")
    if best and best[0:2] != (2.5, True):
        b_avg = best[2]['avg']
        print(f"best avg ({best[0]} / ma20 {'on' if best[1] else 'off'}): "
              f"gated avg {b_avg:+.2f}%  med {best[2]['med']:+.2f}%  PF {best[2]['pf']:.2f}  "
              f"(vs blocked {best[3]:+.2f}%)")
        if best[2]['avg'] > 0:
            print(f"=> a looser exit turns gated real-exit avg POSITIVE "
                  f"({s_avg:+.2f} -> {b_avg:+.2f}%). Candidate to ship.")
        else:
            print(f"=> looser exit helps ({s_avg:+.2f} -> {b_avg:+.2f}%) but still negative; "
                  f"this window/regime is just weak for breakouts — confirm on full WF history.")
    else:
        print("=> shipped 2.5/ma20-on is already the best avg; the trail isn't the lever here.")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--universe', default='lq45', choices=list(UNIVERSE_FLAGS))
    ap.add_argument('--window', type=int, default=86,
                    help='trailing signal-window length in bars (starvation test used 86)')
    ap.add_argument('--min-fwd', type=int, default=25,
                    help='forward bars required after entry so exits are real, not clipped')
    ap.add_argument('--tune', action='store_true',
                    help='sweep ATR trailing-stop multiplier x MA20-exit on/off over the cohort')
    args = ap.parse_args()

    if args.tune:
        run_tune(args)
        return

    tickers = load_universe(args.universe)
    W, MIN_FWD = args.window, args.min_fwd

    print(f"=== TFB exit-aware re-run ===")
    print(f"universe={args.universe} ({len(tickers)} tickers)  window={W} bars  "
          f"min_fwd={MIN_FWD}\n")

    # Per-signal records
    recs = []  # each: dict(ticker, date, gated, gates, pnl_real, reason, bars, fwd5/10/20)
    gate_fail = defaultdict(int)
    checks = 0

    for tk in tickers:
        df = load_ohlcv(tk)
        if len(df) < MIN_BARS + MIN_FWD:
            continue
        ind = compute_indicators(df)
        n = len(df)
        # signal bars: need >=MIN_BARS of history and >=MIN_FWD bars after entry
        first_sig = max(MIN_BARS, n - W - MIN_FWD)
        last_sig = n - 1 - MIN_FWD     # entry_i = sig+1 <= n-1-MIN_FWD => exits are real
        for s in range(first_sig, last_sig + 1):
            checks += 1
            gf = gate_flags(ind, s)
            if not gf['breakout']:
                continue                # not a raw signal
            pnl_real, reason, bars = simulate_real_exit(df, ind, s)
            rec = dict(
                ticker=tk, date=str(df['date'].iloc[s])[:10],
                gated=all(gf[g] for g in GATE_NAMES),
                gates=gf,
                pnl_real=pnl_real, reason=reason, bars=bars,
                fwd5=naive_fwd(df, s, 5),
                fwd10=naive_fwd(df, s, 10),
                fwd20=naive_fwd(df, s, 20),
            )
            recs.append(rec)
            if not rec['gated']:
                for g in CONTEXT_GATES:
                    if not gf[g]:
                        gate_fail[g] += 1

    raw = len(recs)
    if raw == 0:
        print("No raw breakout signals found in window. widen --window or --universe.")
        return

    gated = [r for r in recs if r['gated']]
    blocked = [r for r in recs if not r['gated']]
    print(f"raw breakout signals: {raw}  ({100.0*raw/max(checks,1):.1f}% of {checks} checks)")
    print(f"gated (all 6 gates):  {len(gated)}  ({100.0*len(gated)/raw:.0f}% pass)")
    print(f"blocked (>=1 fail):   {len(blocked)}")
    if blocked:
        tot = len(blocked)
        print("blocked gate-failure breakdown: "
              + ", ".join(f"{g} {100.0*gate_fail[g]/tot:.0f}%" for g in CONTEXT_GATES))

    # Clip / data-quality report on real exits
    no_real = [r for r in recs if r['pnl_real'] is None]
    clipped = [r for r in recs if r['reason'] == 'CLIPPED']
    print(f"\nreal-exit data quality: {len(no_real)} unusable (no fwd/bad ATR), "
          f"{len(clipped)} still-open at end-of-data (excluded from real-exit stats)")

    def cohort(arr, key):
        return [r[key] for r in arr if r[key] is not None]

    hdr = f"{'cohort':18} {'n':>5} {'avg':>7} {'med':>7} {'pos%':>6} {'>+5%':>7} {'<-5%':>7}"

    print("\n--- NAIVE FIXED-HORIZON HOLD (the starvation test's yardstick) ---")
    print(f"{'(avg/median % return, %-profitable, %strong>+5, %severe<-5)':^70}")
    print(hdr)
    for label, key in [('+5d', 'fwd5'), ('+10d', 'fwd10'), ('+20d', 'fwd20')]:
        print(f"  [{label}] BLOCKED")
        print("    " + fmt_row('blocked', stats(cohort(blocked, key))))
        print(f"  [{label}] GATED")
        print("    " + fmt_row('gated', stats(cohort(gated, key))))

    print("\n--- REAL EXIT (strategy's actual stop/target/time-stop path) ---")
    print(hdr)
    # Exclude clipped (still-open) trades from real-exit stats — outcome unknown.
    blk_real = [r['pnl_real'] for r in blocked if r['pnl_real'] is not None and r['reason'] != 'CLIPPED']
    gat_real = [r['pnl_real'] for r in gated   if r['pnl_real'] is not None and r['reason'] != 'CLIPPED']
    print("  " + fmt_row('blocked', stats(blk_real)))
    print("  " + fmt_row('gated', stats(gat_real)))

    # Exit-reason breakdown
    print("\nreal-exit reason mix:")
    for label, arr in [('blocked', blocked), ('gated', gated)]:
        cnt = defaultdict(int)
        for r in arr:
            cnt[r['reason'] or 'NONE'] += 1
        mix = ", ".join(f"{k}={v}" for k, v in sorted(cnt.items(), key=lambda x: -x[1]))
        print(f"  {label:8} {mix}")

    # ── DECISIVE VERDICT ────────────────────────────────────────────────────
    print("\n" + "=" * 72)
    print("VERDICT")
    print("=" * 72)
    bs, gs = stats(blk_real), stats(gat_real)
    if gs['n'] == 0 or bs['n'] == 0:
        print("insufficient real-exit sample for a verdict.")
        return
    naive_gap = stats(cohort(gated, 'fwd5'))['avg'] - stats(cohort(blocked, 'fwd5'))['avg']
    real_gap = gs['avg'] - bs['avg']
    print(f"naive +5d : gated {stats(cohort(gated,'fwd5'))['avg']:+.2f}%  "
          f"vs blocked {stats(cohort(blocked,'fwd5'))['avg']:+.2f}%  "
          f"(gap {naive_gap:+.2f})  <- starvation test's view")
    print(f"real exit : gated {gs['avg']:+.2f}%  vs blocked {bs['avg']:+.2f}%  "
          f"(gap {real_gap:+.2f})  <- strategy's actual exits")

    if real_gap > 0 and gs['avg'] > 0:
        print("\n=> KEEP THE GATES. Under real exits gated beats blocked and is profitable.")
        print("   The starvation test's 'gates pick losers' was a naive-hold artifact.")
        print("   WF result (+4.63%/trade) is corroborated.")
    elif real_gap > 0:
        print("\n=> GATES HELP DIRECTIONALLY (gated > blocked) but gated still loses money")
        print("   on average. Keep them, but the strategy itself needs work (portfolio layer).")
    else:
        print("\n=> GATES INVERTED. Gated underperforms blocked even under real exits.")
        print("   Investigate the volume + slope thresholds before trusting them live.")
    print("=" * 72)


if __name__ == '__main__':
    main()
