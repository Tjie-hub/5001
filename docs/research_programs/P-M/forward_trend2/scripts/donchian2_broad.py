"""FWD-PM-TREND-002 (DRAFT) -- frozen backtest specification. v1, 2026-09-20.

Donchian 20/10 time-series trend, BROAD-LIQUID threshold universe
(adv20 >= Rp 1e9), replacing FWD-PM-TREND-001's now-withdrawn top-80
membership design.

Design rationale (read before the code): FWD-PM-TREND-001 went through six
revisions and was withdrawn as a big-cap spec -- not because the Donchian
rule failed, but because three of its six defects (v3 loss-hiding, v4
held-count denominator, v5/v6 cross-ticker shift leak) were symptoms of ONE
root cause: a continuous daily portfolio book needs a daily aggregation
denominator, and every version of that denominator hid a bug. This spec
removes the daily book entirely. It measures trade-level events (entry to
actual channel exit, whatever the duration) -- the SAME convention already
registered for HYP-PM-0010 / FWD-PM-REGIME-002 (excess vs IHSG over the
identical window, aggregated as a mean with one-way entry-date-clustered
standard errors). No daily aggregation exists to get wrong.

Position state is built via an explicit per-ticker sequential scan, NOT a
vectorised shift -- deliberately the slower, more auditable choice, because
FWD-PM-TREND-001 v5's defect was specifically a vectorised shift silently
crossing a ticker boundary. A per-ticker loop cannot have that defect by
construction (see extract_trades()).

Universe, traded-days guard and cost basis are copied verbatim from the
ALREADY-REGISTERED FWD-PM-REGIME-002 protocol (adv20 >= Rp1e9 threshold, not
a monthly ranking -- so the sticky-universe bug class is structurally
impossible here: there is no membership table to go stale) for direct
comparability between the two {T1} family candidates.

Known open item, disclosed rather than silently inherited: the split-hygiene
exclusion list below (TMAS, MLPT, RMKE, RAJA, INET, PYFA) was audited under
TOP-80 MEMBERSHIP only (FWD-PM-TREND-001 section 1.2). This broader
threshold universe admits more names than top-80 ever did and has NOT had
its own dedicated split-continuity audit. The +/-35% contamination guard is
the only defense pending that audit -- the same caveat FWD-PM-FADE-001
already carries for the same reason.
"""
import sqlite3
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, ".")

# ---- frozen constants (section 2 of the protocol) ----
WINDOW_IN = 20          # Donchian breakout lookback, calendar sessions
WINDOW_OUT = 10          # Donchian exit lookback, calendar sessions
ADV_THRESH = 1e9        # liquid gate: 20-session ADV (Rp) -- matches FWD-PM-REGIME-002
PRICE_FLOOR = 50        # Rp
MIN_SESSIONS = 25       # minimum prior sessions traded (warm-up)
GUARD_WINDOW = 20
GUARD_MIN_TRADED = 18   # of trailing 20 sessions must have volume > 0
COST_RT = 0.006         # 0.60% round trip, the repo cost authority
CONTAM_MOVE = 0.35      # any single-session |return| beyond this inside the
                         # holding window voids that trade (split/suspension guard)
HYGIENE_EXCLUDE = ("TMAS", "MLPT", "RMKE", "RAJA", "INET", "PYFA")


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
    # every window computed on the FULL per-ticker calendar frame -- no row
    # is ever dropped before a rolling window is computed (window-splice
    # class, closed by construction, not by review)
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
    d = d.merge(splits, on=["ticker", "date"], how="left")
    d["is_split"] = d["is_split"].fillna(0)
    d["bad"] = ((d.ret.abs() > CONTAM_MOVE) | (d.is_split > 0))
    d["liq"] = ((d.adv20 >= ADV_THRESH) & (d.close >= PRICE_FLOOR) &
                (d.n >= MIN_SESSIONS) & (d.volume > 0) & (d.traded20 >= GUARD_MIN_TRADED)
                ).fillna(False)
    d["entry_sig"] = (d.close > d.hh20) & d.hh20.notna() & (d.volume > 0) & d.liq
    d["exit_sig"] = (d.close < d.ll10) & d.ll10.notna()
    return d


