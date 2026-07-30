"""Lightweight backtest harness for premover patterns.

Replays score_ticker (CONTINUATION) and score_ticker_reversal
(REVERSAL_BREAKOUT) over a date range and measures the subsequent
N-day forward return per alert. Used to validate threshold choices
(e.g., is REVERSAL_BREAKOUT@45 a useful signal or noise?).

CLI:
    python3 -m engine.pattern_backtest --start 2026-02-01 --end 2026-04-30 \
        --threshold 45 --win-pct 10 --forward-days 10

Closes G7 in the close-strategy-gap roadmap.
"""

from __future__ import annotations

import argparse
import os
import sqlite3
from typing import Iterable

import pandas as pd

from engine.premover_detector import score_ticker, score_ticker_reversal
from config import default_db_path, resolve_db_path


DEFAULT_DB = default_db_path()


def run_pattern_backtest(
    db_path: str,
    start_date: str,
    end_date: str,
    threshold: int = 45,
    win_threshold_pct: float = 10.0,
    forward_days: int = 10,
    patterns: Iterable[str] = ('CONTINUATION', 'REVERSAL_BREAKOUT'),
    min_bars: int = 60,
    progress: bool = True,
) -> dict:
    """Replay premover scoring and measure forward returns.

    For each (ticker, date) in the range with at least `forward_days` of
    future bars, run the configured pattern scorers. Record any alert with
    score >= threshold along with the realized N-day forward return.

    Returns a dict:
        {
          'alerts':  [ {ticker, date, pattern, score, fwd_max_pct, fwd_end_pct,
                        is_winner}, ... ],
          'summary': { pattern: {alerts, winners, fp_rate_pct, avg_fwd_max,
                                 avg_fwd_end} },
        }
    """
    conn = sqlite3.connect(db_path)
    all_df = pd.read_sql(
        'SELECT ticker, date, open, high, low, close, volume FROM ohlcv '
        'ORDER BY ticker, date ASC',
        conn,
    )
    conn.close()

    for c in ['open', 'high', 'low', 'close', 'volume']:
        all_df[c] = all_df[c].astype(float)

    ohlcv_map = {t: g.reset_index(drop=True) for t, g in all_df.groupby('ticker')}
    ihsg_full = ohlcv_map.get('IHSG')

    in_range = all_df[(all_df['date'] >= start_date) & (all_df['date'] <= end_date)]
    dates = sorted(in_range['date'].unique())

    alerts: list[dict] = []
    pattern_set = set(patterns)
    total_steps = len(dates) * len(ohlcv_map)
    step = 0

    for date in dates:
        ihsg_slice = (
            ihsg_full[ihsg_full['date'] <= date] if ihsg_full is not None else None
        )

        for ticker, df in ohlcv_map.items():
            step += 1
            if progress and step % 20000 == 0:
                print(f"  ... {step:,}/{total_steps:,} ({step / total_steps * 100:.0f}%)")

            if ticker == 'IHSG':
                continue

            df_to_date = df[df['date'] <= date]
            if len(df_to_date) < min_bars:
                continue

            df_future = df[df['date'] > date].head(forward_days)
            if len(df_future) < forward_days:
                continue

            entry_close = df_to_date.iloc[-1]['close']
            fwd_max = df_future['high'].max()
            fwd_end = df_future.iloc[-1]['close']
            fwd_max_pct = (fwd_max / entry_close - 1.0) * 100.0
            fwd_end_pct = (fwd_end / entry_close - 1.0) * 100.0
            is_winner = fwd_max_pct >= win_threshold_pct

            if 'CONTINUATION' in pattern_set:
                r = score_ticker(df_to_date, ihsg_df=ihsg_slice)
                if r.get('score', 0) >= threshold:
                    alerts.append({
                        'ticker': ticker, 'date': date, 'pattern': 'CONTINUATION',
                        'score': r['score'], 'fwd_max_pct': round(fwd_max_pct, 2),
                        'fwd_end_pct': round(fwd_end_pct, 2),
                        'is_winner': is_winner,
                    })

            if 'REVERSAL_BREAKOUT' in pattern_set:
                r = score_ticker_reversal(df_to_date)
                if r.get('score', 0) >= threshold:
                    alerts.append({
                        'ticker': ticker, 'date': date, 'pattern': 'REVERSAL_BREAKOUT',
                        'score': r['score'], 'fwd_max_pct': round(fwd_max_pct, 2),
                        'fwd_end_pct': round(fwd_end_pct, 2),
                        'is_winner': is_winner,
                    })

    summary = {}
    df_alerts = pd.DataFrame(alerts) if alerts else pd.DataFrame(
        columns=['pattern', 'is_winner', 'fwd_max_pct', 'fwd_end_pct']
    )
    for pattern in pattern_set:
        subset = df_alerts[df_alerts['pattern'] == pattern]
        if len(subset) == 0:
            summary[pattern] = {
                'alerts': 0, 'winners': 0, 'fp_rate_pct': None,
                'avg_fwd_max': None, 'avg_fwd_end': None,
            }
            continue
        winners = int(subset['is_winner'].sum())
        summary[pattern] = {
            'alerts': len(subset),
            'winners': winners,
            'fp_rate_pct': round((1 - winners / len(subset)) * 100, 1),
            'avg_fwd_max': round(subset['fwd_max_pct'].mean(), 2),
            'avg_fwd_end': round(subset['fwd_end_pct'].mean(), 2),
        }

    return {'alerts': alerts, 'summary': summary}


def _print_summary(start, end, threshold, win_pct, forward_days, summary):
    print(
        f"\n=== Pattern Backtest: {start} → {end} "
        f"(threshold={threshold}, win=+{win_pct}% within {forward_days}d) ===\n"
    )
    for pattern, s in sorted(summary.items()):
        if s['alerts'] == 0:
            print(f"  {pattern}: 0 alerts")
            continue
        print(
            f"  {pattern}: {s['alerts']} alerts, {s['winners']} winners "
            f"({s['fp_rate_pct']}% FP), "
            f"avg max +{s['avg_fwd_max']}%, avg end {s['avg_fwd_end']:+.2f}%"
        )


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--start', required=True, help='YYYY-MM-DD')
    p.add_argument('--end', required=True, help='YYYY-MM-DD')
    p.add_argument('--threshold', type=int, default=45)
    p.add_argument('--win-pct', type=float, default=10.0)
    p.add_argument('--forward-days', type=int, default=10)
    p.add_argument('--db', default=resolve_db_path(os.getenv('DB_PATH', DEFAULT_DB)))
    p.add_argument('--out-csv', help='Write per-alert detail to CSV')
    p.add_argument('--pattern', action='append',
                   choices=['CONTINUATION', 'REVERSAL_BREAKOUT'],
                   help='Limit to one pattern (repeatable). Default: both.')
    p.add_argument('--quiet', action='store_true', help='Suppress progress lines')
    args = p.parse_args()

    patterns = tuple(args.pattern) if args.pattern else (
        'CONTINUATION', 'REVERSAL_BREAKOUT'
    )

    result = run_pattern_backtest(
        args.db, args.start, args.end,
        threshold=args.threshold,
        win_threshold_pct=args.win_pct,
        forward_days=args.forward_days,
        patterns=patterns,
        progress=not args.quiet,
    )

    _print_summary(args.start, args.end, args.threshold, args.win_pct,
                   args.forward_days, result['summary'])

    if args.out_csv and result['alerts']:
        pd.DataFrame(result['alerts']).to_csv(args.out_csv, index=False)
        print(f"\n  Per-alert detail → {args.out_csv}")


if __name__ == '__main__':
    main()
