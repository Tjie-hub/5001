#!/usr/bin/env python3
"""NR7 edge-generalization study runner (audit Phase 4, first increment).

Runs NR7 walk-forward across the liquid universe, labels each OOS trade with its
entry regime, feeds research.nr7_study, and writes a results doc + JSON. Read-only
w.r.t. production: creates no live-path changes, only the results file.
"""
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pandas as pd

from data.db import connect as db_connect
from engine.liquidity import get_adv_value_30d, VALUE_LIQ_MIN_IDR
from engine.strategies import strategy_nr7_breakout
from research.walkforward_multi import walk_forward_split
from engine.regime_filter import detect_regime
from engine.exits.costs import COMMISSION_SELL, SLIPPAGE
import research.nr7_study as ns

DB_PATH = os.getenv('DB_PATH', os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), 'data', 'walkforward.db'))
RESULTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       'docs', 'superpowers', 'results',
                       '2026-07-07-nr7-generalization-study.md')

# Matches run_walk_forward's get_warmup([calc_vwap, calc_adx, calc_ma_slope,
# calc_atr]) → 60, so the study's NR7 trade set is identical to what wf_edge saw.
WARMUP_BARS = 60
_SELL_ADJ = 1.0 - COMMISSION_SELL - SLIPPAGE   # invert strategy's SELL-leg cost


def _regime_at(full_df: pd.DataFrame, entry_date: str) -> str:
    """Regime from trailing data only (<= entry_date), no look-ahead."""
    hist = full_df[full_df['date'] <= entry_date].tail(250)
    if len(hist) < 30:
        return 'SIDEWAYS'
    return detect_regime(hist.reset_index(drop=True))


def collect_trades_for_ticker(ticker: str, df: pd.DataFrame) -> list:
    """NR7 OOS trades for one ticker as study-trade dicts (raw prices + regime).

    Mirrors run_walk_forward: each 3mo test window gets a 60-bar warmup tail
    prepended, and trades entered before test_start are dropped. strategy_nr7
    stores raw entry but SELL-cost-adjusted exit; we invert that one adjustment
    to recover raw_exit so nr7_study applies full round-trip costs from raw
    prices (single cost authority)."""
    df = df.sort_values('date').reset_index(drop=True)
    out = []
    for w in walk_forward_split(df, train_months=12, test_months=3):
        train_df, test_df, test_start = w['train'], w['test'], w['test_start']
        if len(test_df) < 25:
            continue
        warmup = train_df.tail(WARMUP_BARS) if len(train_df) >= WARMUP_BARS else train_df
        extended = pd.concat([warmup, test_df], ignore_index=True)
        res = strategy_nr7_breakout(extended)
        for tr in res.get('trades', []):
            entry = str(tr.entry_date)[:10]
            if entry < test_start:          # drop warmup-window trades
                continue
            out.append({
                'ticker': ticker,
                'entry_date': entry,
                'raw_entry': float(tr.entry_price),
                'raw_exit': float(tr.exit_price) / _SELL_ADJ,
                'regime': _regime_at(df, entry),
            })
    return out


def liquid_universe(conn, as_of: str) -> list:
    tickers = [r[0] for r in conn.execute(
        "SELECT DISTINCT ticker FROM ohlcv WHERE ticker != 'IHSG'")]
    liq = []
    for t in tickers:
        adv = get_adv_value_30d(conn, t, as_of)
        if adv is not None and adv >= VALUE_LIQ_MIN_IDR:
            liq.append(t)
    return liq


def run():
    conn = db_connect(DB_PATH)
    as_of = conn.execute("SELECT MAX(date) FROM ohlcv").fetchone()[0]
    universe = liquid_universe(conn, as_of)
    all_trades = []
    for t in universe:
        df = pd.read_sql(
            "SELECT date, open, high, low, close, volume FROM ohlcv "
            "WHERE ticker=? ORDER BY date", conn, params=(t,))
        if len(df) < 300:
            continue
        all_trades.extend(collect_trades_for_ticker(t, df))
    conn.close()

    dates = sorted(t['entry_date'] for t in all_trades)
    boundary = dates[len(dates) // 2] if dates else '2099-01-01'

    t1 = ns.pool(all_trades)
    early, late = ns.cv_split(all_trades, boundary)
    picked = ns.select_positive_tickers(early, ns.THRESHOLDS['t2_select_min'])
    late_sel = [x for x in late if x['ticker'] in picked]
    early_sel = [x for x in early if x['ticker'] in picked]
    late_pool, early_pool = ns.pool(late_sel), ns.pool(early_sel)
    retention = (late_pool['exp_pct'] / early_pool['exp_pct']
                 if early_pool['exp_pct'] > 0 else 0.0)
    t2 = {'late_exp': late_pool['exp_pct'], 'late_n': late_pool['n'],
          'early_exp': early_pool['exp_pct'], 'retention': retention}
    t3 = ns.stratify_by_regime(all_trades)
    verdict = ns.evaluate(t1, t2, t3, ns.THRESHOLDS)

    _write_results(as_of, len(universe), boundary, t1, t2, t3, verdict)
    print("DECISION:", verdict['decision'])
    return verdict


def _write_results(as_of, n_universe, boundary, t1, t2, t3, verdict):
    os.makedirs(os.path.dirname(RESULTS), exist_ok=True)
    lines = [
        "# NR7 Edge-Generalization Study — Results", "",
        f"Run: {datetime.now().isoformat(timespec='seconds')} | corpus as-of {as_of} | "
        f"liquid universe {n_universe} tickers | CV boundary {boundary}", "",
        "## T1 — universe pooled (net of round-trip costs)",
        f"- exp {t1['exp_pct']:+.3f}%/trade | N {t1['n']} | win {t1['win_rate']:.1f}% "
        f"| **{'PASS' if verdict['T1']['pass'] else 'FAIL'}** (bar >= +0.50%, N >= 300)", "",
        "## T2 — selection / chronological CV",
        f"- early-selected tickers: late exp {t2['late_exp']:+.3f}% | late N {t2['late_n']} "
        f"| early exp {t2['early_exp']:+.3f}% | retention {t2['retention']:.2f} "
        f"| **{'PASS' if verdict['T2']['pass'] else 'FAIL'}** "
        f"(bar >= +0.50%, N >= 150, retention >= 0.50)", "",
        "## T3 — regime strata",
    ]
    for regime, p in verdict['T3'].items():
        lines.append(f"- {regime}: exp {p['exp_pct']:+.3f}% | N {p['n']} | win {p['win_rate']:.1f}% "
                     f"| **{'PASS' if p['pass'] else 'FAIL'}** (bar >= +0.50%, N >= 100)")
    lines += ["", f"## DECISION: **{verdict['decision']}**", "",
              "```json", json.dumps(verdict, indent=2), "```", ""]
    with open(RESULTS, 'w') as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    run()
