"""FWD-PM-TREND-003 (DRAFT) -- frozen backtest specification. v1, 2026-09-20.

Regime-gated Donchian 20/10 trend: identical construction to FWD-PM-TREND-002
(broad-liquid threshold universe, trade-level event study, no daily book),
with ONE addition -- entries also require HYP-PM-0010's own registered
regime classifier to be True on that day.

Why: FWD-PM-TREND-002's raw (regime-unconditional) Donchian rule showed a
statistically strong full-sample excess (+3.55% vs IHSG, t=4.35) that
evaporated ex-2025 (+0.83%, t=1.31). The year-by-year read there tracked
IHSG's own trending/choppy years almost exactly (2025: IHSG +20.7%, system
excess +12.4%; 2023: IHSG +6.2%, system excess -1.9%). That is consistent
with a plain hypothesis: an UNCONDITIONAL trend rule only works when the
market is actually trending, and HYP-PM-0010's regime classifier
(slope/efficiency-ratio/participation) exists specifically to detect that.
This spec tests that hypothesis directly rather than speculating about it.

The regime classifier is reproduced from
docs/research_programs/P-M/forward_regime/scripts/ma.py and the frozen
definition in forward_regime/PROTOCOL.md section 2, NOT re-derived:
  ema20      = close.ewm(span=20, adjust=False, min_periods=20).mean()
  slope      = ema20(t) / ema20(t-10) - 1                          > +0.02
  ER (Kaufman)= |close(t)-close(t-20)| / sum(|daily close diffs|,20) >= 0.30
  pct_above  = fraction of last 20 closes above ema20               >= 0.70
  regime OK  = all three, evaluated on data through t-1 (lagged one session,
               shift(1), grouped by ticker -- no look-ahead, matches the
               registered protocol's own convention verbatim)

Everything else -- universe, traded-days guard, Donchian 20/10 entry/exit,
cost, contamination guard, dual benchmark, cluster_t, and the explicit
per-ticker trade-extraction scan (not a vectorised shift) -- is copied
unchanged from FWD-PM-TREND-002's frozen script. Only the entry condition
gets one extra AND clause.
"""
import sqlite3
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, ".")

# ---- frozen constants (section 2 of the protocol) ----
WINDOW_IN = 20
WINDOW_OUT = 10
ADV_THRESH = 1e9
PRICE_FLOOR = 50
MIN_SESSIONS = 25
GUARD_WINDOW = 20
GUARD_MIN_TRADED = 18
COST_RT = 0.006
CONTAM_MOVE = 0.35
HYGIENE_EXCLUDE = ("TMAS", "MLPT", "RMKE", "RAJA", "INET", "PYFA")
# regime classifier thresholds -- verbatim from forward_regime/PROTOCOL.md section 2
SLOPE_MIN = 0.02
ER_MIN = 0.30
PA_MIN = 0.70


