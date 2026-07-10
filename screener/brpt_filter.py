"""
brpt_filter.py — Stock Screener: Pick stocks comparable to BRPT
===============================================================
Criteria: Big Liquidity + Tradeable + Strategy-Viable
           (high volume, sufficient range for BRPT-style strategies,
            walk-forward profitability, good fundamentals)

BRPT Reference Profile (pre-crash "normal" state, 2026-05):
  - avg_vol_20d: ~420M IDR
  - 90-day range: ~112% (highly tradable)
  - Close: 1,500–2,300 range
  - PE: ~15 | PBV: ~3.5 | ROE: ~24% | NPM: ~3.5% | DER: ~3.5
  - VR > 1.3x: 12/60 days (strategies triggerable)
  - WF strategies profitable: 6/10 (Conservative +3.54%, Momentum +3.17%, etc.)
  - ADX: 23-58 (trending profile)
  - IDX30 / LQ45 / IDX80 member

ANTI-PATTERN — BBCA (do NOT rank high):
  - 90-day range: 21.8% (too tight for BRPT TP/SL targets)
  - WF strategies: ALL NEGATIVE (best is -0.25%)
  - VR > 1.3x: 8/60 but range too small to matter
  - ADX: 15-31 (sideways 3/4 windows)
  - Commission eats 17% of daily range

Usage:
    python -m screener.brpt_filter                  # top 20, flat table
    python -m screener.brpt_filter --categorized    # grouped by verdict
    python -m screener.brpt_filter --verdict tradeable  # only STRONG+VIABLE
    python -m screener.brpt_filter --verdict strong --json
    python -m screener.brpt_filter --export peers.csv
"""

import sqlite3
import os
import sys
import json
import csv
import math
from datetime import date as dt_date
from typing import Optional
from data.db import connect as db_connect

# ── Paths ──────────────────────────────────────────────────────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT = os.path.dirname(_HERE)
_DB_PATH = os.path.join(_PROJECT, "data", "walkforward.db")

# ── BRPT Reference Values (pre-crash baseline) ─────────────────────────────────
BRPT_PROFILE = {
    "ticker": "BRPT",
    "avg_vol_20d": 420_000_000,
    "range_90d_pct": 112.0,
    "close_low": 1_500,
    "close_high": 2_300,
    "pe_ttm": 14.82,
    "pbv": 3.5,
    "roe": 23.64,
    "npm": 3.52,
    "der": 3.47,
    "in_idx30": 1,
    "in_lq45": 1,
    "in_idx80": 1,
}

# ── Hard Filter Thresholds ─────────────────────────────────────────────────────
MIN_AVG_VOL = 50_000_000
MIN_CLOSE = 200
MAX_PE = 50
MIN_PE = 1
MIN_ROE = 0
MAX_DER = 20
MIN_NPM = -50
MIN_RANGE_90D = 15.0

# ── Scoring Weights (4 dimensions) ─────────────────────────────────────────────
W_LIQUIDITY = 0.25
W_FUNDAMENTALS = 0.15
W_VIABILITY = 0.40
W_SIMILARITY = 0.20

# ── Viability Sub-Weights ──────────────────────────────────────────────────────
W_RANGE = 0.35
W_WF_PROFIT = 0.35
W_VR_TRIGGER = 0.15
W_ADX_PROFILE = 0.15


# ═══════════════════════════════════════════════════════════════════════════════
# DATABASE
# ═══════════════════════════════════════════════════════════════════════════════

def _get_conn():
    conn = db_connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _latest_screen_date(conn) -> Optional[str]:
    row = conn.execute("SELECT MAX(date) FROM daily_screen").fetchone()
    return row[0] if row else None


# ═══════════════════════════════════════════════════════════════════════════════
# FETCH UNIVERSE
# ═══════════════════════════════════════════════════════════════════════════════

