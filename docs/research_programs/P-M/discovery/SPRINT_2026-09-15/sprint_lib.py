#!/usr/bin/env python3
"""Rapid edge discovery sprint (2026-09-15) — shared library.

DISCOVERY ONLY. Nothing here is confirmatory or registered evidence.
Read-only access to: production walkforward.db (ohlcv, stockbit_flow,
corporate_actions, suspension_events), frozen Dataset B views_v1.sqlite,
frozen v002 minute-bar store. No writes to any source store.

Conventions inherited from the program:
- PIT trailing normalization: statistics over the trailing 60 admitted
  sessions, shift(1); never the contemporaneous cross-section alone.
- PIT liquidity floor: trailing-60-session median traded value (close*volume)
  shifted by 1, >= Rp 1e9.
- Forward returns: hold_k(t) = close(t+1+k)/close(t+1) - 1 (entry at next
  close), computed on split- and dividend-adjusted returns.
- Cost reality check: 0.60% round-trip friction floor (memo S6), central
  environment 0.40-0.60%.
- NW t: erfc two-sided (g1_harness.py::nw_t convention). Reported for
  description only — NOT the sprint's ranking criterion.
"""
from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field, asdict

import numpy as np
import pandas as pd

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", ".."))
WF = os.path.join(ROOT, "data", "walkforward.db")
VIEWS = os.path.join(ROOT, "docs", "research_programs", "P-M", "research_data", "views_v1.sqlite")
V002 = os.path.join(ROOT, "data", "frozen", "stockbit-flow-bars-v002", "stockbit-flow-bars-v002.db")
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")

LIQ_FLOOR = 1e9          # Rp, trailing-60 median traded value, PIT
TRAIL = 60               # trailing sessions for PIT normalization
COST_RT_FLOOR = 0.0060   # 60 bp round-trip sensitivity floor
COST_RT_MID = 0.0050     # 50 bp central
HORIZONS = (1, 5, 10, 20)

# v002 minute-bar declared exclusions (from the 2026-09-14 data-gap audit)
V002_FIXTURE_DATES = {"2025-04-14"}
V002_INTEGRITY_ZONE = ("2025-08-04", "2025-09-17")   # inclusive, 31 sessions
BROKER_EXCLUDED = {"DM"}                              # insufficient identity evidence


def ro_conn(path: str):
    import sqlite3
    c = sqlite3.connect("file:" + path + "?mode=ro", uri=True)
    c.execute("PRAGMA query_only = ON;")
    return c


# ---------------------------------------------------------------- loaders --

def load_ohlcv() -> pd.DataFrame:
    """Production final OHLCV, long frame: ticker,date,open,high,low,close,volume."""
    c = ro_conn(WF)
    try:
        df = pd.read_sql_query(
            "SELECT ticker, date, open, high, low, close, volume FROM ohlcv "
            "WHERE is_final=1 AND date>='2024-06-01' AND close>0 ORDER BY ticker, date", c)
    finally:
        c.close()
    return df


def load_corporate_actions() -> pd.DataFrame:
    c = ro_conn(WF)
    try:
        df = pd.read_sql_query("SELECT ticker, date, action, value FROM corporate_actions", c)
    finally:
        c.close()
    return df


def load_stockbit_flow_daily(lo: str = "2024-06-01") -> pd.DataFrame:
    """Daily retail-platform flow (959 tickers). Production table is identical
    to frozen v002 on the overlap (checked 2026-09-15 by aggregate equality),
    so it serves as one continuous canvas 2025-01-02..2026-09-14."""
    c = ro_conn(WF)
    try:
        df = pd.read_sql_query(
            "SELECT ticker, trade_date, buy_lot, sell_lot, net_lot, buy_freq, "
            "sell_freq, net_value FROM stockbit_flow WHERE trade_date>=? "
            "ORDER BY trade_date, ticker", c, params=(lo,))
    finally:
        c.close()
    return df


