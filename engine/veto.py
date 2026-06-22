"""
engine/veto.py — Deterministic pre-LLM vetoes + edge-based sizing.

Runs BEFORE the LLM agent firm. Two tiers, in order:

  Tier A — directional safety (HARD skip, catalyst-overridable):
    d1 distributing flow · d2 bearish technical (no mean-reversion thesis)
    d3 technical vs flow disagree · d4 market regime RISK_OFF
  Tier B — statistical edge gates (HARD skip):
    s1 n_trades<N_MIN · s2 consistency<MIN · s3 win_rate<MIN
    s4 edge < EDGE_FLOOR[market_regime]

Then a market-regime session cap, then size_mult = round(edge, 2).

Tier A is what closes the INCO leak: a name with strong validated history but
DISTRIBUTING flow + bearish technical *today* and no dated catalyst is dropped
before it ever reaches the firm. Edge sizing alone does not catch this (flow is
only a 0.20 term), which is why the hard veto exists in addition to the floor.

Pure function over candidate dicts (enrichment is the caller's job). Each
candidate dict may carry:
  flow_score, flow_verdict, flow_direction, tech_direction, is_mean_reversion,
  has_catalyst, n_trades, consistency_pct, win_rate, expectancy_pct, regime,
  technical_votes
"""
from typing import List

from engine.edge_score import compute_edge

N_MIN_TRADES     = 20
MIN_CONSISTENCY  = 30.0
MIN_WIN_RATE     = 35.0
FLOW_DISTRIB_CUT = -3            # composite_score at/below this = distributing

EDGE_FLOOR = {'BULL': 0.65, 'SIDEWAYS': 0.72, 'BEAR': 0.72}
DEFAULT_EDGE_FLOOR = 0.72
N_MAX = {'BULL': 3, 'SIDEWAYS': 1, 'BEAR': 0}   # by MARKET regime
DEFAULT_N_MAX = 1


def _flow_distributing(c: dict) -> bool:
    if c.get('flow_verdict') == 'DISTRIBUTING':
        return True
    cs = c.get('flow_score')
    return cs is not None and cs <= FLOW_DISTRIB_CUT


def _tech_bearish(c: dict) -> bool:
    return c.get('tech_direction') == 'BEARISH'


def _directions_disagree(c: dict) -> bool:
    td, fd = c.get('tech_direction'), c.get('flow_direction')
    return bool(td and fd and td != 'NEUTRAL' and fd != 'NEUTRAL' and td != fd)


def diagnose(c: dict, market_regime: str):
    """Per-candidate verdict (cap excluded). Returns (edge, veto_reason).

    veto_reason is None when the candidate clears every Tier A + Tier B gate;
    otherwise it is the first failing gate id (e.g. 'd1:distributing_flow').
    edge is the computed score when reachable (None when vetoed before s4).
    """
    cat = bool(c.get('has_catalyst'))

    # ── Tier A: directional safety (catalyst-overridable) ──
    if _flow_distributing(c) and not cat:
        return None, 'd1:distributing_flow'
    if _tech_bearish(c) and not c.get('is_mean_reversion') and not cat:
        return None, 'd2:bearish_tech'
    if _directions_disagree(c) and not cat:
        return None, 'd3:tech_flow_disagree'
    if market_regime == 'BEAR' and not cat:
        return None, 'd4:market_risk_off'

    # ── Tier B: statistical edge gates ──
    n = c.get('n_trades')
    if n is None or n < N_MIN_TRADES:
        return None, 's1:few_trades'
    if (c.get('consistency_pct') or 0) < MIN_CONSISTENCY:
        return None, 's2:low_consistency'
    if (c.get('win_rate') or 0) < MIN_WIN_RATE:
        return None, 's3:low_win_rate'

    edge = compute_edge(
        expectancy_pct=c.get('expectancy_pct'),
        consistency_pct=c.get('consistency_pct'),
        flow_score=c.get('flow_score'),
        regime=c.get('regime'),                  # per-ticker regime fit
        technical_votes=c.get('technical_votes'),
    )
    floor = EDGE_FLOOR.get(market_regime, DEFAULT_EDGE_FLOOR)
    if edge < floor:
        return edge, 's4:below_floor'
    return edge, None


def apply_vetoes(
    candidates: List[dict],
    market_regime: str,
    open_positions_count: int = 0,
) -> List[dict]:
    """Filter candidates through Tier A + Tier B + market-regime cap.

    Returns survivors (sorted by edge desc, capped) with `edge_score` and
    `size_mult` injected. An empty list is a valid, good output.
    """
    survivors: List[dict] = []
    for c in candidates:
        edge, veto = diagnose(c, market_regime)
        if veto is not None:
            continue
        c['edge_score'] = edge
        c['size_mult'] = round(edge, 2)
        survivors.append(c)

    survivors.sort(key=lambda x: x['edge_score'], reverse=True)

    # Market-regime session cap; a dated catalyst may add one slot in RISK_OFF.
    cap = N_MAX.get(market_regime, DEFAULT_N_MAX)
    if market_regime == 'BEAR' and any(s.get('has_catalyst') for s in survivors):
        cap += 1
    cap = max(0, cap - open_positions_count)
    return survivors[:cap]
