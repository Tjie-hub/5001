"""
engine/edge_enrich.py — Build veto-ready candidate dicts from the DB.

Joins, per ticker: best wf_edge row (validated OOS stats), latest stockbit_flow
(composite_score + verdict), per-ticker regime (caller-supplied or detected),
technical direction (MA stack), mean-reversion thesis (from source/strategy),
and catalyst flag. The result is the dict shape engine/veto.apply_vetoes expects.
"""
import logging
from datetime import date

from engine.technicals import tech_direction
from engine.catalyst import has_catalyst
from engine.wf_edge import ensure_wf_edge_table

logger = logging.getLogger(__name__)
_WF_STALE_DAYS = 7

# Sources/strategies that legitimately enter against a bearish tape.
MR_SOURCES    = {'REVERSAL', 'BEAR_DIP'}
MR_STRATEGIES = {'vwap_reversion', 'panic_rebound', 'conservative'}


def _flow_direction(composite_score, verdict) -> str:
    if verdict == 'DISTRIBUTING':
        return 'BEARISH'
    if verdict == 'ACCUMULATING':
        return 'BULLISH'
    if composite_score is None or composite_score == 0:
        return 'NEUTRAL'
    return 'BULLISH' if composite_score > 0 else 'BEARISH'


def _is_mean_reversion(sources, strategies) -> bool:
    return bool(set(sources or ()) & MR_SOURCES
                or set(strategies or ()) & MR_STRATEGIES)


def _latest_flow(conn, ticker):
    row = conn.execute(
        "SELECT composite_score, verdict FROM stockbit_flow "
        "WHERE ticker=? ORDER BY trade_date DESC LIMIT 1", (ticker,),
    ).fetchone()
    return (row[0], row[1]) if row else (None, None)


def _best_wf_edge(conn, ticker) -> dict:
    """Best (highest expectancy) validated strategy for the ticker, if any.
    Self-heals when wf_edge hasn't been built yet → returns {} (s1 drops it).
    Warns (but does not drop) when the stats are stale — refresh_wf_scores()
    may not have run since a fresh deploy / DB restore."""
    ensure_wf_edge_table(conn)
    row = conn.execute(
        "SELECT expectancy_pct, win_rate, consistency_pct, sharpe, n_trades, "
        "last_computed "
        "FROM wf_edge WHERE ticker=? ORDER BY expectancy_pct DESC LIMIT 1",
        (ticker,),
    ).fetchone()
    if not row:
        return {}
    last_computed = row[5]
    if last_computed:
        try:
            computed_date = date.fromisoformat(str(last_computed)[:10])
            age_days = (date.today() - computed_date).days
            if age_days > _WF_STALE_DAYS:
                logger.warning(
                    "wf_edge for %s is stale (last_computed=%s, %d days old) — "
                    "run refresh_wf_scores()", ticker, last_computed, age_days)
        except (ValueError, TypeError):
            logger.warning("wf_edge for %s has unparseable last_computed=%r",
                           ticker, last_computed)
    return {'expectancy_pct': row[0], 'win_rate': row[1],
            'consistency_pct': row[2], 'sharpe': row[3], 'n_trades': row[4]}


def enrich_candidate(conn, ticker, scan_date, *, closes=None, regime=None,
                     sources=(), strategies=(), technical_votes=None) -> dict:
    """Assemble one veto-ready candidate dict. Missing wf_edge → stats stay
    None (Tier B s1 will drop it). Missing flow → None (treated as no signal)."""
    cs, verdict = _latest_flow(conn, ticker)
    wf = _best_wf_edge(conn, ticker)
    return {
        'ticker':            ticker,
        'flow_score':        cs,
        'flow_verdict':      verdict,
        'flow_direction':    _flow_direction(cs, verdict),
        'tech_direction':    tech_direction(closes) if closes else 'NEUTRAL',
        'technical_votes':   technical_votes,
        'is_mean_reversion': _is_mean_reversion(sources, strategies),
        'has_catalyst':      has_catalyst(conn, ticker, scan_date),
        'regime':            regime,
        'n_trades':          wf.get('n_trades'),
        'consistency_pct':   wf.get('consistency_pct'),
        'win_rate':          wf.get('win_rate'),
        'expectancy_pct':    wf.get('expectancy_pct'),
    }


def market_regime(conn) -> str:
    """Market (IHSG) regime → BULL / BEAR / SIDEWAYS. Drives EDGE_FLOOR + cap.
    Falls back to SIDEWAYS on any error or missing data."""
    try:
        import pandas as pd
        from engine.regime_filter import detect_regime
        rows = conn.execute(
            "SELECT date, open, high, low, close, volume FROM ohlcv "
            "WHERE ticker='IHSG' ORDER BY date DESC LIMIT 120",
        ).fetchall()
        if not rows:
            return 'SIDEWAYS'
        df = pd.DataFrame(rows[::-1],
                          columns=['date', 'open', 'high', 'low', 'close', 'volume'])
        return detect_regime(df)
    except Exception as e:
        logger.warning("market_regime failed (%s) — falling back to SIDEWAYS", e)
        return 'SIDEWAYS'
