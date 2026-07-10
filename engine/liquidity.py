"""Liquidity and value composite scoring for signal gate (Sprint 15 L1+L2).

L1 — Liquidity criteria:
  ADV (avg daily volume, lots) >= ADV_MIN_LOTS over last 30 trading days.
  market_cap >= MARKET_CAP_MIN (from stockbit_keystats). Fail-open when
  keystats missing — don't block tickers with no data.

L2 — Value composite score (0–100, higher = better value):
  Weighted normalisation of P/E, P/B, EV/EBITDA (lower-is-better, inverted),
  dividend yield (higher-is-better), PEG (lower-is-better). Fails-open to 50
  when all ratios are missing.
"""

import sqlite3
from typing import Optional
from data.db import connect as db_connect

# ── Thresholds ────────────────────────────────────────────────────────────────

ADV_MIN_LOTS     = 500_000          # 500K lots/day avg — below this = illiquid
MARKET_CAP_MIN   = 500_000_000_000  # Rp 500 billion minimum market cap
VALUE_SCORE_MIN  = 25.0             # bottom quartile cut-off (0–100 scale)
VALUE_LIQ_MIN_IDR = 5_000_000_000   # Rp 5 bn/day avg traded value — value-base liquidity floor


# ── L1: Liquidity helpers ─────────────────────────────────────────────────────

def get_adv_30d(conn: sqlite3.Connection, ticker: str, date: str) -> Optional[float]:
    """Avg daily volume (lots) over last 30 OHLCV rows on or before date."""
    row = conn.execute(
        "SELECT AVG(volume) FROM ("
        "  SELECT volume FROM ohlcv"
        "  WHERE ticker=? AND date<=? AND volume>0"
        "  ORDER BY date DESC LIMIT 30"
        ")",
        (ticker, date),
    ).fetchone()
    return float(row[0]) if row and row[0] is not None else None


def get_adv_value_30d(conn: sqlite3.Connection, ticker: str, date: str) -> Optional[float]:
    """Avg daily traded value in Rupiah (close*volume) over last 30 OHLCV rows
    on or before date. This is value-base liquidity — turnover, not share count —
    so it is comparable across price levels. None when no priced rows exist."""
    row = conn.execute(
        "SELECT AVG(close*volume) FROM ("
        "  SELECT close, volume FROM ohlcv"
        "  WHERE ticker=? AND date<=? AND volume>0 AND close>0"
        "  ORDER BY date DESC LIMIT 30"
        ")",
        (ticker, date),
    ).fetchone()
    return float(row[0]) if row and row[0] is not None else None


def passes_value_liquidity_gate(
    conn: sqlite3.Connection,
    ticker: str,
    date: str,
    min_idr: float = VALUE_LIQ_MIN_IDR,
) -> tuple[bool, str]:
    """Value-base liquidity gate: 30d avg daily turnover (Rp) must be >= min_idr.

    Fails open (passes) when there is no OHLCV data — don't block a ticker we
    simply can't price, consistent with passes_liquidity_gate's philosophy."""
    adv_val = get_adv_value_30d(conn, ticker, date)
    if adv_val is None:
        return True, "no ohlcv — fail-open"
    if adv_val < min_idr:
        return False, f"turnover Rp{adv_val/1e9:.2f}bn < Rp{min_idr/1e9:.1f}bn"
    return True, f"turnover Rp{adv_val/1e9:.2f}bn"


def select_top_liquid_longs(
    rows: list,
    conn: sqlite3.Connection,
    date: str,
    top_n: int = 3,
    min_idr: float = VALUE_LIQ_MIN_IDR,
) -> list:
    """From already-ranked watchlist rows, return up to top_n long-direction
    entries that clear the value-base liquidity gate, preserving input order."""
    picked = []
    for r in rows:
        if r.get("direction") != "long":
            continue
        ok, _ = passes_value_liquidity_gate(conn, r["ticker"], date, min_idr)
        if ok:
            picked.append(r)
        if len(picked) >= top_n:
            break
    return picked


