#!/usr/bin/env python3
"""EXP-PM-0001 — confirmatory experiment for HYP-PM-0001 (frozen sha256 540c2d52...).

Runs the registered spec EXACTLY. No tuning, no optimisation, no parameter search.
- OFI_t   = delta / (buy_lot + sell_lot)                      (signed imbalance, normalized)
- r_t     = log(price_t / price_{t-1})   within (ticker, day)  (contemporaneous displacement)
- rev_k   = log(price_{t+k} / price_t)   within (ticker, day)  (forward reversal, k bars ~ k min)
- signed_reversal_k = -sign(OFI_t) * rev_k   (contrarian capture; >0 == reversion == M1.1)
- friction = 0.60% round-trip (engine/exits/costs.py: buy 0.25% + sell 0.35%, incl slippage)
- inference: cluster-by-DAY (aggregate to daily strategy mean, t-test the daily series)
- guard: bid-ask-bounce control = re-measure with a 1-bar entry gap (t+1 .. t+1+k)

Read-only on data/walkforward.db. Writes results JSON + a text log. No DB writes, no prod code.
"""
import sqlite3, json, math, sys, datetime
import numpy as np, pandas as pd

DB = "data/walkforward.db"
FRICTION = 0.0060          # 0.60% round-trip — registered friction model
KS = [5, 15, 30]           # k=15 PRIMARY; 5/30 robustness-gradient consistency (declared, not selection)
KPRIMARY = 15
RET_CLIP = 0.20            # data-hygiene: drop |1-min return| > 20% (bad prints) — not tuning
OUT = "docs/research_programs/P-M/experiments/EXP-PM-0001"

def log(m, f):
    print(m); f.write(m + "\n")

def daily_stats(per_bar_value, day_index):
    """cluster-by-day: mean per day, then stats across days."""
    s = pd.DataFrame({"d": day_index, "v": per_bar_value}).dropna()
    daily = s.groupby("d")["v"].mean()
    n = len(daily); mu = daily.mean(); sd = daily.std(ddof=1)
    se = sd / math.sqrt(n) if n > 1 else float("nan")
    t = mu / se if se and se == se and se != 0 else float("nan")
    sharpe = (mu / sd * math.sqrt(252)) if sd and sd == sd and sd != 0 else float("nan")
    ci = (mu - 1.959964 * se, mu + 1.959964 * se)
    return dict(n_days=int(n), mean=float(mu), se=float(se), t=float(t),
                ci95=[float(ci[0]), float(ci[1])], sharpe_daily=float(sharpe))