def load():
    con = sqlite3.connect("file:data/walkforward.db?mode=ro", uri=True)
    d = pd.read_sql(
        "SELECT ticker,date,open,high,low,close,volume FROM ohlcv "
        "WHERE is_final=1 AND close>0 AND high>0 AND low>0 AND ticker!='IHSG'", con)
    ca = pd.read_sql("SELECT ticker,date,action FROM corporate_actions", con)
    ihsg = pd.read_sql(
        "SELECT date,open,close FROM ohlcv WHERE ticker='IHSG' AND is_final=1", con)
    con.close()
    d["date"] = pd.to_datetime(d["date"])
    d = d[~d.ticker.isin(HYGIENE_EXCLUDE)]
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
    d["hh20"] = g["high"].transform(
        lambda s: s.rolling(WINDOW_IN, min_periods=WINDOW_IN).max())
    d["hh20"] = d.groupby("ticker", sort=False)["hh20"].shift(1)
    d["ll10"] = g["low"].transform(
        lambda s: s.rolling(WINDOW_OUT, min_periods=WINDOW_OUT).min())
    d["ll10"] = d.groupby("ticker", sort=False)["ll10"].shift(1)
    nz = (d.volume > 0).astype(int)
    d["traded20"] = nz.groupby(d.ticker).transform(
        lambda s: s.rolling(GUARD_WINDOW, min_periods=GUARD_WINDOW).sum())

    # regime classifier -- verbatim reproduction of ma.py / PROTOCOL.md section 2
    d["ema20"] = g["close"].transform(
        lambda s: s.ewm(span=20, adjust=False, min_periods=20).mean())
    d["slope"] = d.ema20 / d.groupby("ticker", sort=False)["ema20"].shift(10) - 1
    d["absmv"] = g["close"].transform(
        lambda s: s.diff().abs().rolling(20, min_periods=20).sum())
    close_shift20 = d.groupby("ticker", sort=False)["close"].shift(20)
    d["ER"] = (d.close - close_shift20).abs() / d.absmv.replace(0, np.nan)
    above = (d.close > d.ema20)
    d["pct_above"] = above.groupby(d.ticker).transform(
        lambda s: s.rolling(20, min_periods=20).mean())
    # evaluated on data through t-1 only -- lagged one session, grouped shift
    d["sl_1"] = d.groupby("ticker", sort=False)["slope"].shift(1)
    d["er_1"] = d.groupby("ticker", sort=False)["ER"].shift(1)
    d["pa_1"] = d.groupby("ticker", sort=False)["pct_above"].shift(1)
    d["regime_ok"] = ((d.sl_1 > SLOPE_MIN) & (d.er_1 >= ER_MIN) & (d.pa_1 >= PA_MIN)).fillna(False)

    d = d.merge(splits, on=["ticker", "date"], how="left")
    d["is_split"] = d["is_split"].fillna(0)
    d["bad"] = ((d.ret.abs() > CONTAM_MOVE) | (d.is_split > 0))
    d["liq"] = ((d.adv20 >= ADV_THRESH) & (d.close >= PRICE_FLOOR) &
                (d.n >= MIN_SESSIONS) & (d.volume > 0) & (d.traded20 >= GUARD_MIN_TRADED)
                ).fillna(False)
    # THE ONE ADDED CLAUSE vs FWD-PM-TREND-002: & d.regime_ok
    d["entry_sig"] = (d.close > d.hh20) & d.hh20.notna() & (d.volume > 0) & d.liq & d.regime_ok
    d["exit_sig"] = (d.close < d.ll10) & d.ll10.notna()
    return d


def extract_trades(d):
    """Explicit per-ticker sequential scan -- unchanged from FWD-PM-TREND-002."""
    trades = []
    censored = 0
    for ticker, g in d.groupby("ticker", sort=False):
        dates = g.date.values
        closes = g.close.values
        entry_sig = g.entry_sig.values
        exit_sig = g.exit_sig.values
        bad = g.bad.values
        n = len(g)
        i = 0
        while i < n:
            if entry_sig[i]:
                entry_i = i
                exit_i = None
                j = i + 1
                while j < n:
                    if exit_sig[j]:
                        exit_i = j
                        break
                    j += 1
                if exit_i is None:
                    censored += 1
                    break
                contaminated = bool(bad[entry_i + 1: exit_i + 1].any())
                trades.append((ticker, dates[entry_i], dates[exit_i],
                                closes[entry_i], closes[exit_i], contaminated))
                i = exit_i + 1
            else:
                i += 1
    tr = pd.DataFrame(trades, columns=["ticker", "entry_date", "exit_date",
                                        "entry_close", "exit_close", "contaminated"])
    return tr, censored


def cluster_t(x, groups):
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


def ewb_returns(d, tr):
    wide_close = d.pivot(index="date", columns="ticker", values="close")
    wide_liq = d.pivot(index="date", columns="ticker", values="liq").fillna(False)
    out = np.full(len(tr), np.nan)
    for k, row in enumerate(tr.itertuples()):
        try:
            elig = wide_liq.loc[row.entry_date].values
            c0 = wide_close.loc[row.entry_date].values
            c1 = wide_close.loc[row.exit_date].values
        except KeyError:
            continue
        mask = elig & np.isfinite(c0) & np.isfinite(c1) & (c0 > 0)
        if mask.sum() < 10:
            continue
        out[k] = (c1[mask] / c0[mask] - 1).mean()
    return out


