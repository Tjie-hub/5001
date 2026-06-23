"""
scripts/edge_ranking.py — Dump today's edge ranking with per-term breakdown.

Shows, for each candidate, the composite edge AND every weighted term
(exp%·.40, cons·.20, flow·.20, reg·.10, tech·.10) plus the first veto reason —
so each name's score and its accept/skip decision are fully explainable.

Candidate source:
    default      → long setups from the unified watchlist (premarket set)
    --tickers    → explicit comma-separated list
    --universe   → every ticker that has a wf_edge row (validated universe)

Usage:
    python3 scripts/edge_ranking.py [--date YYYY-MM-DD] [--tickers AAA,BBB] [--universe]
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import DB_PATH, edge_mode
from engine.edge_score import edge_breakdown
from engine.edge_enrich import enrich_candidate, market_regime
from engine.veto import diagnose, EDGE_FLOOR, DEFAULT_EDGE_FLOOR, N_MAX, DEFAULT_N_MAX


def _ticker_regime(conn, ticker: str) -> str | None:
    """Per-ticker regime via detect_regime; None on insufficient data."""
    try:
        import pandas as pd
        from engine.regime_filter import detect_regime
        rows = conn.execute(
            "SELECT date, open, high, low, close, volume FROM ohlcv "
            "WHERE ticker=? ORDER BY date DESC LIMIT 120", (ticker,)).fetchall()
        if len(rows) < 30:
            return None
        df = pd.DataFrame(rows[::-1],
                          columns=['date', 'open', 'high', 'low', 'close', 'volume'])
        return detect_regime(df)
    except Exception:
        return None


def _watchlist_sources() -> dict:
    """ticker → sources from the unified watchlist (so is_mean_reversion is
    correct regardless of how the candidate list was chosen)."""
    from engine.unified_watchlist import build_unified_watchlist
    return {r['ticker']: r.get('sources', []) for r in build_unified_watchlist(DB_PATH)}


def _candidate_tickers(conn, args) -> list[tuple[str, list]]:
    """Return [(ticker, sources)] for the chosen source."""
    if args.tickers:
        src_map = _watchlist_sources()
        return [(t.strip().upper(), src_map.get(t.strip().upper(), []))
                for t in args.tickers.split(',') if t.strip()]
    if args.universe:
        src_map = _watchlist_sources()
        rows = conn.execute("SELECT DISTINCT ticker FROM wf_edge ORDER BY ticker").fetchall()
        return [(r[0], src_map.get(r[0], [])) for r in rows]
    from engine.unified_watchlist import build_unified_watchlist
    rows = build_unified_watchlist(DB_PATH)
    return [(r['ticker'], r.get('sources', []))
            for r in rows if r.get('direction') == 'long']


def build_ranking(conn, date_str: str, tickers_sources: list[tuple[str, list]]) -> dict:
    mreg = market_regime(conn)
    floor = EDGE_FLOOR.get(mreg, DEFAULT_EDGE_FLOOR)
    cap = N_MAX.get(mreg, DEFAULT_N_MAX)

    out = []
    for ticker, sources in tickers_sources:
        closes_rows = conn.execute(
            "SELECT close FROM ohlcv WHERE ticker=? ORDER BY date DESC LIMIT 60",
            (ticker,)).fetchall()
        closes = [r[0] for r in closes_rows][::-1]
        c = enrich_candidate(conn, ticker, date_str, closes=closes,
                             regime=_ticker_regime(conn, ticker), sources=sources)
        b = edge_breakdown(
            expectancy_pct=c['expectancy_pct'], consistency_pct=c['consistency_pct'],
            flow_score=c['flow_score'], regime=c['regime'],
            technical_votes=c['technical_votes'])
        edge, veto = diagnose(c, mreg)
        out.append({'ticker': ticker, 'cand': c, 'b': b,
                    'edge': b['edge'], 'veto': veto})
    out.sort(key=lambda x: x['edge'], reverse=True)
    return {'market_regime': mreg, 'floor': floor, 'cap': cap, 'rows': out}


def _print(rank: dict, date_str: str):
    print(f"\nEdge ranking — {date_str}   mode={edge_mode()}   "
          f"market={rank['market_regime']}   floor={rank['floor']}   "
          f"N_MAX={rank['cap']}\n")
    hdr = (f"{'ticker':<8}{'edge':>7} | {'exp.40':>7}{'con.20':>7}{'flw.20':>7}"
           f"{'reg.10':>7}{'tec.10':>7} | {'verdict'}")
    print(hdr)
    print('-' * len(hdr))
    survivors = 0
    for r in rank['rows']:
        b = r['b']
        verdict = 'SKIP ' + r['veto'] if r['veto'] else 'PASS'
        if not r['veto'] and survivors < rank['cap']:
            survivors += 1
            verdict = f'PICK #{survivors} (size {round(r["edge"], 2)})'
        elif not r['veto']:
            verdict = 'PASS (over cap)'
        print(f"{r['ticker']:<8}{r['edge']:>7.3f} | {b['expectancy']:>7.3f}"
              f"{b['consistency']:>7.3f}{b['flow']:>7.3f}{b['regime']:>7.3f}"
              f"{b['technical']:>7.3f} | {verdict}")
    print(f"\n{survivors} pick(s) within N_MAX={rank['cap']}; "
          f"{len(rank['rows'])} candidate(s) scored.\n")


def main():
    ap = argparse.ArgumentParser(description="Dump edge ranking with breakdown.")
    ap.add_argument('--date', default=datetime.now().strftime('%Y-%m-%d'))
    ap.add_argument('--tickers', default='')
    ap.add_argument('--universe', action='store_true')
    args = ap.parse_args()

    conn = sqlite3.connect(DB_PATH)
    try:
        ts = _candidate_tickers(conn, args)
        if not ts:
            print("No candidates for the chosen source.")
            return
        rank = build_ranking(conn, args.date, ts)
        _print(rank, args.date)
    finally:
        conn.close()


if __name__ == '__main__':
    main()