def main():
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    f = open(f"{OUT}/execution.log", "w")
    log(f"EXP-PM-0001 confirmatory run @ {ts}", f)
    con = sqlite3.connect(DB)
    fr = con.execute("SELECT MIN(trade_date),MAX(trade_date),COUNT(*),COUNT(DISTINCT ticker) FROM stockbit_flow_bars").fetchone()
    log(f"flow_bars dataset: {fr[0]}..{fr[1]}  rows={fr[2]}  tickers={fr[3]}", f)

    log("loading flow bars...", f)
    df = pd.read_sql("SELECT ticker,trade_date,bar_time,buy_lot,sell_lot,price,delta "
                     "FROM stockbit_flow_bars WHERE price>0", con)
    log(f"loaded {len(df):,} rows", f)
    df = df.sort_values(["ticker", "trade_date", "bar_time"], kind="stable").reset_index(drop=True)

    tot = (df.buy_lot + df.sell_lot).to_numpy(dtype="float64")
    df["ofi"] = np.where(tot > 0, df.delta.to_numpy("float64") / tot, np.nan)
    df["logp"] = np.log(df.price.to_numpy("float64"))
    grp = df.groupby(["ticker", "trade_date"], sort=False)
    df["r_t"] = grp["logp"].diff()
    for k in KS:
        df[f"rev{k}"] = grp["logp"].shift(-k) - df["logp"]
        df[f"revgap{k}"] = grp["logp"].shift(-(k + 1)) - grp["logp"].shift(-1)  # bid-ask-bounce guard (skip 1 bar)

    valid = df.ofi.notna() & df.r_t.notna() & (df.r_t.abs() <= RET_CLIP)
    d = df[valid].copy()
    log(f"analysis rows (valid ofi + r_t, |r_t|<=20%): {len(d):,}", f)

    res = {"experiment_id": "EXP-PM-0001", "hypothesis_id": "HYP-PM-0001",
           "registration_sha256": "540c2d52dd8751dbda2a6b39ea7935860e12078c666a81e2156ff199ee885199",
           "run_utc": ts, "friction_roundtrip": FRICTION, "k_primary": KPRIMARY,
           "dataset": {"table": "stockbit_flow_bars", "range": [fr[0], fr[1]], "rows": fr[2], "tickers": fr[3]},
           "n_analysis_rows": int(len(d))}

    # --- Leg 1: contemporaneous displacement (r_t ~ ofi) : expect beta > 0 ---
    m = d.r_t.notna() & d.ofi.notna()
    cov = np.cov(d.ofi[m], d.r_t[m]); beta_disp = cov[0, 1] / cov[0, 0]
    corr_disp = np.corrcoef(d.ofi[m], d.r_t[m])[0, 1]
    res["displacement"] = {"beta_r_on_ofi": float(beta_disp), "corr": float(corr_disp)}
    log(f"\n[Leg 1] displacement  beta(r_t~ofi)={beta_disp:.6e}  corr={corr_disp:.4f}  (expect >0)", f)

    # --- Leg 2: reversal per k ---
    res["reversal"] = {}
    for k in KS:
        rev = d[f"rev{k}"]
        mk = rev.notna() & d.ofi.notna() & (rev.abs() <= 0.5)
        beta_rev = np.cov(d.ofi[mk], rev[mk])[0, 1] / np.var(d.ofi[mk])
        sr = -np.sign(d.ofi[mk]) * rev[mk]                       # signed reversal (contrarian capture)
        st = daily_stats(sr.to_numpy(), d.trade_date[mk].to_numpy())
        st["beta_rev_on_ofi"] = float(beta_rev)
        st["gross_mean_pct"] = st["mean"] * 100
        st["net_of_cost_mean"] = st["mean"] - FRICTION
        st["net_of_cost_pct"] = (st["mean"] - FRICTION) * 100
        # bid-ask-bounce guard
        revg = d[f"revgap{k}"]
        mg = revg.notna() & d.ofi.notna() & (revg.abs() <= 0.5)
        srg = -np.sign(d.ofi[mg]) * revg[mg]
        stg = daily_stats(srg.to_numpy(), d.trade_date[mg].to_numpy())
        st["guard_gap_gross_mean_pct"] = stg["mean"] * 100
        st["guard_gap_t"] = stg["t"]
        res["reversal"][f"k{k}"] = st
        tag = "PRIMARY" if k == KPRIMARY else "robustness"
        log(f"\n[Leg 2 k={k} {tag}] beta(rev~ofi)={beta_rev:.3e} (expect <0 for reversion)", f)
        log(f"   signed_reversal gross = {st['gross_mean_pct']:.4f}%/trade  t={st['t']:.2f}  "
            f"CI95=[{st['ci95'][0]*100:.4f},{st['ci95'][1]*100:.4f}]%  days={st['n_days']}", f)
        log(f"   NET of 0.60% friction = {st['net_of_cost_pct']:.4f}%/trade", f)
        log(f"   bid-ask-bounce guard (skip 1 bar): gross={st['guard_gap_gross_mean_pct']:.4f}%/trade t={st['guard_gap_t']:.2f}", f)

    # --- Decile sort on OFI (descriptive), k primary ---
    dd = d[d[f"rev{KPRIMARY}"].notna() & (d[f"rev{KPRIMARY}"].abs() <= 0.5)].copy()
    dd["dec"] = pd.qcut(dd.ofi, 10, labels=False, duplicates="drop")
    dec_mean = dd.groupby("dec")[f"rev{KPRIMARY}"].mean() * 100
    spread = float(dec_mean.iloc[0] - dec_mean.iloc[-1])   # low-OFI fwd minus high-OFI fwd
    res["decile"] = {"fwd_ret_pct_by_decile": [float(x) for x in dec_mean.tolist()],
                     "low_minus_high_spread_pct": spread}
    log(f"\n[Decile k={KPRIMARY}] fwd-ret%% by OFI decile (0=lowest OFI): "
        + ", ".join(f"{x:.4f}" for x in dec_mean.tolist()), f)
    log(f"   low-minus-high reversal spread = {spread:.4f}%  (gross; vs 0.60% round-trip)", f)

    # --- Robustness-gradient consistency (sign of gross reversal across k) ---
    signs = {k: (1 if res["reversal"][f"k{k}"]["mean"] > 0 else -1) for k in KS}
    res["robustness_consistent_sign"] = len(set(signs.values())) == 1
    log(f"\n[Robustness] gross reversal signs across k={KS}: {signs}  consistent={res['robustness_consistent_sign']}", f)

    json.dump(res, open(f"{OUT}/results.json", "w"), indent=2)
    log(f"\nresults.json + execution.log written to {OUT}", f)
    f.close()

if __name__ == "__main__":
    main()
