"""FWD-PM-FADE-001 (DRAFT) -- frozen pre-registration script.

Tests whether the "failed breakdown" pattern (price sweeps below the trailing
20-session low intraday, then closes back above it -- a setup widely read by
retail/technical traders as a bullish reversal / "stop hunt" / "spring") is
followed by NEGATIVE forward excess returns on the liquid IDX universe.

This is a pure OBSERVATIONAL / EVENT-STUDY design: it does not hold a
continuous position book, does not attempt to short, and does not touch any
other frozen spec's ledger (in particular FWD-PM-REGIME-002's). It measures
the signal's own forward performance, exactly parallel to how
FWD-PM-VOLEX-001 measured the volatility-exclusion effect on its own before
that effect was ever adopted into BOOK_OVERLAY_POLICY.md. Any future use of
this signal as an entry-suppression / exit-acceleration overlay on another
system is a SEPARATE, later step, contingent on this test's own result --
not assumed here.

Design choices made in response to lessons learned earlier the same session
on FWD-PM-TREND-001 (five real defects found and fixed across v1-v4) and
already-run self-audits on this scan (PATTERN_SCAN_2026-09-17.md section 7):
  - universe membership is a PER-ROW threshold gate (adv20 >= Rp1e9), never a
    ticker-level set -- structurally immune to the "sticky universe" bug.
  - no row is ever dropped before a rolling window is computed -- structurally
    immune to the "window splice" bug.
  - this is an event study (mean + cluster-robust SE per signal), not a
    continuously-held book -- structurally immune to the "aggregation
    denominator" bug (there is no held/count ratio to get wrong).
  - entry fills at the NEXT session's open, not the signal bar's close (the
    close-fill bias PATTERN_SCAN_2026-09-17.md section 7 found and corrected).
  - benchmark is measured BOTH against IHSG (institutional convention) and
    against an equal-weight liquid book computed under the identical
    entry/exit convention (the fairer bar; liquid stocks are known to beat
    IHSG by about +0.35%/20d, which understates any negative signal's true
    magnitude if IHSG alone is trusted).

Independent replication note: the underlying pattern and its exploratory
(close-fill, IHSG-only) numbers were first measured in
docs/research_programs/P-M/pattern_scan/PATTERN_SCAN_2026-09-17.md
(scripts/patterns.py, arm P3a). This script independently rebuilds the
signal and its forward performance from raw data using a different
implementation, to remove the risk that a rebuild-from-scratch would surface
a defect the original scan missed (exactly the check that broke
FWD-PM-TREND-001 down to its honest number). It did not: the rebuild
reproduced the original numbers closely (see PROTOCOL_DRAFT.md section 1).
"""
import sqlite3
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, ".")

# ---- frozen constants (section 2 of the protocol) ----
ADV_THRESH = 1e9        # liquid gate: 20-session ADV (Rp)
PRICE_FLOOR = 50        # Rp
MIN_SESSIONS = 25       # minimum prior sessions traded (warm-up)
LOOKBACK = 20            # Donchian-style trailing-low lookback (calendar sessions)
GUARD_WINDOW = 20
GUARD_MIN_TRADED = 18   # of trailing 20 sessions must have volume > 0
HORIZONS = (5, 10, 20)  # holding periods, sessions
COST = 0.006            # 0.60% round trip, the repo cost authority
CONTAM_MOVE = 0.35      # any single-session |return| beyond this inside the
                         # holding window voids that signal (split/suspension guard)


def load():
    con = sqlite3.connect("file:data/walkforward.db?mode=ro", uri=True)
    d = pd.read_sql(
        "SELECT ticker,date,open,high,low,close,volume FROM ohlcv "
        "WHERE is_final=1 AND close>0 AND volume>=0 AND ticker!='IHSG'", con)
    ca = pd.read_sql("SELECT ticker,date,action FROM corporate_actions", con)
    ihsg = pd.read_sql(
        "SELECT date,open,close FROM ohlcv WHERE ticker='IHSG' AND is_final=1", con)
    con.close()
    d["date"] = pd.to_datetime(d["date"])
    d = d.sort_values(["ticker", "date"]).reset_index(drop=True)
    ihsg["date"] = pd.to_datetime(ihsg["date"])
    ihsg = ihsg.sort_values("date").set_index("date")
    splits = ca[ca.action == "split"][["ticker", "date"]].copy()
    splits["date"] = pd.to_datetime(splits["date"])
    splits["is_split"] = 1
    return d, splits, ihsg