def load_broker_day() -> pd.DataFrame:
    """Frozen Dataset B broker x ticker x day (IDX100 roster), excl. broker DM."""
    c = ro_conn(VIEWS)
    try:
        df = pd.read_sql_query(
            "SELECT ticker, trade_date, broker_code, value_pos, value_neg, gross, net "
            "FROM v_a_broker_day", c)
    finally:
        c.close()
    return df[df.broker_code != "DM"].copy()


def load_broker_day_hist() -> pd.DataFrame:
    """Frozen Dataset B per broker x ticker x day history (bounded lookback
    table used for persistence features): last 8 sessions per ticker-day are
    derived in the family script from this full table."""
    return load_broker_day()


def load_concentration() -> pd.DataFrame:
    c = ro_conn(VIEWS)
    try:
        df = pd.read_sql_query("SELECT * FROM v_b_concentration", c)
    finally:
        c.close()
    return df


def load_flow_price() -> pd.DataFrame:
    c = ro_conn(VIEWS)
    try:
        df = pd.read_sql_query("SELECT * FROM v_f_flow_price", c)
    finally:
        c.close()
    return df


def load_suspensions() -> pd.DataFrame:
    c = ro_conn(WF)
    try:
        df = pd.read_sql_query(
            "SELECT ticker, last_normal_date, resume_date FROM suspension_events", c)
    finally:
        c.close()
    return df


# ------------------------------------------------------- adjusted prices --

def build_adjusted(ohlcv: pd.DataFrame, ca: pd.DataFrame) -> pd.DataFrame:
    """Per ticker: adjusted return series (splits always; dividends on ex-date),
    plus unadjusted close/volume/traded_value kept alongside.

    Split basis detection per dataset_b/foundation.py: if the raw close-to-close
    return across the ex-date matches 1/factor-1 within 25%, the store is
    UNADJUSTED for that event and pre-ex prices get divided by the factor.
    Dividends: ret_adj on ex-date adds div/prev_close.
    """
    df = ohlcv.copy()
    df["traded_value"] = df["close"] * df["volume"]

    splits = ca[ca.action == "split"].rename(columns={"date": "ex_date", "value": "factor"})
    divs = ca[ca.action == "dividend"].rename(columns={"date": "ex_date", "value": "div"})

    df = df.sort_values(["ticker", "date"])
    df["prev_close"] = df.groupby("ticker")["close"].shift(1)
    df["ret_raw"] = df["close"] / df["prev_close"] - 1.0

    split_factor = {}   # (ticker, ex_date) -> divisor applied to pre-ex prices if unadjusted
    for (t, ex), fac in splits.set_index(["ticker", "ex_date"])["factor"].items():
        if fac and 0.01 < fac < 1000:
            split_factor[(t, ex)] = float(fac)

    # detect applied basis per event (foundation.py convention); keep an events
    # list and patch each affected ticker's history before its ex-date
    events = {}         # ticker -> list of (ex_date, multiplier)
    by_ticker = {t: g[["date", "close"]].reset_index(drop=True) for t, g in df.groupby("ticker")}
    for (t, ex), fac in split_factor.items():
        g = by_ticker.get(t)
        if g is None:
            continue
        prior = g[g.date < ex]
        cur = g.loc[g.date == ex, "close"]
        if prior.empty or cur.empty:
            continue
        obs = float(cur.iloc[0]) / float(prior["close"].iloc[-1]) - 1.0
        if abs(obs - (1.0 / fac - 1.0)) < 0.25:   # unadjusted -> patch
            events.setdefault(t, []).append((ex, 1.0 / fac))

    fix = np.ones(len(df))
    if events:
        dates_arr = df["date"].values
        tick_arr = df["ticker"].values
        for t, evs in events.items():
            m = tick_arr == t
            idx = np.where(m)[0]
            dts = dates_arr[idx]
            for ex, mult in evs:
                fix[idx[dts < ex]] *= mult
    df["close_adj"] = df["close"] * fix

    df["ret"] = df["close_adj"] / df.groupby("ticker")["close_adj"].shift(1) - 1.0
    # dividend patch on ex-dates
    dv = divs.groupby(["ticker", "ex_date"])["div"].sum()
    dv.index.names = ["ticker", "date"]
    df = df.merge(dv.rename("div").reset_index(), on=["ticker", "date"], how="left")
    df["div"] = df["div"].fillna(0.0)
    df["ret"] = df["ret"] + df["div"] / df["prev_close"]
    df.loc[df["prev_close"].isna(), "ret"] = np.nan
    df.loc[df["ret"].abs() > 0.9, "ret"] = np.nan   # residual data defect guard
    return df


