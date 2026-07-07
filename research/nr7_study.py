"""NR7 edge-generalization study — pure statistics (audit Phase 4, first increment).

No DB, no I/O, no scheduler imports. Every number the study reports comes from
these functions so the methodology is unit-tested independent of a 5y backtest.
Net P&L is always full round-trip: costs applied to BOTH legs from raw prices.
"""
from engine.exits.costs import apply_costs


THRESHOLDS = {
    'min_net_exp':      0.50,   # %/trade net, the bar for "tradeable"
    't1_min_n':         300,    # universe pooled trade count
    't2_select_min':    5,      # min early trades for a ticker to be "selected"
    't2_min_n':         150,    # held-out late pooled trade count
    't2_min_retention': 0.50,   # late_exp / early_exp on selected tickers
    't3_min_n':         100,    # per-regime stratum trade count
}


def round_trip_net_pct(raw_entry: float, raw_exit: float) -> float:
    """Net %/trade after full round-trip costs, from RAW prices.

    Applies the buy leg to entry and the sell leg to exit via the single cost
    authority (engine.exits.costs), so this does not trust any upstream cost
    handling. Long-only (BUY entry, SELL exit)."""
    buy_fill = apply_costs(raw_entry, 'BUY')
    sell_fill = apply_costs(raw_exit, 'SELL')
    return (sell_fill - buy_fill) / buy_fill * 100.0


def pool(trades) -> dict:
    """Trade-weighted pooled net expectancy over a list of study trades."""
    n = len(trades)
    if n == 0:
        return {'exp_pct': 0.0, 'n': 0, 'win_rate': 0.0}
    nets = [round_trip_net_pct(t['raw_entry'], t['raw_exit']) for t in trades]
    wins = sum(1 for x in nets if x > 0)
    return {'exp_pct': sum(nets) / n, 'n': n, 'win_rate': 100.0 * wins / n}


def cv_split(trades, boundary_date: str):
    """Partition trades into (early, late) by entry_date < boundary_date."""
    early = [t for t in trades if t['entry_date'] < boundary_date]
    late = [t for t in trades if t['entry_date'] >= boundary_date]
    return early, late


def select_positive_tickers(trades, min_trades: int) -> set:
    """Tickers with >= min_trades and positive pooled net expectancy."""
    by_ticker = {}
    for t in trades:
        by_ticker.setdefault(t['ticker'], []).append(t)
    picked = set()
    for ticker, ts in by_ticker.items():
        if len(ts) >= min_trades and pool(ts)['exp_pct'] > 0:
            picked.add(ticker)
    return picked


def stratify_by_regime(trades) -> dict:
    """Pool net expectancy separately per entry-regime label."""
    buckets = {}
    for t in trades:
        buckets.setdefault(t['regime'], []).append(t)
    return {regime: pool(ts) for regime, ts in buckets.items()}


def evaluate(t1, t2, t3, thr) -> dict:
    """Apply pre-registered thresholds → PASS/FAIL per test + widen decision.

    t1: pool dict for the full liquid universe.
    t2: {'late_exp','late_n','early_exp','retention'} on early-selected tickers.
    t3: {regime: pool dict}.
    """
    me = thr['min_net_exp']
    t1_pass = t1['exp_pct'] >= me and t1['n'] >= thr['t1_min_n']
    t2_pass = (t2['late_exp'] >= me and t2['late_n'] >= thr['t2_min_n']
               and t2['retention'] >= thr['t2_min_retention'])
    t3_out = {}
    for regime, p in (t3 or {}).items():
        t3_out[regime] = {**p, 'pass': p['exp_pct'] >= me and p['n'] >= thr['t3_min_n']}

    widen_universe = t1_pass and t2_pass
    widen_sideways = bool(t3_out.get('SIDEWAYS', {}).get('pass'))
    parts = []
    if widen_universe:
        parts.append('WIDEN-UNIVERSE')
    if widen_sideways:
        parts.append('WIDEN-SIDEWAYS')
    decision = '+'.join(parts) if parts else 'DO-NOT-WIDEN'

    return {
        'T1': {**t1, 'pass': t1_pass},
        'T2': {**t2, 'pass': t2_pass},
        'T3': t3_out,
        'widen_universe': widen_universe,
        'widen_sideways': widen_sideways,
        'decision': decision,
    }
