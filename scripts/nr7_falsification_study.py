"""NR7 Breakout falsification study — research-only, no production writes.

NR7 Breakout is the only strategy in wf_edge whose pooled OOS expectancy is
positive (run 08ff0ca6, 2026-08-28: 54 tickers, 1,311 trades, avg +1.63%/trade).
Before that number is treated as evidence of an edge, this study attacks it:
it re-derives the trade list with the exact wf-refresh OOS methodology, then
tests window consistency, transaction-cost sensitivity, liquidity, ticker /
temporal / market-state concentration, outlier dependence, sample size and the
multiple-testing context across the 9 strategies in wf_edge.

Falsification first: the goal is to kill the candidate, not to keep it.

Output: data/reports/nr7_falsification_<date>.md (+ per-trade CSV).
Usage:
  python -m scripts.nr7_falsification_study               # full corpus
  python -m scripts.nr7_falsification_study --tickers AALI --smoke
"""
import argparse
import csv
import os
import sqlite3
from datetime import datetime

import numpy as np
import pandas as pd

from config import DB_PATH
from data.loaders import _load_ohlcv_bulk
from engine.strategies import strategy_nr7_breakout
from research.walkforward_multi import walk_forward_split

WARMUP_TAIL = 60
BOOTSTRAP_N = 10_000
RNG_SEED = 20260903


def oos_trades_for_ticker(df: pd.DataFrame) -> list:
    """wf-refresh methodology applied to NR7 Breakout; returns raw OOS trades."""
    kept = []
    for w in walk_forward_split(df, train_months=12, test_months=3):
        train_df, test_df = w['train'], w['test']
        tail = train_df.tail(WARMUP_TAIL) if len(train_df) >= WARMUP_TAIL else train_df
        extended = pd.concat([tail, test_df], ignore_index=True)
        raw = strategy_nr7_breakout(extended, capital=50_000_000)
        for t in raw['trades']:
            if t.entry_date >= w['test_start']:
                kept.append({
                    'window': w['window'], 'test_start': w['test_start'],
                    'entry_date': t.entry_date, 'exit_date': t.exit_date,
                    'entry_price': t.entry_price, 'exit_price': t.exit_price,
                    'exit_reason': t.exit_reason,
                    'pnl_pct': t.pnl_pct, 'pnl_rp': t.pnl_rp,
                })
    return kept


