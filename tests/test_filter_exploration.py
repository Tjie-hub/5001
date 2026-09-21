"""
test_filter_exploration.py — Test alternative TFB filters and find patterns.

Tests trade-level signal-quality filters (different angle from the stock-level
pre-screen that failed OOS). Runs single full-history backtests (fast) on the
12 tickers analysed previously, then ranks filters by their impact.

Filters tested (all AND-ed with existing TFB signal):
  1. atr_contracting   — ATR < 1.1× ATR_MA20  (vol not spiking)
  2. adx_trending      — 18 < ADX < 45         (trend present, not exhausted)
  3. efficiency        — ER(10) > 0.25          (directional, not choppy)
  4. ma_stacked        — MA10 > MA20 > MA50     (clean bullish alignment)
  5. pullback_ok       — close > 0.92 × 20-bar high  (not overextended)
  6. vr_capped         — VR < 5.0               (reject extreme volume spikes)
  7. rs_strong         — RS(20) vs IHSG > 0.95  (at least keeping up)
  8. ma20_slope_strong — MA20 slope > 1.0%      (stronger trend requirement)
  9. no_gap_up         — open < 1.03 × prev_high (no major gap chase)
 10. combo_conservative — atr_contracting + efficiency + ma_stacked
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
import sqlite3
from dataclasses import dataclass
from typing import List, Optional

from config import DB_PATH
from engine.indicators import calc_atr, calc_adx, calc_sma
from engine.strategies import (
    Trade, lot_size, apply_costs,
    filter_low_atr, filter_above_ma50, filter_vr_min, filter_uptrend, filter_vwma_above,
    strategy_trend_following_breakout as tfb_original,
)

# ═══════════════════════════════════════════════════════════════════════════════
# MODIFIED TFB — accepts extra_conditions list
# ═══════════════════════════════════════════════════════════════════════════════

def strategy_tfb_filtered(
    df: pd.DataFrame,
    capital: float = 50_000_000,
    extra_conditions: Optional[List[pd.Series]] = None,
) -> dict:
    """
    TFB with optional additional AND-conditions on signal bars.
    Each element in extra_conditions must be a boolean Series aligned to df.index.
    """
    from engine.regime_filter import calc_ma_slope

    strategy_name = 'Trend Following Breakout'
    initial_capital = capital

    if len(df) < 65:
        return {'strategy': strategy_name, 'trades': [],
                'equity': [capital] * len(df),
                'final_capital': capital, 'initial_capital': capital}

    ma20 = df['close'].rolling(20).mean()
    ma50 = df['close'].rolling(50).mean()
    atr = calc_atr(df, 14)
    avg_vol = df['volume'].rolling(20).mean()
    donchian20 = df['high'].rolling(20).max().shift(1)
    atr60_med = atr.rolling(60).median()
    ma20_slope = calc_ma_slope(df, 20, 5)

    signal = (
        (df['close'] > donchian20) &
        (df['volume'] > 1.8 * avg_vol) &
        (atr > 0.5 * atr60_med) &
        (df['close'] > ma50) &
        (ma20_slope > 0.5) &
        (df['volume'] < 4.0 * avg_vol)
    )

    # Apply extra conditions (each is a callable that takes df, returns Series)
    if extra_conditions:
        for cond_fn in extra_conditions:
            signal = signal & cond_fn(df).fillna(False)

    equity = [capital]
    trades = []
    in_trade = False
    entry_price = 0.0
    trail_stop = 0.0
    lots = 0
    entry_date = ''

    for i in range(65, len(df)):
        row = df.iloc[i]
        date = str(row['date'])[:10]
        cur_atr = atr.iloc[i]
        cur_ma20 = ma20.iloc[i]

        if in_trade:
            low_i = row['low']
            new_stop = row['close'] - 2.5 * cur_atr
            trail_stop = max(trail_stop, new_stop)

            exit_reason = None
            exit_price = None
            if low_i <= trail_stop:
                exit_price = apply_costs(trail_stop, 'SELL')
                exit_reason = 'TRAIL_SL'
            elif row['close'] < cur_ma20:
                exit_price = apply_costs(row['close'], 'SELL')
                exit_reason = 'MA20_BREAK'
            elif i == len(df) - 1:
                exit_price = apply_costs(row['close'], 'SELL')
                exit_reason = 'EOD'

            if exit_reason:
                gross = (exit_price - entry_price) * lots * 100
                pnl_pct = (exit_price - entry_price) / entry_price
                capital += gross
                trades.append(Trade(
                    entry_date=entry_date, exit_date=date,
                    entry_price=entry_price, exit_price=exit_price,
                    lots=lots, direction='BUY', exit_reason=exit_reason,
                    pnl_rp=gross, pnl_pct=pnl_pct * 100,
                    strategy=strategy_name
                ))
                in_trade = False
        elif signal.iloc[i - 1]:
            sig_atr = atr.iloc[i - 1]
            if pd.isna(sig_atr) or sig_atr <= 0:
                equity.append(capital)
                continue
            entry_price = apply_costs(row['open'], 'BUY')
            sl_dist = 2.5 * sig_atr
            sl_pct = sl_dist / entry_price
            if sl_pct <= 0.001:
                equity.append(capital)
                continue
            lots = lot_size(capital, entry_price, 0.005, sl_pct)
            cost = entry_price * lots * 100
            if cost <= capital and lots > 0:
                trail_stop = entry_price - sl_dist
                in_trade = True
                entry_date = date

        equity.append(capital)

    return {
        'strategy': strategy_name,
        'trades': trades,
        'equity': equity,
        'final_capital': capital,
        'initial_capital': initial_capital,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# FILTER DEFINITIONS — each returns a boolean Series aligned to df.index
# ═══════════════════════════════════════════════════════════════════════════════

def cond_atr_contracting(df):
    """ATR not spiking: ATR < 1.1 × rolling mean ATR20"""
    atr = calc_atr(df, 14)
    atr_ma = atr.rolling(20).mean()
    return atr < atr_ma * 1.1

def cond_adx_trending(df):
    """ADX indicates trend present but not exhausted: 18 < ADX < 45"""
    adx = calc_adx(df, 14)
    return (adx > 18) & (adx < 45)

def cond_efficiency(df, period=10):
    """Efficiency ratio: net move / sum of absolute moves > 0.25 → directional"""
    close = df['close']
    net_move = (close - close.shift(period)).abs()
    path = close.diff().abs().rolling(period).sum()
    er = (net_move / path.replace(0, np.nan)).fillna(0)
    return er > 0.25

def cond_ma_stacked(df):
    """MA10 > MA20 > MA50 — clean bullish alignment"""
    ma10 = calc_sma(df, 10)
    ma20 = calc_sma(df, 20)
    ma50 = calc_sma(df, 50)
    return (ma10 > ma20) & (ma20 > ma50)

def cond_pullback_ok(df, pct=0.92):
    """Close within 8% of 20-bar high — not overextended"""
    hh20 = df['high'].rolling(20).max()
    return df['close'] > hh20 * pct

def cond_vr_capped(df, cap=5.0):
    """Volume ratio below extreme threshold"""
    avg_vol = df['volume'].rolling(20).mean()
    vr = df['volume'] / avg_vol.replace(0, np.nan)
    return vr < cap

def cond_rs_strong(df, rs_df=None):
    """Relative strength vs market (approximation: vs self-MA50 if no IHSG)"""
    # Use price vs MA50 as a proxy when IHSG data not available
    ma50 = calc_sma(df, 50)
    rs = df['close'] / ma50.replace(0, np.nan)
    return rs > 0.90  # close within 10% of MA50

def cond_ma20_slope_strong(df):
    """Stricter MA20 slope: > 1.0% instead of base 0.5%"""
    from engine.regime_filter import calc_ma_slope
    slope = calc_ma_slope(df, 20, 5)
    return slope > 1.0

def cond_no_gap_up(df):
    """No major gap-up chase: today's open < 1.03 × yesterday's high"""
    prev_high = df['high'].shift(1)
    return df['open'] < prev_high * 1.03


# ═══════════════════════════════════════════════════════════════════════════════
# TEST HARNESS
# ═══════════════════════════════════════════════════════════════════════════════

FILTERS = {
    'baseline':             [],
    'atr_contracting':      [cond_atr_contracting],
    'adx_trending':         [cond_adx_trending],
    'efficiency':           [cond_efficiency],
    'ma_stacked':           [cond_ma_stacked],
    'pullback_ok':          [cond_pullback_ok],
    'vr_capped':            [cond_vr_capped],
    'rs_strong':            [cond_rs_strong],
    'ma20_slope_strong':    [cond_ma20_slope_strong],
    'no_gap_up':            [cond_no_gap_up],
    'combo_cons':           [cond_atr_contracting, cond_efficiency, cond_ma_stacked],
}


def evaluate_filter(ticker: str, df: pd.DataFrame, name: str,
                    conditions: list) -> dict:
    """Run TFB with given extra conditions and return metrics."""
    result = strategy_tfb_filtered(df, extra_conditions=conditions)
    trades = result['trades']
    capital_init = result['initial_capital']
    capital_final = result['final_capital']

    if not trades:
        return {
            'ticker': ticker, 'filter': name,
            'n_trades': 0, 'n_wins': 0, 'wr': 0,
            'total_return': 0.0, 'avg_pnl': 0.0,
            'max_dd': 0.0, 'profit_factor': 0,
        }

    pnls_pct = [t.pnl_pct for t in trades]
    winners = [p for p in pnls_pct if p > 0]
    losers = [p for p in pnls_pct if p <= 0]

    # Max drawdown
    equity = np.array(result['equity'])
    peak = np.maximum.accumulate(equity)
    dd = (equity - peak) / np.where(peak > 0, peak, 1)
    max_dd = float(np.min(dd) * 100)

    # Profit factor
    gross_profit = sum(winners)
    gross_loss = abs(sum(losers)) if losers else 0
    pf = gross_profit / gross_loss if gross_loss > 0 else 99

    return {
        'ticker': ticker, 'filter': name,
        'n_trades': len(trades),
        'n_wins': len(winners),
        'wr': round(len(winners) / len(trades) * 100, 1),
        'total_return': round((capital_final / capital_init - 1) * 100, 2),
        'avg_pnl': round(np.mean(pnls_pct), 2),
        'max_dd': round(max_dd, 2),
        'profit_factor': round(pf, 2),
    }


def load_ihsg(conn):
    """Load IHSG data for RS computation."""
    df = pd.read_sql("SELECT * FROM ohlcv WHERE ticker='IHSG' ORDER BY date", conn)
    return df


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    TICKERS = ['BRPT', 'ENRG', 'ANTM', 'DEWA', 'SCMA', 'ARCI',
               'DSSA', 'CDIA', 'TPIA', 'RAJA', 'BULL', 'MSIN']

    conn = sqlite3.connect(DB_PATH)
    rows = []
    n_total = len(TICKERS) * len(FILTERS)
    n_done = 0

    for ticker in TICKERS:
        df = pd.read_sql(
            "SELECT * FROM ohlcv WHERE ticker=? ORDER BY date",
            conn, params=(ticker,)
        )
        if len(df) < 65:
            print(f"SKIP {ticker}: only {len(df)} bars")
            continue

        for fname, fconds in FILTERS.items():
            try:
                r = evaluate_filter(ticker, df, fname, fconds)
                rows.append(r)
            except Exception as e:
                print(f"ERROR {ticker}/{fname}: {e}")
            n_done += 1

        print(f"  {ticker}: {len(FILTERS)} filters done ({n_done}/{n_total})")

    conn.close()

    # ── Aggregate results ──
    results_df = pd.DataFrame(rows)

    # Per-filter summary across all tickers
    print("\n" + "=" * 100)
    print("FILTER PERFORMANCE SUMMARY (mean across 12 tickers)")
    print("=" * 100)

    summary = results_df.groupby('filter').agg(
        tickers_tested=('ticker', 'nunique'),
        total_trades=('n_trades', 'sum'),
        avg_trades_per_ticker=('n_trades', 'mean'),
        avg_return=('total_return', 'mean'),
        avg_wr=('wr', 'mean'),
        avg_pnl=('avg_pnl', 'mean'),
        avg_max_dd=('max_dd', 'mean'),
        avg_pf=('profit_factor', 'mean'),
        n_profitable=('total_return', lambda x: (x > 0).sum()),
    ).round(2)

    # Sort by avg_return
    summary = summary.sort_values('avg_return', ascending=False)
    print(summary.to_string())

    # ── Per-ticker detail ──
    print("\n" + "=" * 100)
    print("PER-TICKER: BASELINE vs BEST FILTER")
    print("=" * 100)

    baseline = results_df[results_df['filter'] == 'baseline'].set_index('ticker')

    for ticker in TICKERS:
        if ticker not in baseline.index:
            continue
        base_row = baseline.loc[ticker]
        ticker_rows = results_df[results_df['ticker'] == ticker].copy()
        ticker_rows['delta_return'] = ticker_rows['total_return'] - base_row['total_return']
        best = ticker_rows.loc[ticker_rows['delta_return'].idxmax()]

        print(f"\n{ticker:6s}  baseline: ret={base_row['total_return']:+.2f}%  "
              f"WR={base_row['wr']:.0f}%  trades={int(base_row['n_trades'])}")
        print(f"        best ({best['filter']:20s}): ret={best['total_return']:+.2f}%  "
              f"delta={best['delta_return']:+.2f}%  trades={int(best['n_trades'])}")

    # ── Delta analysis ──
    print("\n" + "=" * 100)
    print("FILTER DELTA vs BASELINE (positive = filter helps)")
    print("=" * 100)

    # Compute delta per ticker/filter
    pivot = results_df.pivot_table(
        index='filter', columns='ticker', values='total_return', aggfunc='first'
    )
    baseline_vals = pivot.loc['baseline'] if 'baseline' in pivot.index else None
    if baseline_vals is not None:
        delta = pivot.subtract(baseline_vals, axis=1)
        delta_mean = delta.mean(axis=1).sort_values(ascending=False)
        delta_std = delta.std(axis=1)
        n_better = (delta > 0).sum(axis=1)

        delta_summary = pd.DataFrame({
            'mean_delta': delta_mean.round(2),
            'std_delta': delta_std.round(2),
            'n_better': n_better.astype(int),
            'n_total': len(TICKERS),
        })
        print(delta_summary.to_string())

    # ── Which filters help which ticker types? ──
    print("\n" + "=" * 100)
    print("PATTERN: FILTER IMPACT BY TICKER TYPE")
    print("=" * 100)

    # Classify tickers by baseline return
    if baseline_vals is not None:
        for ticker in TICKERS:
            if ticker not in delta.columns:
                continue
            base_ret = baseline_vals[ticker]
            ticker_deltas = delta[ticker].drop('baseline', errors='ignore').sort_values(ascending=False)
            best3 = ticker_deltas.head(3)
            worst3 = ticker_deltas.tail(3)
            tag = "WINNER" if base_ret > 2 else ("NEUTRAL" if base_ret > 0 else "LOSER")
            print(f"\n{ticker:6s} [{tag}] baseline={base_ret:+.2f}%")
            print(f"  helps:  {', '.join(f'{k}({v:+.1f})' for k,v in best3.items())}")
            print(f"  hurts:  {', '.join(f'{k}({v:+.1f})' for k,v in worst3.items())}")