def fetch_universe(conn, screen_date: str) -> list[dict]:
    query = """
        SELECT 
            ds.ticker, ds.close, ds.volume, ds.avg_vol_20d, ds.vol_ratio,
            ds.vwap, ds.delta, ds.signal, ds.consec_up, ds.vpin,
            ks.pe_ttm, ks.pbv, ks.roe, ks.der, ks.npm, ks.eps_ttm,
            ks.market_cap, ks.rev_growth, ks.earn_growth, ks.current_ratio,
            it.in_idx30, it.in_lq45, it.in_idx80,
            wf.best_return as wf_best_return, wf.best_strategy as wf_best_strategy,
            wf.avg_return as wf_avg_return, wf.positive_count as wf_positive_count,
            wf.total_strategies as wf_total_strategies,
            wf.top_consistency as wf_top_consistency,
            bc.regime, bc.best_strategy as bt_best_strategy,
            bc.best_return as bt_best_return, bc.win_rate as bt_win_rate,
            bc.sharpe as bt_sharpe,
            sf.net_lot, sf.composite_score as flow_score, sf.verdict as flow_verdict,
            rng.range_90d_pct, rng.high_90d, rng.low_90d,
            vr60.vr_exceed_1_3, vr60.vr_exceed_1_8, vr60.vr_max_60d
        FROM daily_screen ds
        LEFT JOIN (
            SELECT k.* FROM stockbit_keystats k
            INNER JOIN (SELECT ticker, MAX(fetch_date) as max_date
                        FROM stockbit_keystats GROUP BY ticker) latest
            ON k.ticker = latest.ticker AND k.fetch_date = latest.max_date
        ) ks ON ds.ticker = ks.ticker
        LEFT JOIN idx_tickers it ON ds.ticker = it.ticker
        LEFT JOIN (
            SELECT ticker,
                MAX(avg_return_pct) as best_return,
                MAX(CASE WHEN avg_return_pct = (SELECT MAX(avg_return_pct) FROM wf_scores w2 WHERE w2.ticker = wf_scores.ticker) THEN strategy END) as best_strategy,
                AVG(avg_return_pct) as avg_return,
                SUM(CASE WHEN avg_return_pct > 0 THEN 1 ELSE 0 END) as positive_count,
                COUNT(*) as total_strategies,
                MAX(consistency_pct) as top_consistency
            FROM wf_scores GROUP BY ticker
        ) wf ON ds.ticker = wf.ticker
        LEFT JOIN (
            SELECT ticker, regime, best_strategy, best_return, win_rate, sharpe
            FROM backtest_cache
            WHERE computed_date = (SELECT MAX(computed_date) FROM backtest_cache)
        ) bc ON ds.ticker = bc.ticker
        LEFT JOIN (
            SELECT ticker, net_lot, composite_score, verdict
            FROM stockbit_flow WHERE trade_date = ?
        ) sf ON ds.ticker = sf.ticker
        LEFT JOIN (
            SELECT ticker,
                (MAX(high) - MIN(low)) * 100.0 / NULLIF(MIN(low), 0) as range_90d_pct,
                MAX(high) as high_90d, MIN(low) as low_90d
            FROM ohlcv WHERE date >= date(?, '-90 days') AND date <= ?
            GROUP BY ticker
        ) rng ON ds.ticker = rng.ticker
        LEFT JOIN (
            SELECT ticker,
                SUM(CASE WHEN vol_ratio > 1.3 THEN 1 ELSE 0 END) as vr_exceed_1_3,
                SUM(CASE WHEN vol_ratio > 1.8 THEN 1 ELSE 0 END) as vr_exceed_1_8,
                MAX(vol_ratio) as vr_max_60d
            FROM daily_screen WHERE date >= date(?, '-60 days') AND date <= ?
            GROUP BY ticker
        ) vr60 ON ds.ticker = vr60.ticker
        WHERE ds.date = ?
          AND ds.close > ? AND ds.avg_vol_20d > ?
          AND (ks.pe_ttm IS NULL OR (ks.pe_ttm > ? AND ks.pe_ttm < ?))
          AND (ks.roe IS NULL OR ks.roe > ?)
          AND (ks.der IS NULL OR ks.der < ?)
          AND (ks.npm IS NULL OR ks.npm > ?)
          AND (rng.range_90d_pct IS NULL OR rng.range_90d_pct > ?)
        ORDER BY ds.avg_vol_20d DESC
    """
    params = (
        screen_date,
        screen_date, screen_date,
        screen_date, screen_date,
        screen_date,
        MIN_CLOSE, MIN_AVG_VOL,
        MIN_PE, MAX_PE, MIN_ROE, MAX_DER, MIN_NPM,
        MIN_RANGE_90D,
    )
    rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


