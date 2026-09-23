"""Audit of the FWD-PM-VOLEX-001 in-sample backtest reference for suspension look-ahead.

DIAGNOSTIC ONLY. Touches neither the ledger nor the frozen protocol, and cannot change
VOLEX-001's decision rule (PROTOCOL §3 thresholds are absolute numbers, frozen at opening).

The runner's universe mask (`run_forward.py::load_panel`, SUSP_PAD=20) excludes a ticker from
i0-20 .. i1+20 around each suspension (i0 = last_normal_date, i1 = resume_date). The i0-20..i0-1
half is unknowable at formation. The backtest reference (+0.394%/mo, t 3.74, median across 21
rebalance phases, 45 periods, 2022-07..2026-08; PROTOCOL §3) was produced in session analysis
with no committed code, so it is reconstructed here from the runner's own functions.

Arms (everything else is the runner's code, unchanged):
  A  as coded:   mask [i0-20, i1+20]                      (look-ahead)
  B  ex-ante:    mask [i0,    i1+20]  (only suspensions already begun by the formation date)
  C  no suspension mask at all
and two exit conventions:
  drop   runner's score(): names with no close at exit are DROPPED from both books
  last   last traded close on or before exit (ffill), never dropped
"""
import importlib.util, os, sys, json
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("rf", os.path.join(HERE, "..", "run_forward.py"))
rf = importlib.util.module_from_spec(spec); spec.loader.exec_module(rf)

panel = rf.load_panel()
# Session calendar = COMPLETE sessions only. The runner's own score() indexes the raw date list,
# so an exit can land on a partial fetch (2026-09-07: 137 rows; 2026-09-15: 824) and its
# dropna() then silently removes every name missing that day. The audit must not inherit that.
keep = [d for d in panel["dates"] if bool(panel["complete"].get(d, False))]
print(f"sessions: {len(panel['dates'])} raw, {len(keep)} complete; dropped "
      f"{sorted(set(panel['dates']) - set(keep))}", flush=True)
raw_dates = panel["dates"]; raw_idx = {d: i for i, d in enumerate(raw_dates)}
cl, vol, tvm, park = panel["close"], panel["vol"], panel["tvm"], panel["park"]
con = rf._ro(rf.DB)
susp = pd.read_sql_query("SELECT ticker,last_normal_date,resume_date FROM suspension_events", con)
con.close()

def mask(pre_pad):
    m = pd.DataFrame(False, index=cl.index, columns=cl.columns)
    for _, r in susp.iterrows():
        tk = r["ticker"]
        if tk not in m.columns: continue
        i0 = raw_idx.get(r["last_normal_date"])      # runner's raw calendar, as coded
        if i0 is None: continue
        i1 = raw_idx.get(r["resume_date"], i0)
        m.iloc[max(0, i0 - pre_pad): min(len(raw_dates) - 1, i1 + rf.SUSP_PAD) + 1,
               m.columns.get_loc(tk)] = True
    return m

base = (tvm >= rf.LIQ_FLOOR) & (cl >= rf.MIN_PRICE) & (vol > 0)
ELIG = {"A_as_coded": (base & ~mask(rf.SUSP_PAD)).fillna(False),
        "B_ex_ante": (base & ~mask(0)).fillna(False),
        "C_no_mask": base.fillna(False)}
# sanity: the as-coded arm must reproduce the runner's own eligibility exactly
assert ELIG["A_as_coded"].equals(panel["eligible"]), "reconstruction differs from runner"
# evaluate on complete sessions only
cl_ff = cl.ffill().loc[keep]
cl, tvm, park = cl.loc[keep], tvm.loc[keep], park.loc[keep]
ELIG = {k: v.loc[keep] for k, v in ELIG.items()}
dates = keep; didx = {d: i for i, d in enumerate(dates)}

def form_score(elig, t, exitmode):
    i = didx[t]
    if i + 1 + rf.HORIZON >= len(dates): return None
    adv = tvm.loc[t].where(elig.loc[t]).dropna()
    if len(adv) < rf.UNIVERSE_N: return None
    uni = adv.nlargest(rf.UNIVERSE_N).index
    sig = park.loc[t].reindex(uni).dropna()
    k = max(1, int(round(len(sig) * rf.EXCLUDE_FRAC)))
    drop = set(sig.nlargest(k).index); held = [x for x in sig.index if x not in drop]
    d0, d1 = dates[i + 1], dates[i + 1 + rf.HORIZON]
    px1 = cl if exitmode == "drop" else cl_ff
    def basket(n):
        r = (px1.loc[d1, n] / cl.loc[d0, n] - 1).replace([np.inf, -np.inf], np.nan).dropna()
        return r.mean(), int(cl.loc[d1, n].isna().sum())
    h, _ = basket(held); u, nmiss = basket(list(sig.index))
    return 100 * (h - u), nmiss

def stats(v):
    v = np.asarray(v, float); n = len(v)
    return dict(n=n, mean=float(v.mean()), t=float(v.mean() / (v.std(ddof=1) / np.sqrt(n))),
                p_pos=float((v > 0).mean()))

start = next(i for i, d in enumerate(dates) if d >= "2022-07-01")
end = next(i for i, d in enumerate(dates) if d >= "2026-09-01")      # formations through 2026-08
out = {}
for arm, elig in ELIG.items():
    for ex in ("drop", "last"):
        phases, missing = [], 0
        for p in range(rf.HORIZON):
            v = []
            for i in range(start + p, end, rf.HORIZON):
                r = form_score(elig, dates[i], ex)
                if r: v.append(r[0]); missing += r[1]
            phases.append(stats(v))
        # calendar-month cadence (the live test's): last session of each month
        mo = pd.Series(dates[start:end]).groupby(pd.Series(dates[start:end]).str[:7]).max()
        vm = [r[0] for r in (form_score(elig, d, ex) for d in mo) if r]
        out[f"{arm}|{ex}"] = {
            "phase_median_mean": float(np.median([s["mean"] for s in phases])),
            "phase_median_t": float(np.median([s["t"] for s in phases])),
            "phase_median_p_pos": float(np.median([s["p_pos"] for s in phases])),
            "periods_per_phase": int(np.median([s["n"] for s in phases])),
            "names_missing_at_exit_total": int(missing),
            "calendar_month": stats(vm)}
        o = out[f"{arm}|{ex}"]
        print(f"{arm:11s} exit={ex:4s}  phase-median mean {o['phase_median_mean']:+.3f}%/mo "
              f"t {o['phase_median_t']:+.2f}  P>0 {o['phase_median_p_pos']:.0%}  "
              f"n/phase {o['periods_per_phase']}  | month-end mean {o['calendar_month']['mean']:+.3f} "
              f"t {o['calendar_month']['t']:+.2f} n {o['calendar_month']['n']}  | missing-at-exit {missing}",
              flush=True)
json.dump(out, open(os.path.join(HERE, "suspension_lookahead_audit_RESULT.json"), "w"), indent=1)