def pooled_exp(pnls: np.ndarray) -> float:
    return float(pnls.mean()) if len(pnls) else 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tickers', default=None)
    ap.add_argument('--smoke', action='store_true')
    args = ap.parse_args()

    ohlcv_map = _load_ohlcv_bulk(final_only=True)
    tickers = sorted(ohlcv_map.keys())
    if args.tickers:
        want = [t.strip() for t in args.tickers.split(',')]
        tickers = [t for t in tickers if t in want]

    trades = []
    per_ticker = []
    for k, tk in enumerate(tickers, 1):
        df = ohlcv_map[tk]
        if df is None or len(df) < 60:
            continue
        ts = oos_trades_for_ticker(df)
        vol = df.set_index(df['date'].astype(str).str[:10])['volume']
        price_open = df.set_index(df['date'].astype(str).str[:10])['open']
        for t in ts:
            t['ticker'] = tk
            d = t['entry_date']
            t['entry_dollar_vol'] = (float(price_open.get(d, np.nan))
                                     * float(vol.get(d, np.nan)))
        trades.extend(ts)
        pnls = np.array([t['pnl_pct'] for t in ts])
        wins = pd.DataFrame(ts)
        if len(ts):
            cons = (wins.groupby('window')['pnl_pct'].mean() > 0).mean() * 100
        else:
            cons = 0.0
        per_ticker.append({'ticker': tk, 'n': len(ts),
                           'exp': pooled_exp(pnls),
                           'wr': float((pnls > 0).mean() * 100) if len(ts) else 0.0,
                           'consistency': cons,
                           'total_pnl_pct': float(pnls.sum())})
        if k % 150 == 0:
            print(f"[NR7-FALSIFY] {k}/{len(tickers)} tickers done", flush=True)

    res = pd.DataFrame(per_ticker)
    tr = pd.DataFrame(trades)
    os.makedirs('data/reports', exist_ok=True)
    stamp = datetime.now().strftime('%Y-%m-%d')
    tr.to_csv(f'data/reports/nr7_oos_trades_{stamp}.csv', index=False)

    # ---- Validation vs persisted wf_edge ----
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    wf = pd.read_sql("SELECT ticker, expectancy_pct, win_rate, n_trades "
                     "FROM wf_edge WHERE strategy='NR7 Breakout'", conn)
    # multiple-testing context: all strategies' cells
    all_cells = pd.read_sql(
        "SELECT strategy, expectancy_pct, win_rate, n_trades FROM wf_edge", conn)
    # point-in-time IHSG panic calendar (same definition as wf_gate_compare)
    ihsg = pd.read_sql("SELECT date, close FROM ohlcv WHERE ticker='IHSG' "
                       "ORDER BY date", conn)
    conn.close()
    closes = ihsg['close'].astype(float)
    ma200 = closes.rolling(200).mean()
    vol20 = closes.pct_change().rolling(20).std()
    vol_p75 = vol20.rolling(252, min_periods=60).quantile(0.75)
    panic = pd.Series(((closes < ma200) & (vol20 > vol_p75)).values,
                      index=ihsg['date'].astype(str).str[:10].values)
    tr['panic'] = tr['entry_date'].map(panic).astype(bool)

    merged = res.merge(wf, on='ticker', how='inner')
    n_match = (merged['n'] == merged['n_trades']).mean() * 100 if len(merged) else 0
    exp_diff = (merged['exp'] - merged['expectancy_pct']).abs()

    pnls = tr['pnl_pct'].values
    n = len(pnls)
    mean_exp = pooled_exp(pnls)
    rng = np.random.default_rng(RNG_SEED)
    boots = np.array([pooled_exp(pnls[rng.integers(0, n, n)]) for _ in range(BOOTSTRAP_N)])
    ci_lo, ci_hi = np.percentile(boots, [2.5, 97.5])

    # outlier dependence
    order = np.sort(pnls)[::-1]
    drop1 = pooled_exp(np.delete(pnls, np.argmax(pnls)))
    drop5 = pooled_exp(pnls[np.argsort(pnls)[:-5]])
    drop10 = pooled_exp(pnls[np.argsort(pnls)[:-10]])

    # ticker concentration
    r20 = res[res['n'] >= 20].copy()
    r20['share'] = r20['total_pnl_pct'].clip(lower=0)
    tot_pos = r20['share'].sum()
    top5_share = (r20['share'].nlargest(5).sum() / tot_pos * 100) if tot_pos > 0 else float('nan')
    ex_top5 = r20.nsmallest(len(r20) - 5, 'share')
    w_all = (r20['exp'] * r20['n']).sum() / r20['n'].sum()
    w_ex5_num = (r20[~r20['ticker'].isin(r20['share'].nlargest(5).index)]['exp']
                 * r20[~r20['ticker'].isin(r20['share'].nlargest(5).index)]['n']).sum()
    w_ex5 = w_ex5_num / r20[~r20['ticker'].isin(r20['share'].nlargest(5).index)]['n'].sum()

    # temporal
    tr['year'] = tr['entry_date'].str[:4]
    by_year = tr.groupby('year')['pnl_pct'].agg(['count', 'mean'])
    by_state = tr.groupby('panic')['pnl_pct'].agg(['count', 'mean'])

    # liquidity
    liq = tr.dropna(subset=['entry_dollar_vol'])
    liq_lo = liq[liq['entry_dollar_vol'] < liq['entry_dollar_vol'].quantile(0.33)]['pnl_pct']
    liq_hi = liq[liq['entry_dollar_vol'] > liq['entry_dollar_vol'].quantile(0.67)]['pnl_pct']

    # consistency at 50% bar (gatekeeper stage-6 proxy)
    cons_50 = (r20['consistency'] >= 50).mean() * 100 if len(r20) else 0

    # multiple-testing context
    strat_pool = all_cells.groupby('strategy').apply(
        lambda g: pd.Series({
            'cells': len(g), 'n': g['n_trades'].sum(),
            'exp_tw': (g['expectancy_pct'] * g['n_trades']).sum() / max(g['n_trades'].sum(), 1),
            'pos_share': (g['expectancy_pct'] > 0).mean() * 100,
        }), include_groups=False).sort_values('exp_tw', ascending=False)

    L = [
        f"# NR7 Breakout falsification study — {stamp}",
        "",
        f"Universe: {len(tickers)} tickers; OOS trades collected: {n}; "
        f"tickers with any OOS trade: {(res['n'] > 0).sum()}",
        "",
        "## Validation vs persisted wf_edge",
        f"- tickers compared: {len(merged)}; n exact-match {n_match:.1f}%; "
        f"|dExp| mean {exp_diff.mean():.4f}pp / max {exp_diff.max():.4f}pp",
        "",
        "## Pooled OOS",
        f"- n={n}, trade-weighted expectancy {mean_exp:.4f} %/trade, "
        f"win rate {(pnls>0).mean()*100:.2f}%",
        f"- bootstrap 95% CI (10k): [{ci_lo:.4f}, {ci_hi:.4f}] -> "
        f"{'CI excludes 0' if ci_lo > 0 else 'CI INCLUDES 0 — edge not established'}",
        f"- median {np.median(pnls):.4f}% vs mean {mean_exp:.4f}% "
        f"({'right-tail driven' if mean_exp > np.median(pnls) else 'left-tail driven'})",
        "",
        "## Outlier dependence (expectancy after dropping best trades)",
        f"- drop top 1: {drop1:.4f}pp | top 5: {drop5:.4f}pp | top 10: {drop10:.4f}pp",
        "",
        "## Cost sensitivity (engine bakes ~0.60% round trip into pnl)",
        f"- as-is {mean_exp:.4f}pp | +0.25% extra {(mean_exp-0.25):.4f}pp | "
        f"+0.50% extra {(mean_exp-0.50):.4f}pp",
        "",
        "## Ticker concentration (cells n>=20)",
        f"- {len(r20)} cells; top-5 tickers = {top5_share:.1f}% of positive pnl",
        f"- trade-weighted exp all: {w_all:.4f}pp; excluding top-5: {w_ex5:.4f}pp",
        f"- tickers with >=50% positive windows: {cons_50:.1f}% of cells",
        "",
        "## Temporal concentration (by entry year)",
        by_year.to_string(),
        "",
        "## Market state (IHSG panic calendar, point-in-time)",
        by_state.to_string(),
        "",
        "## Liquidity (entry-day open*volume terciles)",
        f"- low tercile n={len(liq_lo)} exp {liq_lo.mean():.4f}pp | "
        f"high tercile n={len(liq_hi)} exp {liq_hi.mean():.4f}pp",
        "",
        "## Multiple-testing context (wf_edge, 9 strategies)",
        strat_pool.to_string(),
        "",
        f"- NR7 positive-cell share {strat_pool.loc['NR7 Breakout','pos_share']:.1f}% "
        f"vs all-strategy mean "
        f"{all_cells.assign(pos=all_cells.expectancy_pct>0).groupby('strategy')['pos'].mean().mul(100).mean():.1f}%",
        "",
        "Per-trade detail: " f"data/reports/nr7_oos_trades_{stamp}.csv",
    ]
    report = "\n".join(L)
    path = f'data/reports/nr7_falsification_{stamp}.md'
    with open(path, 'w') as f:
        f.write(report + "\n")
    print(report)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