# ═══════════════════════════════════════════════════════════════════════════════
# SCORING
# ═══════════════════════════════════════════════════════════════════════════════

def _safe_float(val, default=0.0) -> float:
    if val is None: return default
    try:
        f = float(val)
        return default if math.isnan(f) or math.isinf(f) else f
    except (ValueError, TypeError): return default

def _safe_int(val, default=0) -> int:
    if val is None: return default
    try: return int(val)
    except (ValueError, TypeError): return default

def _normalize_log(value: float, floor: float, ceiling: float) -> float:
    if value <= floor: return 0.0
    if value >= ceiling: return 100.0
    return ((math.log(value) - math.log(floor)) / (math.log(ceiling) - math.log(floor))) * 100.0

def _normalize_linear(value: float, floor: float, ceiling: float) -> float:
    if value <= floor: return 0.0
    if value >= ceiling: return 100.0
    return ((value - floor) / (ceiling - floor)) * 100.0

def _proximity_score(value: float, target: float, tolerance_pct: float = 50.0) -> float:
    if target == 0: return 0.0
    pct_diff = abs(value - target) / abs(target) * 100.0
    if pct_diff >= tolerance_pct: return 0.0
    return max(0.0, 100.0 * (1.0 - (pct_diff / tolerance_pct) ** 1.5))


