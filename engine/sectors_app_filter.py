"""
sectors_app_filter.py — Consumer for sectors.app scraped data.
==============================================================
Reads sectors_index_perf / sectors_sector_perf / sectors_dividend_calendar
tables (populated by sectors_fetcher.py) and exposes regime checks the
walkforward engine can consult before opening positions.

This module is purely additive — it does NOT modify engine/sector_rotation.py
or any existing logic. Combine it with the internal scorer via
combined_sector_verdict() when both opinions should agree.

Usage:
    from engine.sectors_app_filter import (
        latest_sector_regime,
        is_sector_hot,
        is_sector_collapsing,
        ex_dividend_window,
        combined_sector_verdict,
    )

    if combined_sector_verdict("TLKM")[0]:
        # both internal score AND sectors.app agree → trade allowed
        ...
"""

import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

from config import DB_PATH

# sectors.app sector label → internal sector_rotation label
SECTORS_APP_TO_INTERNAL: Dict[str, str] = {
    "Banks":                          "Financials",
    "Basic Materials":                "BasicMaterials",
    "Oil, Gas & Coal":                "Energy",
    "Telecommunication":              "Telecom",
    "Food & Beverage":                "ConsumerNCyclical",
    "Software & IT Services":         "Technology",
    "Utilities":                      "Infrastructure",
    "Properties & Real Estate":       "Property",
    "Healthcare Equipment & Provide": "Healthcare",  # truncated label in DB
    "Healthcare Equipment & Providers": "Healthcare",
    "Holding & Investment Companies": "HoldingInvestment",  # no internal peer
}

# Thresholds (in percent)
HOT_30D_PCT       = 10.0   # sector return ≥ +10% over 30d → hot
COLLAPSE_30D_PCT  = -15.0  # sector return ≤ -15% over 30d → collapsing
EX_DIV_BEFORE     = 2      # days before ex-date to flag
EX_DIV_AFTER      = 1      # days after ex-date to flag


# ── DB helpers ─────────────────────────────────────────────────────────

def _conn() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH)


def _latest_fetch_date(conn: sqlite3.Connection, table: str) -> Optional[str]:
    row = conn.execute(f"SELECT MAX(fetch_date) FROM {table}").fetchone()
    return row[0] if row else None


# ── Sector regime ──────────────────────────────────────────────────────

def latest_sector_regime() -> Dict[str, Dict]:
    """
    Returns the most recent sector snapshot from sectors.app, keyed by
    INTERNAL sector name (so it lines up with engine/sector_rotation.py).

    Each value: {market_cap_t, chg_1d, chg_7d, chg_30d, chg_90d, chg_1y,
                 chg_ytd, fetch_date, sectors_app_name}.
    """
    out: Dict[str, Dict] = {}
    with _conn() as conn:
        latest = _latest_fetch_date(conn, "sectors_sector_perf")
        if not latest:
            return out
        rows = conn.execute(
            """SELECT sector, market_cap_idr_t, chg_1d, chg_7d, chg_30d,
                      chg_90d, chg_1y, chg_ytd
               FROM sectors_sector_perf WHERE fetch_date=?""",
            (latest,),
        ).fetchall()
    for sa_name, mc, c1, c7, c30, c90, c1y, cytd in rows:
        internal = SECTORS_APP_TO_INTERNAL.get(sa_name, sa_name)
        out[internal] = {
            "market_cap_t":     mc,
            "chg_1d":           c1,
            "chg_7d":           c7,
            "chg_30d":          c30,
            "chg_90d":          c90,
            "chg_1y":           c1y,
            "chg_ytd":          cytd,
            "fetch_date":       latest,
            "sectors_app_name": sa_name,
        }
    return out


def _lookup_sector(internal_sector: str) -> Optional[Dict]:
    return latest_sector_regime().get(internal_sector)


def is_sector_hot(internal_sector: str, period: str = "30d",
                  threshold: float = HOT_30D_PCT) -> bool:
    """True iff the sector return over `period` is ≥ threshold (pct)."""
    s = _lookup_sector(internal_sector)
    if not s:
        return False
    val = s.get(f"chg_{period}")
    return val is not None and val >= threshold


def is_sector_collapsing(internal_sector: str, period: str = "30d",
                         threshold: float = COLLAPSE_30D_PCT) -> bool:
    """True iff the sector return over `period` is ≤ threshold (pct, negative)."""
    s = _lookup_sector(internal_sector)
    if not s:
        return False
    val = s.get(f"chg_{period}")
    return val is not None and val <= threshold


# ── Index regime ──────────────────────────────────────────────────────

def latest_index_perf(index_code: str) -> Optional[Dict]:
    """Most recent snapshot for a named index (IHSG, LQ45, IDX30, ...)."""
    with _conn() as conn:
        latest = _latest_fetch_date(conn, "sectors_index_perf")
        if not latest:
            return None
        row = conn.execute(
            """SELECT level,chg_1d,chg_7d,chg_30d,chg_90d,chg_1y,chg_ytd,category
               FROM sectors_index_perf WHERE fetch_date=? AND index_code=?""",
            (latest, index_code.upper()),
        ).fetchone()
    if not row:
        return None
    lvl, c1, c7, c30, c90, c1y, cytd, cat = row
    return {
        "level": lvl, "chg_1d": c1, "chg_7d": c7, "chg_30d": c30,
        "chg_90d": c90, "chg_1y": c1y, "chg_ytd": cytd,
        "category": cat, "fetch_date": latest,
    }


