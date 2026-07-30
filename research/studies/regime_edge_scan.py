#!/usr/bin/env python3
"""Regime-conditional edge scan (audit Phase 4, second increment).

Runs every roster strategy through walk-forward across the liquid universe,
labels each OOS trade's entry regime, and classifies each (strategy, regime)
cell CONFIRMED / PROMISING / REJECTED against pre-registered thresholds. Reuses
research.nr7_study for all statistics. Read-only w.r.t. production.
"""
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pandas as pd

from data.db import connect as db_connect
from engine.liquidity import get_adv_value_30d, VALUE_LIQ_MIN_IDR
from research.walkforward_multi import STRATEGY_FUNCS, walk_forward_split
from engine.regime_filter import detect_regime
from engine.exits.costs import COMMISSION_SELL, SLIPPAGE
import research.nr7_study as ns
from config import DB_PATH

RESULTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       'docs', 'superpowers', 'results',
                       '2026-07-07-regime-edge-scan.md')

WARMUP_BARS = 60                       # matches run_walk_forward (wf_edge parity)
_SELL_ADJ = 1.0 - COMMISSION_SELL - SLIPPAGE
T2_MIN_N = 60                          # cell-scaled late-CV sample floor
_VWMA_NAME = 'VWMA Breakout Pullback'  # the one no-`filters` strategy

# Memoize regime per (ticker, entry_date) — many strategies enter on the same
# bars, so this avoids recomputing detect_regime (ADX on 250 rows) 14x per date.
_REGIME_CACHE = {}


def _regime_at(full_df: pd.DataFrame, ticker: str, entry_date: str) -> str:
    key = (ticker, entry_date)
    if key in _REGIME_CACHE:
        return _REGIME_CACHE[key]
    hist = full_df[full_df['date'] <= entry_date].tail(250)
    reg = 'SIDEWAYS' if len(hist) < 30 else detect_regime(hist.reset_index(drop=True))
    _REGIME_CACHE[key] = reg
    return reg


def collect_trades_for_strategy(strategy_fn, name: str, ticker: str,
                                df: pd.DataFrame) -> list:
    """OOS trades for one (strategy, ticker) as study-trade dicts.

    Mirrors run_walk_forward: 60-bar warmup tail per test window, drop trades
    entered before test_start. Recovers raw_exit by inverting the strategy's
    SELL-leg cost so nr7_study applies full round-trip costs from raw prices."""
    df = df.sort_values('date').reset_index(drop=True)
    out = []
    for w in walk_forward_split(df, train_months=12, test_months=3):
        train_df, test_df, test_start = w['train'], w['test'], w['test_start']
        if len(test_df) < 25:
            continue
        warmup = train_df.tail(WARMUP_BARS) if len(train_df) >= WARMUP_BARS else train_df
        extended = pd.concat([warmup, test_df], ignore_index=True)
        if name == _VWMA_NAME:
            res = strategy_fn(extended)          # takes no filters kwarg
        else:
            res = strategy_fn(extended, filters=None)
        for tr in res.get('trades', []):
            entry = str(tr.entry_date)[:10]
            if entry < test_start:
                continue
            out.append({
                'strategy': name,
                'ticker': ticker,
                'entry_date': entry,
                'raw_entry': float(tr.entry_price),
                'raw_exit': float(tr.exit_price) / _SELL_ADJ,
                'regime': _regime_at(df, ticker, entry),
            })
    return out


def classify_cell(cell_trades, boundary: str) -> dict:
    """Classify one (strategy, regime) cell → CONFIRMED / PROMISING / REJECTED.

    Regime bar: cell pooled exp >= 0.50% net and N >= 100.
    CV: early-positive tickers' late pooled exp, retention vs their early exp.
    """
    me = ns.THRESHOLDS['min_net_exp']
    cell_pool = ns.pool(cell_trades)
    regime_pass = cell_pool['exp_pct'] >= me and cell_pool['n'] >= ns.THRESHOLDS['t3_min_n']

    early, late = ns.cv_split(cell_trades, boundary)
    picked = ns.select_positive_tickers(early, ns.THRESHOLDS['t2_select_min'])
    late_sel = [t for t in late if t['ticker'] in picked]
    early_sel = [t for t in early if t['ticker'] in picked]
    late_pool, early_pool = ns.pool(late_sel), ns.pool(early_sel)
    retention = (late_pool['exp_pct'] / early_pool['exp_pct']
                 if early_pool['exp_pct'] > 0 else 0.0)

    persistent = (retention >= ns.THRESHOLDS['t2_min_retention']
                  and late_pool['exp_pct'] > 0)
    if not regime_pass:
        state = 'REJECTED'
    elif persistent and late_pool['exp_pct'] >= me and late_pool['n'] >= T2_MIN_N:
        state = 'CONFIRMED'
    elif persistent:
        state = 'PROMISING'
    else:
        state = 'REJECTED'

    return {
        'state': state, 'regime_pass': regime_pass,
        'exp_pct': cell_pool['exp_pct'], 'n': cell_pool['n'],
        'win_rate': cell_pool['win_rate'],
        'late_exp': late_pool['exp_pct'], 'late_n': late_pool['n'],
        'early_exp': early_pool['exp_pct'], 'retention': retention,
    }