def build(d, splits):
    g = d.groupby("ticker", sort=False)
    d["ret"] = g["close"].pct_change()
    d["n"] = g.cumcount()
    dval = d.close * d.volume
    d["adv20"] = dval.groupby(d.ticker).transform(
        lambda s: s.rolling(20, min_periods=15).mean())
    d["adv20"] = d.groupby("ticker", sort=False)["adv20"].shift(1)
    d["lo20"] = g["low"].transform(
        lambda s: s.rolling(LOOKBACK, min_periods=LOOKBACK).min()).groupby(d.ticker).shift(1)
    nz = (d.volume > 0).astype(int)
    d["nz20"] = nz.groupby(d.ticker).transform(
        lambda s: s.shift(1).rolling(GUARD_WINDOW, min_periods=GUARD_WINDOW).sum())
    d = d.merge(splits, on=["ticker", "date"], how="left")
    d["is_split"] = d["is_split"].fillna(0)
    d["bad"] = ((d.ret.abs() > CONTAM_MOVE) | (d.is_split > 0)).astype(int)
    d["liq"] = ((d.adv20 >= ADV_THRESH) & (d.close >= PRICE_FLOOR) &
                (d.n >= MIN_SESSIONS) & (d.volume > 0) & (d.nz20 >= GUARD_MIN_TRADED)
                ).fillna(False).astype(bool)
    # next-session open/date -- the tradeable entry (signal close is not fillable)
    g = d.groupby("ticker", sort=False)
    d["entry_open"] = g["open"].shift(-1)
    d["entry_date"] = g["date"].shift(-1)
    for h in HORIZONS:
        d[f"exit_close_{h}"] = g["close"].shift(-h)
        d[f"exit_date_{h}"] = g["date"].shift(-h)
        # contamination anywhere in [signal+1 .. signal+h]
        d[f"bad_{h}"] = g["bad"].transform(
            lambda s: s.shift(-1).rolling(h, min_periods=1).sum())
        # equal-weight liquid-book forward return under the SAME entry/exit
        # convention (next-open in, h-session close out), for the fair
        # (non-IHSG) benchmark -- computed on every liquid row, not just signals
        d[f"fwd_open_{h}"] = np.where(
            d.liq, d[f"exit_close_{h}"] / d.entry_open - 1, np.nan)
    return d


def cluster_t(x, groups):
    """one-way cluster-robust t-stat of the mean, clustered on `groups`
    (identical to docs/research_programs/P-M/forward_regime/scripts/panel.py)."""
    x = np.asarray(x, float)
    groups = np.asarray(groups)
    n = len(x)
    if n < 3:
        return np.nan, np.nan
    mu = x.mean()
    e = x - mu
    s = pd.Series(e).groupby(groups).sum().values
    G = len(s)
    if G < 3:
        return mu, np.nan
    var = (s ** 2).sum() * (G / (G - 1)) / n ** 2
    if var <= 0:
        return mu, np.nan
    return mu, mu / np.sqrt(var)


def main():
    d, splits, ihsg = load()
    d = build(d, splits)
    signal = d.liq & (d.low < d.lo20) & (d.close > d.lo20) & d.entry_open.notna()

    # equal-weight liquid book, per (calendar date, horizon): the fair benchmark
    ewb = {h: d[d.liq].groupby("date")[f"fwd_open_{h}"].mean() for h in HORIZONS}

    ihsg_open = ihsg["open"]
    ihsg_close = ihsg["close"]

    sig = d[signal].copy()
    print("FWD-PM-FADE-001 frozen event study v1 (DRAFT, in-sample reference)")
    print(f"signal   : {len(sig):,} candidate signals, {sig.date.nunique():,} distinct "
          f"dates, {sig.ticker.nunique():,} distinct tickers")
    top = sig.groupby("ticker").size().sort_values(ascending=False)
    print(f"           top ticker {top.index[0]} = {top.iloc[0]} signals "
          f"({100*top.iloc[0]/len(sig):.1f}% of total)")

    rows = []
    for h in HORIZONS:
        s = sig[sig[f"exit_close_{h}"].notna() & (sig[f"bad_{h}"].fillna(1) == 0)].copy()
        stock_ret = s[f"exit_close_{h}"] / s.entry_open - 1

        ih_open = s.entry_date.map(ihsg_open)
        ih_close = s[f"exit_date_{h}"].map(ihsg_close)
        ihsg_ret = ih_close / ih_open - 1
        ok = ihsg_ret.notna()
        exc_ihsg = (stock_ret - COST - ihsg_ret)[ok].values
        mu_i, t_i = cluster_t(exc_ihsg, s.date.values[ok])

        ewb_ret = s.apply(lambda r: ewb[h].get(r.date, np.nan), axis=1)
        ok2 = ewb_ret.notna()
        exc_ewb = (stock_ret - COST - ewb_ret)[ok2].values
        mu_e, t_e = cluster_t(exc_ewb, s.date.values[ok2])

        rows.append([h, int(ok.sum()), mu_i * 100, t_i, int(ok2.sum()), mu_e * 100, t_e])

    tab = pd.DataFrame(rows, columns=["h", "N", "exc_vs_IHSG%", "t_IHSG",
                                       "N_ewb", "exc_vs_EWbook%", "t_EWbook"])
    print(tab.to_string(index=False, float_format=lambda x: f"{x:.2f}"))

    # ex-2025 read, h=20, the program's standard "remove the inflated era" check
    s = sig[sig["exit_close_20"].notna() & (sig["bad_20"].fillna(1) == 0)].copy()
    s = s[pd.DatetimeIndex(s.date).year != 2025]
    stock_ret = s["exit_close_20"] / s.entry_open - 1
    ih_open = s.entry_date.map(ihsg_open)
    ih_close = s["exit_date_20"].map(ihsg_close)
    ihsg_ret = ih_close / ih_open - 1
    ok = ihsg_ret.notna()
    mu, t = cluster_t((stock_ret - COST - ihsg_ret)[ok].values, s.date.values[ok])
    print(f"ex-2025 h=20 vs IHSG: N={int(ok.sum())}  exc {mu*100:+.2f}%  t {t:.2f}")


if __name__ == "__main__":
    main()