# ------------------------------------------------------------ panels -----

def to_panel(df: pd.DataFrame, value_col: str, index_col: str = "date",
             col_col: str = "ticker") -> pd.DataFrame:
    return df.pivot_table(index=index_col, columns=col_col, values=value_col, aggfunc="last").sort_index()


def trailing_z(panel: pd.DataFrame, window: int = TRAIL, min_obs: int = 20) -> pd.DataFrame:
    """PIT z-score vs own trailing history: (x - mean_past)/std_past, shift(1)."""
    mean = panel.rolling(window, min_periods=min_obs).mean().shift(1)
    std = panel.rolling(window, min_periods=min_obs).std().shift(1)
    return (panel - mean) / std.replace(0.0, np.nan)


def trailing_median_panel(panel: pd.DataFrame, window: int = TRAIL) -> pd.DataFrame:
    return panel.rolling(window, min_periods=20).median().shift(1)


class SprintPanel:
    """The daily discovery canvas: 2025-01-02 .. 2026-09-14, ~958 tickers."""

    def __init__(self):
        ohlcv = load_ohlcv()
        ca = load_corporate_actions()
        adj = build_adjusted(ohlcv, ca)
        self.adj = adj
        # Sprint canvas: 2025-01-02..2026-09-14. The 2026-09-15 session present
        # in production ohlcv (585 is_final=1 rows inserted by the morning fetch
        # BEFORE WIB open) is anomalous and excluded; 2026-08-25 is absent from
        # stockbit_flow (missed daily fetch) — flows are NaN there, no signal
        # formation. Both declared as sprint exclusions.
        self.dates = np.sort(adj["date"].unique())
        self.dates = self.dates[(self.dates >= "2025-01-01") & (self.dates <= "2026-09-14")]
        cal = adj[adj.date >= "2024-06-01"]
        self.close = to_panel(cal, "close")
        self.ret = to_panel(cal, "ret").reindex(index=self.close.index)  # pivot drops the all-NaN first row
        self.volume = to_panel(cal, "volume")
        self.traded_value = to_panel(cal, "traded_value")
        self.tv_med60 = trailing_median_panel(self.traded_value)
        self.liquid = self.tv_med60 >= LIQ_FLOOR

        sbf = load_stockbit_flow_daily()
        self.nb = to_panel(sbf[sbf.trade_date >= "2024-06-01"], "net_value", "trade_date")
        self.buy_lot = to_panel(sbf[sbf.trade_date >= "2024-06-01"], "buy_lot", "trade_date")
        self.sell_lot = to_panel(sbf[sbf.trade_date >= "2024-06-01"], "sell_lot", "trade_date")
        # align flow panels to the OHLCV calendar (missed daily-fetch sessions become NaN)
        for name in ("nb", "buy_lot", "sell_lot"):
            setattr(self, name, getattr(self, name).reindex(index=self.close.index,
                                                            columns=self.close.columns))
        # traded-value-based flow ratio: net_value / ADV60 (PIT)
        self.adv60 = trailing_median_panel(self.traded_value)
        self.nb_over_adv = self.nb / self.adv60
        self.nb_z = trailing_z(self.nb)
        self.ret1 = self.ret
        self.ret5 = (self.ret.fillna(0.0) + 1).rolling(5).apply(np.prod, raw=True) - 1
        self.ret20 = (self.ret.fillna(0.0) + 1).rolling(20).apply(np.prod, raw=True) - 1
        self.vol_z = trailing_z(self.volume)
        # forward returns, I7 convention: hold_k(t) = prod_{i=2..k+1}(1+ret(t+i)) - 1
        self.hold = {}
        r1 = self.ret + 1.0
        cum = r1.cumprod()
        for k in HORIZONS:
            # close(t+1+k)/close(t+1)-1 = cum(t+1+k)/cum(t+1)-1
            self.hold[k] = cum.shift(-1 - k) / cum.shift(-1) - 1.0
        # entry-day tradability: stock must trade on t+1
        self.trades_next = (self.volume.shift(-1) > 0) & self.volume.shift(-1).notna()

    def mask_base(self) -> pd.DataFrame:
        """Base tradability mask: liquid PIT + trades next day + inside window."""
        m = self.liquid & self.trades_next
        m = m[m.index.isin(self.dates)]
        return m