def main():
    d, splits, ihsg = load()
    d = build(d, splits)
    tr, censored = extract_trades(d)

    n_raw = len(tr)
    tr = tr[~tr.contaminated].copy()
    n_used = len(tr)

    tr["trade_ret"] = tr.exit_close / tr.entry_close - 1 - COST_RT
    tr["hold_days"] = (tr.exit_date - tr.entry_date).dt.days

    ihsg_c = ihsg["close"]
    tr["ihsg_ret"] = (tr.exit_date.map(ihsg_c).values / tr.entry_date.map(ihsg_c).values - 1)
    tr = tr[tr.ihsg_ret.notna()].copy()
    tr["excess_ihsg"] = tr.trade_ret - tr.ihsg_ret

    tr["ewb_ret"] = ewb_returns(d, tr)
    tr["excess_ewb"] = tr.trade_ret - tr.ewb_ret

    mu_i, t_i = cluster_t(tr.excess_ihsg.values, tr.entry_date.values)
    ewb_ok = tr.excess_ewb.notna()
    mu_e, t_e = cluster_t(tr.loc[ewb_ok, "excess_ewb"].values, tr.loc[ewb_ok, "entry_date"].values)

    top = tr.groupby("ticker").size().sort_values(ascending=False)

    print("FWD-PM-TREND-003 frozen event study v1 (DRAFT, in-sample reference)")
    print(f"universe : adv20>=Rp1e9 threshold + regime_ok gate, {d.ticker.nunique()} tickers loaded, "
          f"{int(d.liq.sum()):,} liquid ticker-days, {int((d.liq & d.regime_ok).sum()):,} liquid+regime-ok ticker-days")
    print(f"trades   : {n_raw:,} raw -> {n_raw - n_used:,} contaminated (excluded) -> "
          f"{n_used:,} used; {censored:,} still open at data end (censored, excluded)")
    print(f"          {tr.ticker.nunique()} distinct tickers, {tr.entry_date.nunique()} distinct entry dates")
    if len(tr):
        print(f"          top ticker {top.index[0]} = {top.iloc[0]} trades ({100*top.iloc[0]/len(tr):.1f}% of total)")
        print(f"          median hold {tr.hold_days.median():.0f}d, mean hold {tr.hold_days.mean():.1f}d")
    print(f"vs IHSG  : N={len(tr):,}  mean excess {mu_i*100:+.2f}%  cluster-t {t_i:.2f}")
    print(f"vs EWbook: N={int(ewb_ok.sum()):,}  mean excess {mu_e*100:+.2f}%  cluster-t {t_e:.2f}")

    ex25 = tr[tr.entry_date.dt.year != 2025]
    mu_x, t_x = cluster_t(ex25.excess_ihsg.values, ex25.entry_date.values)
    print(f"ex-2025 vs IHSG: N={len(ex25):,}  mean excess {mu_x*100:+.2f}%  cluster-t {t_x:.2f}")

    print()
    print("year-by-year (excess vs IHSG, entry-date year):")
    tr["yr"] = tr.entry_date.dt.year
    yby = tr.groupby("yr").excess_ihsg.agg(["size", "mean"])
    yby["mean"] = yby["mean"] * 100
    print(yby.to_string(float_format=lambda x: f"{x:.2f}"))

    assert (tr.exit_date > tr.entry_date).all(), "FAIL: non-positive holding period found"
    assert not set(tr.ticker) & set(HYGIENE_EXCLUDE), "FAIL: hygiene-excluded ticker in trades"
    print()
    print("integrity: entry<exit for all trades OK; no hygiene-excluded ticker present OK")


if __name__ == "__main__":
    main()