def score_stock(row: dict) -> dict:
    """Score on 4 dimensions: Liquidity, Fundamentals, Viability, Similarity."""
    avg_vol = _safe_float(row.get("avg_vol_20d"), 0)
    vol_ratio = _safe_float(row.get("vol_ratio"), 0)
    close = _safe_float(row.get("close"), 0)
    pe = _safe_float(row.get("pe_ttm"), -1)
    pbv = _safe_float(row.get("pbv"), -1)
    roe = _safe_float(row.get("roe"), -999)
    npm = _safe_float(row.get("npm"), -999)
    der = _safe_float(row.get("der"), 0)
    in_idx30 = _safe_int(row.get("in_idx30"), 0)
    in_lq45 = _safe_int(row.get("in_lq45"), 0)
    in_idx80 = _safe_int(row.get("in_idx80"), 0)
    wf_best_return = _safe_float(row.get("wf_best_return"), 0)
    wf_positive_count = _safe_int(row.get("wf_positive_count"), 0)
    wf_total_strategies = _safe_int(row.get("wf_total_strategies"), 10)
    wf_top_consistency = _safe_float(row.get("wf_top_consistency"), 0)
    range_90d = _safe_float(row.get("range_90d_pct"), 0)
    vr_exceed_1_3 = _safe_int(row.get("vr_exceed_1_3"), 0)
    vr_exceed_1_8 = _safe_int(row.get("vr_exceed_1_8"), 0)
    vr_max_60d = _safe_float(row.get("vr_max_60d"), 0)
    regime = row.get("regime") or ""

    # 1. LIQUIDITY (25%)
    vol_score = _normalize_log(avg_vol, 50_000_000, 2_000_000_000)
    if vol_ratio <= 0: vr_score = 0
    elif vol_ratio < 0.5: vr_score = vol_ratio / 0.5 * 40
    elif vol_ratio <= 2.0: vr_score = 40 + (vol_ratio - 0.5) / 1.5 * 50
    elif vol_ratio <= 5.0: vr_score = max(0, 90 - (vol_ratio - 2.0) / 3.0 * 50)
    else: vr_score = max(0, 40 - (vol_ratio - 5.0) / 10.0 * 40)
    idx_bonus = 100 if in_idx30 else (75 if in_lq45 else (40 if in_idx80 else 0))
    price_score = _normalize_log(close, 200, 10_000)
    liquidity = vol_score * 0.40 + vr_score * 0.15 + idx_bonus * 0.25 + price_score * 0.20

    # 2. FUNDAMENTALS (15%)
    if pe <= 0: pe_score = 0
    elif pe < 5: pe_score = pe / 5 * 50
    elif pe <= 20: pe_score = 50 + (pe - 5) / 15 * 50
    elif pe <= 50: pe_score = max(0, 100 - (pe - 20) / 30 * 100)
    else: pe_score = 0
    roe_score = min(100.0, max(0.0, roe * 4)) if roe > -900 else 0
    if npm <= -900: npm_score = 50
    elif npm < 0: npm_score = max(0, 30 + npm * 3)
    elif npm <= 20: npm_score = 30 + npm / 20 * 70
    else: npm_score = 100
    if der <= 0: der_score = 60
    elif der <= 2: der_score = 60 + (2 - der) / 2 * 40
    elif der <= 5: der_score = max(0, 60 - (der - 2) / 3 * 60)
    else: der_score = max(0, 0 - (der - 5) / 15 * 20)
    fundamentals = pe_score * 0.30 + roe_score * 0.30 + npm_score * 0.20 + der_score * 0.20

    # 3. TRADING VIABILITY (40%)
    range_score = _normalize_log(range_90d, 25, 120)
    wf_profit_ratio = wf_positive_count / max(wf_total_strategies, 1)
    if wf_best_return <= -1: wf_return_score = 0
    elif wf_best_return <= 0: wf_return_score = (wf_best_return + 1) * 25
    elif wf_best_return <= 1: wf_return_score = 25 + wf_best_return * 25
    elif wf_best_return <= 2: wf_return_score = 50 + (wf_best_return - 1) * 25
    elif wf_best_return <= 4: wf_return_score = 75 + (wf_best_return - 2) / 2 * 25
    else: wf_return_score = 100
    wf_consistency_score = min(100.0, wf_top_consistency * 1.33)
    wf_profit_score = wf_profit_ratio * 100 * 0.30 + wf_return_score * 0.45 + wf_consistency_score * 0.25

    vr_trigger_ratio = vr_exceed_1_3 / 60.0
    vr_trigger_score = min(100.0, vr_trigger_ratio * 100 * 5)
    if vr_max_60d < 1.3: vr_trigger_score *= 0.3
    elif vr_max_60d < 1.8: vr_trigger_score *= 0.7

    regime_upper = (regime or "").upper()
    if "TRENDING" in regime_upper: adx_score = 100
    elif "SIDEWAYS" in regime_upper: adx_score = 15
    elif "VOLATILE" in regime_upper: adx_score = 70
    elif "BULL" in regime_upper: adx_score = 85
    elif "BEAR" in regime_upper: adx_score = 30
    else: adx_score = 50

    viability = (range_score * W_RANGE + wf_profit_score * W_WF_PROFIT +
                 vr_trigger_score * W_VR_TRIGGER + adx_score * W_ADX_PROFILE)

    # 4. PROFILE SIMILARITY (20%)
    pe_sim = _proximity_score(pe, BRPT_PROFILE["pe_ttm"], 80) if pe > 0 else 0
    pbv_sim = _proximity_score(pbv, BRPT_PROFILE["pbv"], 80) if pbv > 0 else 50
    roe_sim = _proximity_score(roe, BRPT_PROFILE["roe"], 80) if roe > -900 else 50
    der_sim = _proximity_score(der, BRPT_PROFILE["der"], 80) if der > 0 else 50
    if 1_000 <= close <= 3_000: price_in_range = 100.0
    elif 500 <= close <= 5_000: price_in_range = 65.0
    elif close > 5_000: price_in_range = 35.0
    else: price_in_range = max(0, close / 500 * 50)
    if range_90d >= 60 and range_90d <= 200:
        range_sim = max(20, 100.0 - abs(range_90d - BRPT_PROFILE["range_90d_pct"]) / 100 * 50)
    elif range_90d > 30: range_sim = 40.0
    else: range_sim = max(0, range_90d / 30 * 40)
    mcap_sim = 100.0 if in_idx30 else (85.0 if in_lq45 else (60.0 if in_idx80 else 30.0))
    similarity = (pe_sim * 0.15 + pbv_sim * 0.10 + roe_sim * 0.10 + der_sim * 0.05 +
                  price_in_range * 0.25 + range_sim * 0.20 + mcap_sim * 0.15)

    # COMPOSITE
    composite = (liquidity * W_LIQUIDITY + fundamentals * W_FUNDAMENTALS +
                 viability * W_VIABILITY + similarity * W_SIMILARITY)
    crash_penalty = min(15.0, (vol_ratio - 3.0) * 3.0) if vol_ratio > 3.0 and close > 0 else 0.0
    composite -= crash_penalty

    # VERDICT
    if row["ticker"] == "BBCA":
        verdict = "❌ BLUE-CHIP HOLD (not for BRPT strats)"
    elif viability < 25: verdict = "❌ UNTRADEABLE"
    elif viability < 45: verdict = "⚠️ MARGINAL"
    elif viability < 65: verdict = "✅ VIABLE"
    else: verdict = "🔥 STRONG"

    return {
        "ticker": row["ticker"], "composite": round(composite, 1),
        "liquidity": round(liquidity, 1), "fundamentals": round(fundamentals, 1),
        "viability": round(viability, 1), "similarity": round(similarity, 1),
        "verdict": verdict,
        "range_score": round(range_score, 1), "wf_profit_score": round(wf_profit_score, 1),
        "close": row.get("close"), "avg_vol_20d": row.get("avg_vol_20d"),
        "vol_ratio": row.get("vol_ratio"), "range_90d_pct": round(range_90d, 1) if range_90d else None,
        "wf_best_return": round(wf_best_return, 2) if wf_best_return else None,
        "wf_positive_count": wf_positive_count, "wf_total_strategies": wf_total_strategies,
        "wf_best_strategy": row.get("wf_best_strategy"),
        "vr_exceed_1_3": vr_exceed_1_3, "vr_exceed_1_8": vr_exceed_1_8,
        "pe_ttm": row.get("pe_ttm"), "pbv": row.get("pbv"),
        "roe": row.get("roe"), "npm": row.get("npm"), "der": row.get("der"),
        "market_cap": row.get("market_cap"), "in_idx30": row.get("in_idx30"),
        "in_lq45": row.get("in_lq45"), "regime": row.get("regime"),
        "bt_best_strategy": row.get("bt_best_strategy"),
        "flow_verdict": row.get("flow_verdict"),
        "signal": row.get("signal"), "consec_up": row.get("consec_up"),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN FILTER
# ═══════════════════════════════════════════════════════════════════════════════

def run_filter(screen_date: str = None, top_n: int = 20) -> list[dict]:
    conn = _get_conn()
    try:
        if screen_date is None:
            screen_date = _latest_screen_date(conn)
            if not screen_date:
                print("[brpt_filter] No daily_screen data found.", file=sys.stderr)
                return []
        print(f"[brpt_filter] Scanning {screen_date} for stocks comparable to BRPT...", file=sys.stderr)
        universe = fetch_universe(conn, screen_date)
        print(f"[brpt_filter] Universe after hard filters: {len(universe)} tickers", file=sys.stderr)
        scored = [score_stock(row) for row in universe]
        scored.sort(key=lambda x: x["composite"], reverse=True)
        for s in scored:
            if s["ticker"] == "BRPT":
                s["is_brpt"] = True
        return scored[:top_n]
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# OUTPUT FORMATTERS
# ═══════════════════════════════════════════════════════════════════════════════

def format_table(results: list[dict]) -> str:
    if not results: return "No results found."
    header = (
        f"{'#':>3} {'Ticker':<8} {'Comp':>6} {'Liq':>5} {'Fund':>5} {'Viab':>5} {'Sim':>5} "
        f"{'Close':>8} {'AvgVol20D':>14} {'VR':>5} "
        f"{'Rng90D%':>8} {'WF Best%':>8} {'WF+':>4} {'PE':>7} {'Verdict'}"
    )
    sep = "-" * len(header)
    lines = [header, sep]
    for i, r in enumerate(results, 1):
        marker = "→" if r.get("is_brpt") else " "
        close_str = f"{r['close']:>8,}" if r['close'] else "       -"
        vol_str = f"{r['avg_vol_20d']:>14,}" if r['avg_vol_20d'] else "             -"
        vr_str = f"{r['vol_ratio']:>5.1f}" if r['vol_ratio'] else "    -"
        rng_str = f"{r['range_90d_pct']:>8.1f}" if r['range_90d_pct'] else "       -"
        wf_str = f"{r['wf_best_return']:>8.2f}" if r['wf_best_return'] is not None else "       -"
        wfp_str = f"{r['wf_positive_count']}/{r['wf_total_strategies']}" if r.get('wf_total_strategies') else "  -"
        pe_str = f"{r['pe_ttm']:>7.1f}" if r['pe_ttm'] else "      -"
        lines.append(
            f"{marker}{i:>2} {r['ticker']:<8} {r['composite']:>6.1f} {r['liquidity']:>5.1f} "
            f"{r['fundamentals']:>5.1f} {r['viability']:>5.1f} {r['similarity']:>5.1f} "
            f"{close_str} {vol_str} {vr_str} {rng_str} {wf_str} {wfp_str:>4} {pe_str} {r.get('verdict','-')}"
        )
    return "\n".join(lines)


def format_categorized(results: list[dict]) -> str:
    if not results: return "No results found."
    categories = {}
    for r in results:
        v = r.get('verdict', 'UNKNOWN')
        categories.setdefault(v, []).append(r)
    order = ['🔥 STRONG', '✅ VIABLE', '⚠️ MARGINAL', '❌ UNTRADEABLE',
             '❌ BLUE-CHIP HOLD (not for BRPT strats)']
    lines = ["=" * 95, "BRPT COMPARABLE STOCKS — CATEGORIZED BY VERDICT", "=" * 95]
    for cat in order:
        stocks = categories.get(cat, [])
        if not stocks: continue
        lines.extend(["", "─" * 95, f"  {cat}  ({len(stocks)} stocks)", "─" * 95])
        lines.append(f"{'#':>3} {'Ticker':<8} {'Comp':>6} {'Viab':>5} {'Liq':>5} {'Fund':>5} {'Sim':>5} "
                     f"{'Close':>8} {'AvgVol20D':>13} {'Rng90%':>7} {'WF Best':>8} {'WF+/Tot':>7} {'PE':>6}")
        lines.append("-" * 95)
        for i, r in enumerate(stocks, 1):
            marker = "→" if r.get('is_brpt') else " "
            close_str = f"{r['close']:>8,}" if r['close'] else "       -"
            vol_str = f"{r['avg_vol_20d']:>13,.0f}" if r['avg_vol_20d'] else "            -"
            rng_str = f"{r['range_90d_pct']:>7.1f}" if r['range_90d_pct'] else "      -"
            wf_str = f"{r['wf_best_return']:>8.2f}" if r['wf_best_return'] is not None else "       -"
            wfp_str = f"{r['wf_positive_count']}/{r['wf_total_strategies']}" if r.get('wf_total_strategies') else "  -  "
            pe_str = f"{r['pe_ttm']:>6.1f}" if r['pe_ttm'] else "     -"
            lines.append(f"{marker}{i:>2} {r['ticker']:<8} {r['composite']:>6.1f} {r['viability']:>5.1f} "
                         f"{r['liquidity']:>5.1f} {r['fundamentals']:>5.1f} {r['similarity']:>5.1f} "
                         f"{close_str} {vol_str} {rng_str} {wf_str} {wfp_str:>7} {pe_str}")
    n_strong = len(categories.get('🔥 STRONG', []))
    n_viable = len(categories.get('✅ VIABLE', []))
    n_marginal = len(categories.get('⚠️ MARGINAL', []))
    n_untradeable = len(categories.get('❌ UNTRADEABLE', []))
    n_bbca = len(categories.get('❌ BLUE-CHIP HOLD (not for BRPT strats)', []))
    lines.extend(["", "=" * 95])
    lines.append(f"SUMMARY: {len(results)} total | 🔥 STRONG: {n_strong} | ✅ VIABLE: {n_viable} | "
                 f"⚠️ MARGINAL: {n_marginal} | ❌ UNTRADEABLE: {n_untradeable} | BBCA-HOLD: {n_bbca}")
    lines.append(f"FOCUS: {n_strong + n_viable} tradeable stocks (STRONG + VIABLE)")
    return "\n".join(lines)


def format_json(results: list[dict]) -> str:
    return json.dumps({
        "generated": dt_date.today().isoformat(),
        "reference_ticker": "BRPT", "reference_profile": BRPT_PROFILE,
        "scoring_weights": {"liquidity": W_LIQUIDITY, "fundamentals": W_FUNDAMENTALS,
                            "viability": W_VIABILITY, "similarity": W_SIMILARITY},
        "count": len(results), "results": results,
    }, indent=2, default=str)


def export_csv(results: list[dict], filepath: str):
    if not results: print("No results to export."); return
    fieldnames = ["ticker","composite","liquidity","fundamentals","viability","similarity",
                  "verdict","close","avg_vol_20d","vol_ratio","range_90d_pct",
                  "wf_best_return","wf_positive_count","wf_total_strategies","wf_best_strategy",
                  "vr_exceed_1_3","vr_exceed_1_8","pe_ttm","pbv","roe","npm","der",
                  "market_cap","in_idx30","in_lq45","regime","bt_best_strategy",
                  "flow_verdict","signal","consec_up"]
    with open(filepath, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader(); w.writerows(results)
    print(f"Exported {len(results)} rows to {filepath}")


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

VERDICT_FILTER_MAP = {
    "strong": "🔥 STRONG",
    "viable": "✅ VIABLE",
    "marginal": "⚠️ MARGINAL",
    "untradeable": "❌ UNTRADEABLE",
    "tradeable": ["🔥 STRONG", "✅ VIABLE"],
}


def main():
    import argparse
    p = argparse.ArgumentParser(description="BRPT Comparable Stock Filter")
    p.add_argument("--top", type=int, default=20)
    p.add_argument("--date", type=str, default=None)
    p.add_argument("--json", action="store_true")
    p.add_argument("--export", type=str, default=None, metavar="FILE.csv")
    p.add_argument("--all", action="store_true")
    p.add_argument("--categorized", action="store_true", help="Group by verdict")
    p.add_argument("--verdict", type=str, default=None,
                   choices=["strong","viable","marginal","untradeable","tradeable"],
                   help="Filter by verdict (tradeable=strong+viable)")
    args = p.parse_args()

    top_n = 9999 if args.all else args.top
    results = run_filter(screen_date=args.date, top_n=top_n)

    if args.verdict:
        target = VERDICT_FILTER_MAP[args.verdict]
        if isinstance(target, list):
            results = [r for r in results if r.get('verdict') in target]
        else:
            results = [r for r in results if r.get('verdict') == target]

    if args.json: print(format_json(results))
    elif args.export:
        export_csv(results, args.export)
        print(format_categorized(results[:min(len(results), 50)]) if args.categorized
              else format_table(results[:min(len(results), 30)]))
    elif args.categorized: print(format_categorized(results))
    else:
        print(format_table(results))
        print(f"\nTotal comparable stocks found: {len(results)}")
        brpt_result = next((r for r in results if r["ticker"] == "BRPT"), None)
        if brpt_result:
            print(f"BRPT reference: Comp={brpt_result['composite']:.1f} "
                  f"(Liq={brpt_result['liquidity']:.1f}, Fund={brpt_result['fundamentals']:.1f}, "
                  f"Viab={brpt_result['viability']:.1f}, Sim={brpt_result['similarity']:.1f})")


if __name__ == "__main__":
    main()