def build_matrix(strategies: dict, dfs: dict) -> dict:
    """strategies={name: fn}, dfs={ticker: df} → {strategy: {regime: cell}}.

    Collects all trades, computes the global median-date CV boundary once, and
    classifies every observed (strategy, regime) cell."""
    all_trades = []
    for name, fn in strategies.items():
        for ticker, df in dfs.items():
            if len(df) < 300:
                continue
            all_trades.extend(collect_trades_for_strategy(fn, name, ticker, df))

    dates = sorted(t['entry_date'] for t in all_trades)
    boundary = dates[len(dates) // 2] if dates else '2099-01-01'

    matrix = {}
    for name in strategies:
        strat_trades = [t for t in all_trades if t['strategy'] == name]
        by_regime = {}
        for regime in ('BULL', 'SIDEWAYS', 'BEAR'):
            cell = [t for t in strat_trades if t['regime'] == regime]
            if cell:
                by_regime[regime] = classify_cell(cell, boundary)
        matrix[name] = by_regime
    return matrix


def _load_liquid_dfs(conn, as_of):
    tickers = [r[0] for r in conn.execute(
        "SELECT DISTINCT ticker FROM ohlcv WHERE ticker != 'IHSG'")]
    dfs = {}
    for t in tickers:
        adv = get_adv_value_30d(conn, t, as_of)
        if adv is None or adv < VALUE_LIQ_MIN_IDR:
            continue
        df = pd.read_sql("SELECT date, open, high, low, close, volume FROM ohlcv "
                         "WHERE ticker=? ORDER BY date", conn, params=(t,))
        if len(df) >= 300:
            dfs[t] = df
    return dfs


def run():
    conn = db_connect(DB_PATH)
    as_of = conn.execute("SELECT MAX(date) FROM ohlcv").fetchone()[0]
    dfs = _load_liquid_dfs(conn, as_of)
    conn.close()
    matrix = build_matrix(STRATEGY_FUNCS, dfs)
    _write_results(as_of, len(dfs), matrix)
    confirmed = [(s, r) for s, rr in matrix.items() for r, c in rr.items()
                 if c['state'] == 'CONFIRMED']
    promising = [(s, r) for s, rr in matrix.items() for r, c in rr.items()
                 if c['state'] == 'PROMISING']
    print(f"CONFIRMED: {confirmed or 'none'}")
    print(f"PROMISING: {promising or 'none'}")
    return matrix


def _write_results(as_of, n_universe, matrix):
    os.makedirs(os.path.dirname(RESULTS), exist_ok=True)
    L = ["# Regime-Conditional Edge Scan — Results", "",
         f"Run: {datetime.now().isoformat(timespec='seconds')} | corpus as-of {as_of} | "
         f"liquid universe {n_universe} tickers | bar +0.50% net, N>=100 (T3), "
         f"late N>=60 (CV)", "",
         "## Matrix — pooled net expectancy per (strategy, regime)", "",
         "| strategy | BULL | SIDEWAYS | BEAR |", "|---|---|---|---|"]
    for name, rr in matrix.items():
        cells = []
        for regime in ('BULL', 'SIDEWAYS', 'BEAR'):
            c = rr.get(regime)
            if c is None:
                cells.append("—")
            else:
                flag = {'CONFIRMED': '✓✓', 'PROMISING': '✓?', 'REJECTED': ''}[c['state']]
                cells.append(f"{c['exp_pct']:+.2f}% (N{c['n']},{c['win_rate']:.0f}%){flag}")
        L.append(f"| {name} | {cells[0]} | {cells[1]} | {cells[2]} |")
    L += ["", "Legend: ✓✓ CONFIRMED · ✓? PROMISING (thin CV) · blank REJECTED", ""]

    L += ["## CV detail (cells clearing the +0.50%/N>=100 regime bar)", ""]
    any_cv = False
    for name, rr in matrix.items():
        for regime, c in rr.items():
            if c['regime_pass']:
                any_cv = True
                L.append(f"- **{name} / {regime}** [{c['state']}]: cell {c['exp_pct']:+.2f}% "
                         f"N{c['n']} | late {c['late_exp']:+.2f}% N{c['late_n']} "
                         f"| early {c['early_exp']:+.2f}% | retention {c['retention']:.2f}")
    if not any_cv:
        L.append("- (no cell cleared the regime bar)")

    confirmed = sorted(((s, r, c) for s, rr in matrix.items() for r, c in rr.items()
                        if c['state'] == 'CONFIRMED'), key=lambda x: -x[2]['exp_pct'])
    promising = sorted(((s, r, c) for s, rr in matrix.items() for r, c in rr.items()
                        if c['state'] == 'PROMISING'), key=lambda x: -x[2]['exp_pct'])
    L += ["", "## CONFIRMED candidates (ranked)"]
    L += ([f"- {s} / {r}: {c['exp_pct']:+.2f}% net (N{c['n']}, win {c['win_rate']:.0f}%)"
           for s, r, c in confirmed] or ["- none"])
    L += ["", "## PROMISING candidates (thin CV — SHADOW to gather data)"]
    L += ([f"- {s} / {r}: {c['exp_pct']:+.2f}% net (N{c['n']}, win {c['win_rate']:.0f}%)"
           for s, r, c in promising] or ["- none"])

    L += ["", "```json", json.dumps(matrix, indent=2, default=float), "```", ""]
    with open(RESULTS, 'w') as f:
        f.write("\n".join(L))


if __name__ == "__main__":
    run()