def extract_trades(d):
    """Explicit per-ticker sequential scan for entry->exit pairs. NOT a
    vectorised shift/ffill -- see module docstring. Deliberately the slower,
    auditable choice."""
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
                    break  # unresolved position through data end; no more
                           # entries can open in this ticker after it
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
    """one-way cluster-robust t-stat of the mean, clustered on `groups`
    (identical formula to forward_regime/scripts/panel.py's convention,
    reused verbatim)."""
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
    """Secondary benchmark: equal-weight return of every liq-eligible name
    AT ENTRY, over the SAME entry->exit window as the trade (variable
    duration, unlike a fixed-horizon event study -- computed per trade via a
    wide close-price matrix, not a python loop over tickers)."""
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

    ihsg_open_close = ihsg["close"]
    tr["ihsg_ret"] = (tr.exit_date.map(ihsg_open_close).values /
                       tr.entry_date.map(ihsg_open_close).values - 1)
    tr = tr[tr.ihsg_ret.notna()].copy()
    tr["excess_ihsg"] = tr.trade_ret - tr.ihsg_ret

    tr["ewb_ret"] = ewb_returns(d, tr)
    tr["excess_ewb"] = tr.trade_ret - tr.ewb_ret

    mu_i, t_i = cluster_t(tr.excess_ihsg.values, tr.entry_date.values)
    ewb_ok = tr.excess_ewb.notna()
    mu_e, t_e = cluster_t(tr.loc[ewb_ok, "excess_ewb"].values, tr.loc[ewb_ok, "entry_date"].values)

    top = tr.groupby("ticker").size().sort_values(ascending=False)

    print("FWD-PM-TREND-002 frozen event study v1 (DRAFT, in-sample reference)")
    print(f"universe : adv20>=Rp1e9 threshold (not membership), {d.ticker.nunique()} tickers loaded, "
          f"{int(d.liq.sum()):,} liquid ticker-days")
    print(f"trades   : {n_raw:,} raw -> {n_raw - n_used:,} contaminated (excluded) -> "
          f"{n_used:,} used; {censored:,} still open at data end (censored, excluded)")
    print(f"          {tr.ticker.nunique()} distinct tickers, {tr.entry_date.nunique()} distinct entry dates")
    print(f"          top ticker {top.index[0]} = {top.iloc[0]} trades ({100*top.iloc[0]/len(tr):.1f}% of total)")
    print(f"          median hold {tr.hold_days.median():.0f}d, mean hold {tr.hold_days.mean():.1f}d")
    print(f"vs IHSG  : N={len(tr):,}  mean excess {mu_i*100:+.2f}%  cluster-t {t_i:.2f}")
    print(f"vs EWbook: N={int(ewb_ok.sum()):,}  mean excess {mu_e*100:+.2f}%  cluster-t {t_e:.2f}")

    ex25 = tr[tr.entry_date.dt.year != 2025]
    mu_x, t_x = cluster_t(ex25.excess_ihsg.values, ex25.entry_date.values)
    print(f"ex-2025 vs IHSG: N={len(ex25):,}  mean excess {mu_x*100:+.2f}%  cluster-t {t_x:.2f}")

    # integrity checks, printed every run
    assert (tr.exit_date > tr.entry_date).all(), "FAIL: non-positive holding period found"
    assert not set(tr.ticker) & set(HYGIENE_EXCLUDE), "FAIL: hygiene-excluded ticker in trades"
    print("integrity: entry<exit for all trades OK; no hygiene-excluded ticker present OK")


if __name__ == "__main__":
    main()