def get_keystats(conn: sqlite3.Connection, ticker: str) -> dict:
    """Latest stockbit_keystats row for ticker. Empty dict when missing."""
    row = conn.execute(
        "SELECT pe_ttm, pbv, peg_ratio, div_yield, ev_ebitda, market_cap "
        "FROM stockbit_keystats WHERE ticker=? ORDER BY fetch_date DESC LIMIT 1",
        (ticker,),
    ).fetchone()
    if not row:
        return {}
    keys = ('pe_ttm', 'pbv', 'peg_ratio', 'div_yield', 'ev_ebitda', 'market_cap')
    return dict(zip(keys, row))


# ── L2: Value composite score ─────────────────────────────────────────────────

def compute_value_score(
    pe_ttm:    Optional[float],
    pbv:       Optional[float],
    peg_ratio: Optional[float],
    div_yield: Optional[float],
    ev_ebitda: Optional[float],
) -> float:
    """Return 0–100 value score. Higher = cheaper / better value.

    Components (weights sum to 1.0):
      PE (TTM)   30% — lower is cheaper, clamp [5, 50]
      PBV        25% — lower is cheaper, clamp [0.5, 10]
      EV/EBITDA  25% — lower is cheaper, clamp [3, 30]
      Div yield  15% — higher is better,  clamp [0, 10]
      PEG        05% — lower is cheaper, clamp [0.2, 3]
    """
    def _inv(v, lo, hi):
        """Normalise v to [0,1]: 1 when v==lo (best), 0 when v==hi (worst)."""
        if v is None or v <= 0:
            return None
        v = max(lo, min(hi, float(v)))
        return 1.0 - (v - lo) / (hi - lo)

    def _fwd(v, lo, hi):
        """Normalise v to [0,1]: 0 when v==lo (worst), 1 when v==hi (best)."""
        if v is None or v < 0:
            return None
        v = max(lo, min(hi, float(v)))
        return (v - lo) / (hi - lo)

    components = [
        (_inv(pe_ttm,    5,   50), 0.30),
        (_inv(pbv,       0.5, 10), 0.25),
        (_inv(ev_ebitda, 3,   30), 0.25),
        (_fwd(div_yield, 0,   10), 0.15),
        (_inv(peg_ratio, 0.2,  3), 0.05),
    ]

    total_weight = sum(w for v, w in components if v is not None)
    if total_weight == 0:
        return 50.0  # fail-open: no data → neutral score

    score = sum(v * w for v, w in components if v is not None) / total_weight
    return round(score * 100, 1)


# ── L1+L2: Combined lookup ────────────────────────────────────────────────────

def get_liquidity_value(db_path: str, ticker: str, date: str) -> dict:
    """Return all liquidity + value metrics for a single ticker.

    Returns:
        adv_30d, market_cap, value_score, is_liquid, has_value,
        pe_ttm, pbv, div_yield, ev_ebitda, peg_ratio.
    """
    conn = db_connect(db_path)
    try:
        adv = get_adv_30d(conn, ticker, date)
        ks  = get_keystats(conn, ticker)
    finally:
        conn.close()

    mc = ks.get('market_cap')
    vs = compute_value_score(
        ks.get('pe_ttm'), ks.get('pbv'), ks.get('peg_ratio'),
        ks.get('div_yield'), ks.get('ev_ebitda'),
    )
    # Fail-open on missing market_cap (consistent with passes_liquidity_gate)
    is_liquid = (adv is not None and adv >= ADV_MIN_LOTS and
                 (mc is None or mc >= MARKET_CAP_MIN))
    has_value = vs >= VALUE_SCORE_MIN

    return {
        'adv_30d':    adv,
        'market_cap': mc,
        'value_score': vs,
        'is_liquid':   is_liquid,
        'has_value':   has_value,
        'pe_ttm':      ks.get('pe_ttm'),
        'pbv':         ks.get('pbv'),
        'div_yield':   ks.get('div_yield'),
        'ev_ebitda':   ks.get('ev_ebitda'),
        'peg_ratio':   ks.get('peg_ratio'),
    }


