"""Phase A: IDX80 Stockbit flow descriptive study.

Purpose: establish what stockbit_flow_bars actually looks like for the
point-in-time IDX80 universe (research.idx80_membership) -- coverage,
distribution, data-quality -- before any predictive (Phase B+) work.
Read-only: never writes to any table.

Universe: research.idx80_membership.idx80_universe_as_of(), resolved once
per reconstitution period (membership is constant within a period). Default
tier="reconstructed" (PRIMARY_VERIFIED + BRACKETED_RECONSTRUCTED +
CROSS_VALIDATED). P2 (2025-05-02..2025-07-31, confidence=UNRESOLVED) always
resolves to an empty universe under both "strict" and "reconstructed" and is
therefore always excluded -- this module never uses
members_as_of_all_evidence() and never reads idx_tickers.in_idx80.

stockbit_flow_bars column semantics (from stockbit_fetcher.py / flow_filter.py
_parse_bars() -- verified against the live DB: BBCA 2025-03-03's last bar has
buy_lot=1,120,303 + sell_lot=809,140; at 100 shares/lot that is exactly that
day's OHLCV volume of 192,944,300 shares):

  - buy_lot / sell_lot : CUMULATIVE running totals through the trading day.
                         The daily value is MAX() across the day's bars,
                         never SUM() (summing would overcount by ~n_bars x).
  - net_value          : a genuine PER-BAR net transaction value (bounces
                         positive/negative minute to minute). The daily
                         value is SUM() across the day's bars.
  - delta = buy_lot - sell_lot, stored per bar; since buy_lot/sell_lot are
    cumulative, delta is cumulative too and is not summed either (this
    module derives buy_minus_sell itself from the daily MAX values).
  - n_bars             : a coverage/data-quality diagnostic, not a feature.

Research hygiene: every feature here is dated T (the trading day the flow
was observed) with no forward return of any kind -- Phase A is descriptive
only. OHLCV is read via the finalized-only convention (COALESCE(is_final,1)=1,
matching data.loaders.load_ohlcv_df's filter) for the flow-intensity feature.
"""
from __future__ import annotations

from typing import Dict, Sequence, Tuple

import pandas as pd

from research.idx80_membership import RECONSTRUCTED, idx80_universe_as_of

FEATURE_COLS = [
    "buy_lot", "sell_lot", "buy_minus_sell", "imbalance",
    "total_flow_lots", "net_value", "flow_intensity",
]
QUANTILES = (0.05, 0.25, 0.5, 0.75, 0.95)

PANEL_COLUMNS = [
    "period_label", "ticker", "trade_date", "buy_lot", "sell_lot", "net_value",
    "n_bars", "buy_minus_sell", "total_flow_lots", "imbalance", "zero_activity",
    "ohlcv_volume", "flow_intensity",
]


def _flow_data_bound(conn) -> str:
    """Latest trade_date actually present in stockbit_flow_bars -- the
    data-driven cap used for an open-ended period's effective_to (e.g. P7),
    never the system clock / 'today'."""
    row = conn.execute("SELECT MAX(trade_date) FROM stockbit_flow_bars").fetchone()
    return row[0]


def resolve_periods(conn, tier: str = RECONSTRUCTED) -> list:
    """Every idx80_reconstitution_periods row, each with its resolved PIT
    universe under `tier` and an explicit `included` flag.

    A period is included iff its universe is non-empty under `tier`.
    UNRESOLVED periods (P2) resolve to an empty universe under every
    members_as_of() tier and are therefore always excluded -- but they are
    still returned here (included=False) so callers report them explicitly
    rather than silently dropping them from any listing.
    """
    bound = _flow_data_bound(conn)
    rows = conn.execute(
        "SELECT period_label, effective_from, effective_to, confidence "
        "FROM idx80_reconstitution_periods ORDER BY effective_from"
    ).fetchall()
    out = []
    for label, eff_from, eff_to, confidence in rows:
        universe = idx80_universe_as_of(conn, eff_from, tier)
        out.append({
            "period_label": label,
            "effective_from": eff_from,
            "effective_to": eff_to or bound,
            "confidence": confidence,
            "included": bool(universe),
            "universe": universe,
        })
    return out


