"""D-096 G0: pre-outcome facts + pre-sample power. Reads NO 2025+ returns (only 2023-24 price-only drop days)."""
import sqlite3, numpy as np, pandas as pd
from scipy.stats import norm, spearmanr
DB = "file:data/walkforward.db?mode=ro"
RET = {"XL", "XC", "YP", "PD", "KK"}
BAR, FLOOR, MINPOW, COST = 3.2996, 0.30, 0.20, 0.60
c = sqlite3.connect(DB, uri=True)
o = pd.read_sql("select ticker,date,open,high,low,close,volume from ohlcv where date>='2022-11-01' order by ticker,date", c)
o["val"] = o.close * o.volume
g = o.groupby("ticker")
o["adv20"] = g.val.transform(lambda s: s.shift(1).rolling(20).mean())
o["ret"] = g.close.pct_change() * 100
o["vr"] = o.val / o.adv20
o["lr"] = np.log(o.high / o.low) ** 2 / (4 * np.log(2))
o["pk60"] = g.lr.transform(lambda s: np.sqrt(s.shift(1).rolling(60).mean()))
# forward excess return: next open -> close t+5 (price-only; used on PRE-SAMPLE only)
o["fwd"] = (g.close.shift(-5) / g.open.shift(-1) - 1) * 100
liq = o[(o.adv20 >= 5e9)].copy()
liq["xsr"] = liq.fwd - liq.groupby("date").fwd.transform("mean")
# ---- pre-outcome facts on the 2025+ events (no returns) ----
bf = pd.read_sql("select ticker,trade_date date,broker_code b,value from broker_flow where trade_date>='2025-01-02'", c)
bf = bf[~bf.b.isin(RET)]
net = bf.groupby(["ticker", "date", "b"]).value.sum().reset_index()
sell = net.assign(ns=-net.value).groupby(["ticker", "date"]).ns.max().rename("topsell").reset_index()
tot = net[net.value < 0].groupby(["ticker", "date"]).value.sum().abs().rename("totsell").reset_index()
f = liq[liq.date >= "2025-01-02"].merge(sell, on=["ticker", "date"]).merge(tot, on=["ticker", "date"], how="left")
f["FS"] = f.topsell.clip(lower=0) / f.adv20
f["conc"] = f.topsell / f.totsell
ev = f[(f.FS >= .5) & (f.ret <= -3)]
ctl = f[(f.FS < .1) & (f.ret <= -3)]
print("events", len(ev), "dates", ev.date.nunique(), "| controls", len(ctl), "dates", ctl.date.nunique())
d = sorted(ev.date.unique()); half = d[len(d) // 2]
print("halves split at", half, "events", (ev.date < half).sum(), (ev.date >= half).sum())
top5 = ev.groupby("date").size().sort_values(ascending=False).head(5)
print("top-5 date share of events %.1f%%" % (100 * top5.sum() / len(ev)), dict(top5))
ff = f.dropna(subset=["pk60", "vr", "conc"])
for k in ["ret", "vr", "pk60", "conc"]:
    print("spearman FS vs", k, round(spearmanr(ff.FS, ff[k])[0], 3))
print("event median vr %.2f conc %.2f; control median vr %.2f" % (ev.vr.median(), ev.conc.median(), ctl.vr.median()))
# ---- pre-sample power (2023-2024, price-only drop days) ----
pre = liq[(liq.date >= "2023-01-01") & (liq.date <= "2024-12-31") & (liq.ret <= -3)].dropna(subset=["xsr"])
print("pre-sample drop days", len(pre), "dates", pre.date.nunique(), "sd(xsr) %.2f%%" % pre.xsr.std(), "mean %.2f" % pre.xsr.mean())
rng = np.random.default_rng(96)
dates = pre.date.unique(); by = {k: v.xsr.values for k, v in pre.groupby("date")}
N_DATES = ev.date.nunique(); N_EV = len(ev); per = N_EV / N_DATES
res = []
for _ in range(4000):
    ds = rng.choice(dates, N_DATES, replace=True)
    x = np.concatenate([rng.choice(by[k], max(1, int(round(per))), replace=True) for k in ds])
    res.append(x.mean())
se_ev = np.std(res)
se_diff = se_ev * np.sqrt(1 + N_EV / max(len(ctl), 1))
for lab, se in [("event mean", se_ev), ("event-minus-control", se_diff)]:
    pw = 1 - norm.cdf(BAR - FLOOR / se)
    print(f"{lab}: SE {se:.3f}% | MDE@80% {(BAR + .84) * se:.2f}% | power at floor {FLOOR}%: {100 * pw:.2f}%  (stop rule min {100 * MINPOW:.0f}%)")
# half-sample version (thresholds judged on the second half only)
se_h = se_diff * np.sqrt(2)
print("second-half only: SE %.3f%% power %.2f%%" % (se_h, 100 * (1 - norm.cdf(BAR - FLOOR / se_h))))