# ------------------------------------------------------------ evaluation --

def nw_t(x: np.ndarray) -> float:
    """erfc two-sided p via g1 convention; returns the t statistic."""
    x = x[~np.isnan(x)]
    if len(x) < 5:
        return np.nan
    se = x.std(ddof=1) / math.sqrt(len(x))
    if se == 0:
        return np.nan
    return float(x.mean() / se)


def nw_p(x: np.ndarray) -> float:
    t = nw_t(x)
    if math.isnan(t):
        return np.nan
    return math.erfc(abs(t) / math.sqrt(2.0))


def eval_signal(name: str, sig: pd.DataFrame, mask: pd.DataFrame, panel: SprintPanel,
                ledger: list | None = None, meta: dict | None = None,
                horizons=HORIZONS, direction: int = 1,
                min_obs: int = 1000, min_tickers: int = 50) -> dict:
    """Evaluate a long-only candidate. sig>0 (after direction) = candidate long.

    Discovery metrics only: economic magnitude, breadth, stability by
    subperiod, cost survival, NW t reported for description (NOT ranked on).
    """
    sig = sig.reindex(index=mask.index, columns=mask.columns)
    act = (mask & (direction * sig > 0) & sig.notna()).fillna(False).astype(bool)
    out = {"id": name, "meta": meta or {}}
    n_obs = int(act.values.sum())
    out["n_obs"] = n_obs
    out["n_tickers"] = int(act.any(axis=0).sum())
    out["avg_per_day"] = float(act.sum(axis=1).mean())
    if n_obs < 500:
        out["status"] = "KILL(too-few-obs)"
        if ledger is not None:
            ledger.append(out)
        return out
    out["min_obs_req"], out["min_tickers_req"] = min_obs, min_tickers

    def stats(mask_k: pd.DataFrame, k: int) -> dict:
        r = panel.hold[k][mask_k]
        v = r.values[r.notna().values]
        if len(v) == 0:
            return {}
        return {"mean": float(np.mean(v)), "med": float(np.median(v)),
                "hit": float((v > 0).mean()), "n": int(len(v))}

    subperiods = {"2025H1": ("2025-01-01", "2025-07-01"), "2025H2": ("2025-07-01", "2026-01-01"),
                  "2026H1": ("2026-01-01", "2026-07-01"), "2026H2": ("2026-07-01", "2026-12-31")}
    for k in horizons:
        r = panel.hold[k][act]
        per_day_mean = r.mean(axis=1)           # equal-weight daily portfolio return
        vals = r.values[r.notna().values]
        if len(vals) < 100:
            continue
        gross = float(np.nanmean(vals))
        sp_means = {}
        for sp, (lo, hi) in subperiods.items():
            sub = r[(r.index >= lo) & (r.index < hi)]
            v = sub.values[sub.notna().values]
            sp_means[sp] = round(float(np.mean(v)), 6) if len(v) > 50 else None
        net = gross - COST_RT_FLOOR
        out[f"h{k}"] = {
            "gross_mean": gross, "gross_med": float(np.median(vals)),
            "hit": float((vals > 0).mean()),
            "net_floor": net,
            "nw_t_perday": round(nw_t(per_day_mean.values), 3),
            "nw_p_perday": round(nw_p(per_day_mean.values), 4),
            "by_subperiod": sp_means,
            "subperiod_min": min([v for v in sp_means.values() if v is not None], default=None),
        }
    # status heuristics (explicit rules, no tuning)
    h5 = out.get("h5") or out.get("h10") or out.get("h20")
    best = max([out[f"h{k}"]["gross_mean"] for k in horizons if f"h{k}" in out], default=None)
    if best is None:
        out["status"] = "KILL(no-data)"
    elif n_obs < min_obs or out["n_tickers"] < min_tickers:
        out["status"] = "KILL(breadth)"
    elif h5 is None:
        out["status"] = "WATCH"
    else:
        sub_vals = [v for v in h5["by_subperiod"].values() if v is not None]
        sign_flips = len({(v > 0) for v in sub_vals}) > 1
        if h5["net_floor"] < 0:
            out["status"] = "KILL(cost)"
        elif sign_flips:
            out["status"] = "WATCH(unstable)"
        else:
            out["status"] = "WATCH"
    if ledger is not None:
        ledger.append(out)
    return out