def _daily_flow_aggregates(conn, tickers: Sequence[str], date_from: str, date_to: str) -> pd.DataFrame:
    """Raw per-(ticker, trade_date) aggregation of stockbit_flow_bars.

    buy_lot/sell_lot -> MAX (cumulative counters); net_value -> SUM (per-bar
    value); n_bars -> COUNT (coverage diagnostic). See module docstring.
    """
    cols = ["ticker", "trade_date", "buy_lot", "sell_lot", "net_value", "n_bars"]
    if not tickers:
        return pd.DataFrame(columns=cols)
    placeholders = ",".join("?" for _ in tickers)
    df = pd.read_sql(
        f"SELECT ticker, trade_date, MAX(buy_lot) AS buy_lot, MAX(sell_lot) AS sell_lot, "
        f"SUM(net_value) AS net_value, COUNT(*) AS n_bars "
        f"FROM stockbit_flow_bars "
        f"WHERE ticker IN ({placeholders}) AND trade_date >= ? AND trade_date <= ? "
        f"GROUP BY ticker, trade_date",
        conn, params=(*tickers, date_from, date_to),
    )
    return df[cols]


def _add_derived_features(df: pd.DataFrame) -> pd.DataFrame:
    """buy_minus_sell, total_flow_lots, imbalance (in [-1,1], NaN when the
    day had zero total flow -- 0/0 is undefined, not 0), zero_activity flag."""
    df = df.copy()
    df["buy_minus_sell"] = df["buy_lot"] - df["sell_lot"]
    df["total_flow_lots"] = df["buy_lot"] + df["sell_lot"]
    denom = df["total_flow_lots"].astype(float).replace(0.0, pd.NA)
    df["imbalance"] = df["buy_minus_sell"].astype(float) / denom
    df["zero_activity"] = (df["buy_lot"] == 0) & (df["sell_lot"] == 0)
    return df


def _attach_ohlcv_volume(conn, df: pd.DataFrame) -> pd.DataFrame:
    """Left-join finalized OHLCV volume (COALESCE(is_final,1)=1, matching
    data.loaders.load_ohlcv_df's filter) for the flow-intensity feature.

    flow_intensity is left NaN (never 0) whenever finalized volume is
    missing or zero -- "where valid" per the Phase A spec; it must never be
    silently treated as zero flow-vs-volume.
    """
    if df.empty:
        df = df.copy()
        df["ohlcv_volume"] = pd.Series(dtype=float)
        df["flow_intensity"] = pd.Series(dtype=float)
        return df
    tickers = tuple(df["ticker"].unique())
    lo, hi = df["trade_date"].min(), df["trade_date"].max()
    placeholders = ",".join("?" for _ in tickers)
    vol = pd.read_sql(
        f"SELECT ticker, date AS trade_date, volume AS ohlcv_volume FROM ohlcv "
        f"WHERE COALESCE(is_final,1)=1 AND ticker IN ({placeholders}) "
        f"AND date >= ? AND date <= ?",
        conn, params=(*tickers, lo, hi),
    )
    merged = df.merge(vol, on=["ticker", "trade_date"], how="left")
    valid = merged["ohlcv_volume"].notna() & (merged["ohlcv_volume"] > 0)
    merged["flow_intensity"] = pd.NA
    merged.loc[valid, "flow_intensity"] = (
        (merged.loc[valid, "total_flow_lots"] * 100) / merged.loc[valid, "ohlcv_volume"]
    ).astype(float)
    merged["flow_intensity"] = pd.to_numeric(merged["flow_intensity"], errors="coerce")
    return merged


def build_flow_panel(conn, tier: str = RECONSTRUCTED) -> pd.DataFrame:
    """One row per (period_label, ticker, trade_date) with daily flow
    features for the PIT IDX80 universe. P2 (and any other UNRESOLVED-only
    period) contributes zero rows. Deterministic: sorted by
    (period_label, ticker, trade_date)."""
    frames = []
    for p in resolve_periods(conn, tier):
        if not p["included"]:
            continue
        raw = _daily_flow_aggregates(conn, p["universe"], p["effective_from"], p["effective_to"])
        if raw.empty:
            continue
        raw = raw.copy()
        raw["period_label"] = p["period_label"]
        frames.append(raw)
    if not frames:
        return pd.DataFrame(columns=PANEL_COLUMNS)
    panel = pd.concat(frames, ignore_index=True)
    panel = _add_derived_features(panel)
    panel = _attach_ohlcv_volume(conn, panel)
    panel = panel[PANEL_COLUMNS]
    return panel.sort_values(["period_label", "ticker", "trade_date"]).reset_index(drop=True)


