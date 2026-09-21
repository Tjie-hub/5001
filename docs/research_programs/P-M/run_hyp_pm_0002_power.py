#!/usr/bin/env python3
"""HYP-PM-0002 power/MDE analysis — preparation only, NO OFI data touched.

Uses ONLY: (1) the 62 pre-registered formation dates (already fixed, coverage-derived),
(2) OHLCV prices (unconditional k-day returns, to measure the noise floor), (3) the
ADV>=5bn liquidity rule (already fixed), (4) suspension_events. Never loads OFI, delta,
buy_lot/sell_lot, or any flow-conditioned statistic. This is by construction: the noise
floor (idiosyncratic return variance + common-day-factor variance) is a nuisance
parameter of the null distribution, not the tested effect.
"""
import sqlite3, math
import numpy as np
import pandas as pd

DB = "data/walkforward.db"
ADV_MIN = 5_000_000_000  # engine/liquidity.py VALUE_LIQ_MIN_IDR, reused unchanged
KS = [3, 7, 15]
ALPHA = 0.05
Z_ALPHA2 = 1.959964
Z_80 = 0.841621
Z_90 = 1.281552

con = sqlite3.connect(DB)

# 1. The 62 pre-registered formation dates (coverage-derived, fixed in the draft)
dates = [r[0] for r in con.execute("""
    SELECT trade_date FROM (
      SELECT trade_date, COUNT(DISTINCT ticker) nt FROM stockbit_flow_bars
      WHERE trade_date>='2026-04-01' GROUP BY trade_date
    ) WHERE nt>=500 ORDER BY trade_date
""")]
print(f"formation dates: {len(dates)} ({dates[0]}..{dates[-1]})")

# 2. Flow-reporting ticker set per formation date (restrict query to exactly these 62 dates
#    to avoid touching the 18.3M-row table broadly)
ph = ",".join("?" * len(dates))
flow_tickers = {}
for d, t in con.execute(
    f"SELECT trade_date, ticker FROM stockbit_flow_bars WHERE trade_date IN ({ph})", dates
):
    flow_tickers.setdefault(d, set()).add(t)

# 3. Master trading calendar (for k-trading-day-ahead lookups)
cal = [r[0] for r in con.execute("SELECT DISTINCT date FROM ohlcv ORDER BY date")]
cal_idx = {d: i for i, d in enumerate(cal)}

# 4. OHLCV window: 35 trading days before first formation date -> last needed exit date (k=15)
start_buf = cal[max(cal_idx[dates[0]] - 35, 0)]
end_needed = cal[min(cal_idx[dates[-1]] + 15, len(cal) - 1)]
print(f"loading ohlcv window {start_buf}..{end_needed}")
ohlcv = pd.read_sql(
    "SELECT ticker, date, close, volume FROM ohlcv WHERE date>=? AND date<=? AND is_final=1",
    con, params=[start_buf, end_needed],
)
print(f"ohlcv rows loaded: {len(ohlcv):,}  mem~{ohlcv.memory_usage(deep=True).sum()/1e6:.1f}MB")
ohlcv = ohlcv.sort_values(["ticker", "date"]).reset_index(drop=True)
ohlcv["dollar_vol"] = ohlcv["close"] * ohlcv["volume"]
ohlcv["logp"] = np.log(ohlcv["close"].clip(lower=1e-9))

# 30-trading-day trailing ADV per ticker (shift(1) so "as of t" excludes t itself -> no lookahead)
ohlcv["adv30"] = (
    ohlcv.groupby("ticker")["dollar_vol"]
    .transform(lambda s: s.shift(1).rolling(30, min_periods=20).mean())
)

price_lookup = ohlcv.set_index(["ticker", "date"])["logp"].to_dict()
adv_lookup = ohlcv.set_index(["ticker", "date"])["close"].to_dict()  # not used; placeholder
adv30_lookup = ohlcv.set_index(["ticker", "date"])["adv30"].to_dict()

# 5. Suspension windows, for exclusion of tickers suspended between t and t+k
susp = pd.read_sql("SELECT ticker, last_normal_date, resume_date FROM suspension_events", con)
susp_intervals = {}
for _, r in susp.iterrows():
    susp_intervals.setdefault(r["ticker"], []).append((r["last_normal_date"], r["resume_date"] or "9999-12-31"))

def is_suspended_between(ticker, d_from, d_to):
    for lo, hi in susp_intervals.get(ticker, []):
        if not (hi < d_from or lo > d_to):
            return True
    return False

# 6. For each k: build the (ticker, formation_date) universe and the UNCONDITIONAL k-day
#    log-return for each -- no OFI, no sign, no flow value used at all.
results = {}
for k in KS:
    rows = []
    for d in dates:
        i = cal_idx.get(d)
        if i is None or i + k >= len(cal):
            continue  # horizon-tail trim
        d_exit = cal[i + k]
        ftick = flow_tickers.get(d, set())
        for tkr in ftick:
            adv = adv30_lookup.get((tkr, d))
            if adv is None or adv < ADV_MIN:
                continue
            if is_suspended_between(tkr, d, d_exit):
                continue
            lp0 = price_lookup.get((tkr, d))
            lp1 = price_lookup.get((tkr, d_exit))
            if lp0 is None or lp1 is None:
                continue
            rows.append((d, tkr, lp1 - lp0))
    df = pd.DataFrame(rows, columns=["formation_date", "ticker", "ret_k"])
    # data hygiene: same clip convention as EXP-PM-0001 (drop >20% single-name moves as bad prints)
    df = df[df["ret_k"].abs() <= 0.5]  # k-day moves can legitimately exceed 20%; use a wider 50% guard
    results[k] = df
    n_days = df["formation_date"].nunique()
    n_obs = len(df)
    print(f"k={k}: usable formation dates={n_days}  total ticker-day obs={n_obs}  "
          f"median universe/day={df.groupby('formation_date').size().median():.0f}")

con.close()

# 7. Variance decomposition: for each k, day-level cross-sectional mean (f_t) and
#    within-day idiosyncratic variance (sigma_e^2), both from RAW returns only.
print("\n=== Variance decomposition (unconditional k-day returns; NO OFI used) ===")
decomp = {}
for k in KS:
    df = results[k]
    day_stats = df.groupby("formation_date")["ret_k"].agg(["mean", "var", "count"])
    sigma_f2 = day_stats["mean"].var(ddof=1)          # variance of the daily cross-sectional mean
    sigma_e2 = (day_stats["var"] * (day_stats["count"] - 1)).sum() / (day_stats["count"] - 1).sum()
    n_days = len(day_stats)
    n_t_median = day_stats["count"].median()
    decomp[k] = dict(sigma_f2=sigma_f2, sigma_e2=sigma_e2, n_days=n_days, n_t_median=n_t_median)
    print(f"k={k}: n_days={n_days}  median N_t={n_t_median:.0f}  "
          f"sigma_f (day-factor SD)={math.sqrt(sigma_f2)*100:.3f}%  "
          f"sigma_e (idio SD)={math.sqrt(sigma_e2)*100:.3f}%")

import json, os
out = {k: {kk: float(vv) for kk, vv in v.items()} for k, v in decomp.items()}
out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hyp_pm_0002_decomp.json")
json.dump(out, open(out_path, "w"), indent=2)
print(f"\nwrote {out_path}")