def fm_regression(panel: SprintPanel, sig: pd.DataFrame, mask: pd.DataFrame,
                  controls: list[pd.DataFrame], k: int = 5) -> dict:
    """Fama-MacBeth: hold_k ~ [1, sig_z, controls...] cross-sectionally per date.
    Returns mean and NW t of the sig coefficient (incrementality check)."""
    common = sig.index
    y = panel.hold[k]
    Xs = [sig] + controls
    coefs, ns = [], []
    for d in common:
        if d not in y.index:
            continue
        yy = y.loc[d]
        cols = [xx.loc[d] if d in xx.index else pd.Series(dtype=float) for xx in Xs]
        frame = pd.concat([yy] + cols, axis=1)
        frame.columns = ["y"] + [f"x{i}" for i in range(len(cols))]
        ok = frame.notna().all(axis=1)
        frame = frame[ok]
        if len(frame) < 30:
            continue
        X = frame[[c for c in frame.columns if c != "y"]].values
        X = np.column_stack([np.ones(len(X)), X])
        try:
            beta, *_ = np.linalg.lstsq(X, frame["y"].values, rcond=None)
        except np.linalg.LinAlgError:
            continue
        coefs.append(beta[1])    # coefficient on the candidate (standardized-ish input)
        ns.append(len(frame))
    coefs = np.array(coefs)
    if len(coefs) < 20:
        return {"fm_mean": np.nan, "fm_t": np.nan, "n_dates": len(coefs)}
    return {"fm_mean": round(float(coefs.mean()), 6), "fm_t": round(nw_t(coefs), 3),
            "n_dates": int(len(coefs)), "avg_cross_sec_n": float(np.mean(ns))}


def save_ledger(ledger: list, path: str):
    with open(path, "w") as f:
        json.dump(ledger, f, indent=1, default=str)


def dump_panel_cache(panel: SprintPanel):
    os.makedirs(CACHE, exist_ok=True)
    with open(os.path.join(CACHE, "panel.pkl"), "wb") as f:
        pickle_dump(panel, f)


def pickle_dump(obj, f):
    import pickle
    pickle.dump(obj, f, protocol=4)


def pickle_load(path):
    import pickle
    with open(path, "rb") as f:
        return pickle.load(f)


def in_v002_window(dates: pd.Index) -> pd.Index:
    """Admitted minute-bar sessions: frozen window minus fixture minus integrity zone."""
    lo, hi = V002_INTEGRITY_ZONE
    keep = [(d <= "2026-04-27") and d not in V002_FIXTURE_DATES and not (lo <= d <= hi)
            for d in dates]
    return dates[pd.Series(keep).values]