# ── Dividend window ───────────────────────────────────────────────────

def ex_dividend_window(ticker: str, on: Optional[str] = None,
                       days_before: int = EX_DIV_BEFORE,
                       days_after: int = EX_DIV_AFTER) -> Optional[Dict]:
    """
    Returns the dividend record if `on` (default today) falls within
    [ex_date − days_before, ex_date + days_after]; else None.
    Use to skip entries that would be polluted by ex-div gap-down.
    """
    today = on or datetime.now().strftime("%Y-%m-%d")
    today_dt = datetime.strptime(today, "%Y-%m-%d")
    with _conn() as conn:
        rows = conn.execute(
            """SELECT ex_date, payment_date, dividend_idr, yield_pct
               FROM sectors_dividend_calendar
               WHERE ticker=? AND ex_date IS NOT NULL""",
            (ticker.upper(),),
        ).fetchall()
    for ex_date, pay_date, div, yld in rows:
        try:
            ex_dt = datetime.strptime(ex_date, "%Y-%m-%d")
        except ValueError:
            continue
        if (ex_dt - timedelta(days=days_before)) <= today_dt <= (ex_dt + timedelta(days=days_after)):
            return {
                "ticker":       ticker.upper(),
                "ex_date":      ex_date,
                "payment_date": pay_date,
                "dividend_idr": div,
                "yield_pct":    yld,
            }
    return None


# ── Combined verdict ──────────────────────────────────────────────────

def combined_sector_verdict(ticker: str, scored=None) -> Tuple[bool, str]:
    """
    Combines engine.sector_rotation (internal scoring from local OHLCV)
    with sectors.app's 30d performance. Both must agree to greenlight.

    Pass `scored` (the list returned by engine.sector_rotation.score_sectors)
    to reuse a precomputed snapshot — important when called inside a
    per-ticker loop, since score_sectors() touches the OHLCV table.

    Returns (tradeable, reason).
    """
    # Lazy import to avoid heavy deps at module load
    try:
        from engine.sector_rotation import is_sector_tradeable, get_ticker_sector
    except Exception as e:
        return True, f"internal scorer unavailable ({e})"

    internal_ok, internal_reason = is_sector_tradeable(ticker, scored)
    sector = get_ticker_sector(ticker)
    if sector == "Unknown":
        return internal_ok, f"internal:{internal_reason} | sectors.app:no sector mapping"

    sa = _lookup_sector(sector)
    if not sa:
        return internal_ok, f"internal:{internal_reason} | sectors.app:no data for {sector}"

    chg30 = sa.get("chg_30d")
    sa_ok = chg30 is None or chg30 > COLLAPSE_30D_PCT

    tradeable = internal_ok and sa_ok
    reason = (
        f"internal:{internal_reason} | "
        f"sectors.app:{sector} 30d={chg30:+.2f}%" if chg30 is not None
        else f"internal:{internal_reason} | sectors.app:{sector} 30d=n/a"
    )
    if not sa_ok:
        reason += f" (≤ {COLLAPSE_30D_PCT}% → BLOCKED)"
    return tradeable, reason


# ── CLI ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import json, sys

    cmd = sys.argv[1] if len(sys.argv) > 1 else "regime"

    if cmd == "regime":
        regime = latest_sector_regime()
        for k, v in sorted(regime.items(), key=lambda x: -(x[1].get("chg_30d") or -999)):
            print(f"{k:<22} 30d={v.get('chg_30d'):+7.2f}%  1y={v.get('chg_1y'):+7.2f}%  "
                  f"YTD={v.get('chg_ytd'):+7.2f}%  mcap={v.get('market_cap_t'):,.0f}T")

    elif cmd == "verdict" and len(sys.argv) > 2:
        for tkr in sys.argv[2:]:
            ok, reason = combined_sector_verdict(tkr)
            verdict = "✓ TRADE" if ok else "✗ BLOCK"
            print(f"{tkr:<6} {verdict}  {reason}")

    elif cmd == "exdiv" and len(sys.argv) > 2:
        for tkr in sys.argv[2:]:
            window = ex_dividend_window(tkr)
            print(f"{tkr:<6} {json.dumps(window) if window else 'no upcoming ex-div'}")

    elif cmd == "index" and len(sys.argv) > 2:
        for idx in sys.argv[2:]:
            data = latest_index_perf(idx)
            print(f"{idx:<12} {json.dumps(data) if data else 'not found'}")

    else:
        print("Usage:")
        print("  python -m engine.sectors_app_filter regime")
        print("  python -m engine.sectors_app_filter verdict BBCA TLKM BREN")
        print("  python -m engine.sectors_app_filter exdiv BMRI BJBR ASII")
        print("  python -m engine.sectors_app_filter index IHSG LQ45 IDXBUMN20")