# ── L3: Gate functions (used inside scanner) ──────────────────────────────────

def passes_liquidity_gate(
    conn: sqlite3.Connection, ticker: str, date: str
) -> tuple[bool, str]:
    """Return (ok, reason). Fail-open when market_cap not in keystats."""
    adv = get_adv_30d(conn, ticker, date)
    if adv is None or adv < ADV_MIN_LOTS:
        adv_str = f'{int(adv or 0):,}'
        return False, f"ADV {adv_str} lots < {ADV_MIN_LOTS:,} threshold"

    ks = get_keystats(conn, ticker)
    mc = ks.get('market_cap')
    if mc is None:
        return True, "ADV ok; market_cap unknown (fail-open)"
    if mc < MARKET_CAP_MIN:
        return False, f"market_cap Rp{mc/1e9:.0f}B < Rp{MARKET_CAP_MIN/1e9:.0f}B"

    return True, f"ADV {adv/1e6:.1f}M lots; mcap Rp{mc/1e9:.0f}B"


def passes_value_gate(
    conn: sqlite3.Connection, ticker: str
) -> tuple[bool, str]:
    """Return (ok, reason). Fail-open when no keystats exists."""
    ks = get_keystats(conn, ticker)
    if not ks:
        return True, "no keystats — fail-open"
    vs = compute_value_score(
        ks.get('pe_ttm'), ks.get('pbv'), ks.get('peg_ratio'),
        ks.get('div_yield'), ks.get('ev_ebitda'),
    )
    if vs < VALUE_SCORE_MIN:
        return False, f"value_score {vs} < {VALUE_SCORE_MIN} (bottom quartile)"
    return True, f"value_score {vs}"


# ── L4: Backtest impact analysis ──────────────────────────────────────────────

def compute_filter_impact(db_path: str, date: str) -> dict:
    """Compare backtest metrics for tickers that pass/fail the liquidity+value gate.

    Returns: filtered_count, total_count, and per-group stats
    (avg_win_rate, avg_return) for liquid_valued, liquid_only,
    value_only, and neither populations.
    """
    conn = db_connect(db_path)
    try:
        rows = conn.execute(
            "SELECT ticker, win_rate, best_return FROM backtest_cache "
            "WHERE win_rate IS NOT NULL AND best_return IS NOT NULL"
        ).fetchall()

        buckets: dict[str, list] = {
            'liquid_valued': [], 'liquid_only': [],
            'value_only': [],    'neither': [],
        }

        for ticker, wr, ret in rows:
            liq_ok, _  = passes_liquidity_gate(conn, ticker, date)
            val_ok, _  = passes_value_gate(conn, ticker)
            key = ('liquid_valued' if (liq_ok and val_ok)
                   else 'liquid_only' if liq_ok
                   else 'value_only'  if val_ok
                   else 'neither')
            buckets[key].append({'win_rate': float(wr), 'best_return': float(ret)})

        def _stats(items: list) -> dict:
            if not items:
                return {'count': 0, 'avg_win_rate': None, 'avg_return': None}
            return {
                'count':         len(items),
                'avg_win_rate':  round(sum(x['win_rate']    for x in items) / len(items), 2),
                'avg_return':    round(sum(x['best_return'] for x in items) / len(items), 2),
            }

        total = sum(len(v) for v in buckets.values())
        return {
            'date':          date,
            'total_tickers': total,
            'buckets':       {k: _stats(v) for k, v in buckets.items()},
            'thresholds': {
                'adv_min_lots':   ADV_MIN_LOTS,
                'market_cap_min': MARKET_CAP_MIN,
                'value_score_min': VALUE_SCORE_MIN,
            },
        }
    finally:
        conn.close()
