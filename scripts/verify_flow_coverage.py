#!/usr/bin/env python3
"""
Flow Data Coverage Verification

Checks completeness of stockbit_flow_bars data for walkforward universe.
Identifies tickers with gaps in the specified date range.
"""

import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple


def get_ticker_universe(db_path: str) -> List[str]:
    """Get all tickers in OHLCV (walkforward universe)."""
    conn = sqlite3.connect(db_path)
    tickers = [r[0] for r in conn.execute(
        "SELECT DISTINCT ticker FROM ohlcv ORDER BY ticker"
    ).fetchall()]
    conn.close()
    return tickers


def get_flow_coverage(db_path: str, ticker: str, start_date: str, end_date: str) -> Tuple[int, int]:
    """
    Returns (days_with_flow, total_days) for a ticker in date range.

    Counts distinct trade_date entries in stockbit_flow_bars.
    Total days calculated via date arithmetic (not DB query).
    """
    # Calculate total trading days (approximate: exclude weekends)
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    total = (end - start).days + 1
    # Subtract weekends (rough approximation)
    total -= total // 7 * 2

    conn = sqlite3.connect(db_path)
    flow_days = conn.execute(
        """SELECT COUNT(DISTINCT trade_date)
           FROM stockbit_flow_bars
           WHERE ticker=? AND trade_date BETWEEN ? AND ?""",
        (ticker, start_date, end_date)
    ).fetchone()[0]
    conn.close()

    return flow_days, total


def verify_flow_coverage(
    db_path: str,
    start_date: str,
    end_date: str,
    coverage_threshold: float = 0.95
) -> Dict:
    """
    Verify flow data coverage for all tickers in walkforward universe.

    Returns:
        {
            'total_tickers': int,
            'covered_tickers': int,  # tickers with >= threshold coverage
            'gap_tickers': List[str],  # tickers below threshold
            'coverage_pct': float,
            'details': List[dict]  # per-ticker breakdown
        }
    """
    tickers = get_ticker_universe(db_path)
    total = len(tickers)
    covered = 0
    gap_tickers = []
    details = []

    for ticker in tickers:
        flow_days, total_days = get_flow_coverage(db_path, ticker, start_date, end_date)
        coverage = flow_days / total_days if total_days > 0 else 0.0

        ticker_info = {
            'ticker': ticker,
            'flow_days': flow_days,
            'total_days': total_days,
            'coverage_pct': round(coverage * 100, 1)
        }
        details.append(ticker_info)

        if coverage >= coverage_threshold:
            covered += 1
        else:
            gap_tickers.append(ticker)

    return {
        'total_tickers': total,
        'covered_tickers': covered,
        'gap_tickers': gap_tickers,
        'coverage_pct': round(covered / total * 100, 1) if total > 0 else 0.0,
        'details': details
    }


def verify_lq45_coverage(db_path: str, start_date: str, end_date: str) -> Dict:
    """Verify coverage specifically for LQ45 tickers."""
    # LQ45 tickers as of 2026
    lq45_tickers = [
        'ADRO', 'AKRA', 'ANTM', 'ASII', 'BBCA', 'BBNI', 'BBRI', 'BRPT',
        'BTPS', 'EXCL', 'GOTO', 'GTLT', 'HEXA', 'HRUM', 'ICBP', 'INDF',
        'INDY', 'INCO', 'INFO', 'INTP', 'ITMG', 'JPFA', 'KLBF', 'MAPI',
        'MEDC', 'MIKA', 'MNCN', 'NCMA', 'PGAS', 'PTBA', 'PADI', 'SIDO',
        'SMCB', 'SMGR', 'TINS', 'TLKM', 'TPIA', 'UNTR', 'UNVR', 'WIKA',
        'WRMF', 'WSKT'
    ]

    conn = sqlite3.connect(db_path)
    total = len(lq45_tickers)
    covered = 0
    gap_tickers = []
    details = []

    for ticker in lq45_tickers:
        flow_days, total_days = get_flow_coverage(db_path, ticker, start_date, end_date)
        coverage = flow_days / total_days if total_days > 0 else 0.0

        ticker_info = {
            'ticker': ticker,
            'flow_days': flow_days,
            'total_days': total_days,
            'coverage_pct': round(coverage * 100, 1)
        }
        details.append(ticker_info)

        if coverage >= 0.95:
            covered += 1
        else:
            gap_tickers.append(ticker)

    conn.close()

    return {
        'total_tickers': total,
        'covered_tickers': covered,
        'gap_tickers': gap_tickers,
        'coverage_pct': round(covered / total * 100, 1) if total > 0 else 0.0,
        'details': details
    }


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Verify flow data coverage')
    parser.add_argument('--db', default='data/walkforward.db', help='Database path')
    parser.add_argument('--start', default='2026-01-01', help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end', default='2026-04-30', help='End date (YYYY-MM-DD)')
    parser.add_argument('--lq45-only', action='store_true', help='Only check LQ45 tickers')
    parser.add_argument('--threshold', type=float, default=0.95, help='Coverage threshold (default 0.95)')

    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"Error: Database not found: {db_path}")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"Flow Data Coverage Verification")
    print(f"{'='*60}")
    print(f"Database: {db_path}")
    print(f"Date Range: {args.start} to {args.end}")
    print(f"Threshold: {args.threshold*100}%")
    print(f"{'='*60}\n")

    if args.lq45_only:
        result = verify_lq45_coverage(str(db_path), args.start, args.end)
        print(f"LQ45 Coverage: {result['coverage_pct']}% ({result['covered_tickers']}/{result['total_tickers']})")
    else:
        result = verify_flow_coverage(str(db_path), args.start, args.end, args.threshold)
        print(f"Overall Coverage: {result['coverage_pct']}% ({result['covered_tickers']}/{result['total_tickers']})")

    print(f"\nGap Tickers ({len(result['gap_tickers'])}):")
    for t in result['gap_tickers'][:20]:  # Show first 20
        detail = next(d for d in result['details'] if d['ticker'] == t)
        print(f"  {t}: {detail['coverage_pct']}% ({detail['flow_days']}/{detail['total_days']} days)")
    if len(result['gap_tickers']) > 20:
        print(f"  ... and {len(result['gap_tickers']) - 20} more")

    # Exit code based on coverage
    sys.exit(0 if result['coverage_pct'] >= args.threshold * 100 else 1)


if __name__ == '__main__':
    main()