def coverage_audit(conn, tier: str = RECONSTRUCTED) -> pd.DataFrame:
    """One row per reconstitution period (including excluded ones, e.g. P2 --
    reported explicitly, never silently dropped) with:

    universe_size, trading_days (from trading_calendar within the period's
    window), expected_ticker_days (universe_size x trading_days),
    available_ticker_days (>=1 flow bar), missing_ticker_days, coverage_pct,
    zero_activity_ticker_days, and bar-row-count diagnostics (min/mean/max
    n_bars across available ticker-days).
    """
    rows = []
    for p in resolve_periods(conn, tier):
        label, eff_from, eff_to = p["period_label"], p["effective_from"], p["effective_to"]
        universe = p["universe"]
        n_universe = len(universe)
        if not p["included"]:
            rows.append({
                "period_label": label, "confidence": p["confidence"], "included": False,
                "universe_size": 0, "trading_days": 0, "expected_ticker_days": 0,
                "available_ticker_days": 0, "missing_ticker_days": 0, "coverage_pct": None,
                "zero_activity_ticker_days": 0,
                "min_n_bars": None, "mean_n_bars": None, "max_n_bars": None,
            })
            continue
        n_days = conn.execute(
            "SELECT COUNT(*) FROM trading_calendar WHERE date >= ? AND date <= ?",
            (eff_from, eff_to),
        ).fetchone()[0]
        expected = n_universe * n_days
        raw = _daily_flow_aggregates(conn, universe, eff_from, eff_to)
        available = len(raw)
        zero_activity = int(((raw["buy_lot"] == 0) & (raw["sell_lot"] == 0)).sum()) if available else 0
        rows.append({
            "period_label": label, "confidence": p["confidence"], "included": True,
            "universe_size": n_universe, "trading_days": n_days,
            "expected_ticker_days": expected, "available_ticker_days": available,
            "missing_ticker_days": expected - available,
            "coverage_pct": round(100.0 * available / expected, 2) if expected else None,
            "zero_activity_ticker_days": zero_activity,
            "min_n_bars": int(raw["n_bars"].min()) if available else None,
            "mean_n_bars": round(float(raw["n_bars"].mean()), 1) if available else None,
            "max_n_bars": int(raw["n_bars"].max()) if available else None,
        })
    return pd.DataFrame(rows)


def _describe(group: pd.DataFrame) -> dict:
    n = len(group)
    out = {"n": n}
    for col in FEATURE_COLS:
        s = pd.to_numeric(group[col], errors="coerce").dropna()
        out[f"{col}_mean"] = float(s.mean()) if len(s) else None
        out[f"{col}_median"] = float(s.median()) if len(s) else None
        out[f"{col}_std"] = float(s.std()) if len(s) > 1 else (0.0 if len(s) == 1 else None)
        for q in QUANTILES:
            out[f"{col}_q{int(round(q * 100))}"] = float(s.quantile(q)) if len(s) else None
        out[f"{col}_coverage_pct"] = round(100.0 * len(s) / n, 2) if n else None
    return out


def _grouped_describe(panel: pd.DataFrame, by: str) -> pd.DataFrame:
    rows = []
    for key, group in panel.groupby(by, sort=True):
        row = {by: key}
        row.update(_describe(group))
        rows.append(row)
    return pd.DataFrame(rows)


def descriptive_tables(panel: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """{'overall', 'by_period', 'by_ticker', 'by_date'} descriptive tables:
    N ticker-days, mean, median, std, quantiles (5/25/50/75/95), and
    per-feature coverage pct (share of non-null values within the group)."""
    if panel.empty:
        empty = pd.DataFrame()
        return {"overall": empty, "by_period": empty, "by_ticker": empty, "by_date": empty}
    overall = pd.DataFrame([_describe(panel)])
    return {
        "overall": overall,
        "by_period": _grouped_describe(panel, "period_label"),
        "by_ticker": _grouped_describe(panel, "ticker"),
        "by_date": _grouped_describe(panel, "trade_date"),
    }


def run_phase_a(conn, tier: str = RECONSTRUCTED) -> Dict[str, pd.DataFrame]:
    """Orchestrator: coverage audit + flow panel + descriptive tables."""
    coverage = coverage_audit(conn, tier)
    panel = build_flow_panel(conn, tier)
    tables = descriptive_tables(panel)
    return {"coverage": coverage, "panel": panel, **tables}


if __name__ == "__main__":
    from data.db import connect

    _conn = connect()
    _result = run_phase_a(_conn)
    pd.set_option("display.width", 160)
    print("=== Coverage audit ===")
    print(_result["coverage"].to_string(index=False))
    print("\n=== Overall descriptive stats ===")
    print(_result["overall"].to_string(index=False))
    print("\n=== By-period descriptive stats ===")
    print(_result["by_period"].to_string(index=False))
    _conn.close()
