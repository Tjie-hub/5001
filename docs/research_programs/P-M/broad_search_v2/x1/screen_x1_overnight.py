"""X1 overnight transmission screen -- FROZEN driver (predeclaration rev 2, 2026-10-05).

This driver is committed FROZEN together with PREDECLARATION_X1_OVERNIGHT.md (+ .sha256) and
MUST NOT BE RUN until a REVIEW_R2 file in broad_search_v2/ contains GO for X1 -- the guard
below enforces that mechanically. One run, after GO, through research/tracking.py ->
RESULT_X1_<utc>.json next to this file. A crash before outcomes print may be re-run with
disclosure; anything after that is a new arm and needs a new R2 GO (V2 brief §6).

Everything here implements PREDECLARATION_X1_OVERNIGHT.md rev 2 exactly: signal per TIMING.md
(beta-hat rolling 250 pairs / expanding min 120, sigma trailing 250 / expanding min 120, k<=3
gap aggregation with a single last IDX leg, k>=4 excluded), outcome = LW book open->close over
tick-eligible members (REVIEW_R1 2.3) with the all-rows book as co-equal lens, NW(5) slope,
terciles at fixed normal quantiles, mandatory year-by-year, absorption share, timing-overlay
and standalone economics (0.60% RT floor AND D-059 modeled cost via the committed
cost_liquidity/cost_by_adv.py functions), recorder-count correlations (D-062).
"""
import hashlib
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]                      # broad_search_v2/x1 -> repo root
sys.path.insert(0, str(ROOT))
PREDECL_SHA = hashlib.sha256((HERE / "PREDECLARATION_X1_OVERNIGHT.md").read_bytes()).hexdigest()

# ---------------------------------------------------------------- R2 GO guard
_r2 = sorted((HERE.parent).glob("REVIEW_R2_*.md"))
if not _r2:
    sys.exit("REFUSING TO RUN: no REVIEW_R2_*.md exists in broad_search_v2/ yet (frozen at R2).")
_go = [p.name for p in _r2 if "GO" in p.read_text(errors="ignore").upper()
       and "X1" in p.read_text(errors="ignore").upper()]
if not _go:
    sys.exit(f"REFUSING TO RUN: no REVIEW_R2 GO for X1 found in {[p.name for p in _r2]}.")
print(f"R2 GO found: {_go}")

BAR = 3.2745                    # frozen: E[max|Z|] at N = 555 + 6 arms (bar_v2 integral)
TICK_MAX = 0.005
ADV_MIN = 5e9
SPLIT_DATE = pd.Timestamp("2021-07-05")
END_FROZEN = pd.Timestamp("2026-07-29")     # confirmation end frozen (REVIEW_R1 3)
Q_POS = 100e6                   # D-059 convention: Rp 100m per position
RT_FLOOR = 0.006
out = {"predeclaration_sha256": PREDECL_SHA, "bar_frozen": BAR,
       "r2_go_files": _go, "params": {"issuance": True, "adv_min": ADV_MIN,
       "tick_max_frac": TICK_MAX, "beta_rolling": 250, "beta_min_pairs": 120,
       "sigma_rolling": 250, "sigma_min": 120, "nw_lags": 5,
       "tercile_cut": 0.430727, "end_frozen": str(END_FROZEN),
       "db": "local walkforward.db (fingerprint + max date recorded by tracking)"}}


def norm_cdf(x):
    from math import erf, sqrt
    return 0.5 * (1.0 + np.vectorize(erf)(np.clip(x, -30, 30) / sqrt(2.0)))


def nw_t(y: np.ndarray, x: np.ndarray, lags: int = 5) -> dict:
    """OLS slope of y on x with Newey-West (Bartlett, `lags`) standard error."""
    y = np.asarray(y, float); x = np.asarray(x, float)
    m = np.isfinite(y) & np.isfinite(x)
    y, x = y[m] - y[m].mean(), x[m] - x[m].mean()
    n = len(x)
    if n < 10 or x.std() == 0:
        return {"n": int(n), "slope": np.nan, "t": np.nan}
    denom = float((x * x).sum())
    beta = float((x * y).sum() / denom)
    u = y - beta * x
    g0 = float((u * x).dot(u * x)) / denom ** 2 * n
    acc = g0
    for l in range(1, lags + 1):
        w = 1.0 - l / (lags + 1.0)
        g = float((u[l:] * x[l:]).dot(u[:-l] * x[:-l])) / denom ** 2 * n
        acc += 2.0 * w * g
    se = float(np.sqrt(max(acc, 0.0) / n))
    return {"n": int(n), "slope": beta, "t": (beta / se) if se > 0 else np.nan}


def main() -> None:
    with _tracking() as run:
        # ------------------------------------------------------------- corpus
        import data.db as _ddb
        _orig = _ddb.connect
        def _c(*a, **k):
            c = _orig(*a, **k)
            try: c.execute("PRAGMA mmap_size=0")
            except Exception: pass
            return c
        _ddb.connect = _c
        import research.rulecard.data as rcdata
        from data.adjustments import read_raw_ohlcv
        from data.db import connect
        with connect(read_only=True) as c:
            ihsg = (read_raw_ohlcv(c).loc[lambda x: x["ticker"] == "IHSG",
                                          ["date", "open", "close"]]
                    .assign(date=lambda x: pd.to_datetime(x["date"]))
                    .sort_values("date").reset_index(drop=True))
        print("loading extended panel (issuance=True) ...", flush=True)
        P = rcdata.load_extended_ohlcv(issuance=True)
        P["date"] = pd.to_datetime(P["date"])
        P = P.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)
        val = P["close"] * P["volume"]
        tv = val.groupby(P["ticker"], sort=False)
        P["adv20"] = tv.transform(lambda x: x.rolling(20, min_periods=20).mean())
        P["med60"] = tv.transform(lambda x: x.rolling(60, min_periods=60).median())
        P["prev_close"] = P.groupby("ticker", sort=False)["close"].shift(1)
        P["adv20_d"] = P.groupby("ticker", sort=False)["adv20"].shift(1)
        P["med60_d"] = P.groupby("ticker", sort=False)["med60"].shift(1)

        dates = np.sort(P["date"].unique())
        didx = {d: i for i, d in enumerate(dates)}
        T = len(dates)
        tickers = np.sort(P["ticker"].unique())
        tix = {t: i for i, t in enumerate(tickers)}
        cal = pd.DatetimeIndex(dates)

        def mat(col):
            M = np.full((T, len(tickers)), np.nan)
            M[P["date"].map(didx).values, P["ticker"].map(tix).values] = P[col].values
            return M

        O, C, H, L, V = mat("open"), mat("close"), mat("high"), mat("low"), mat("volume")
        A20, W60, PC = mat("adv20_d"), mat("med60_d"), mat("prev_close")
        liquid = (A20 >= ADV_MIN) & (V > 0) & (O > 0) & (C > 0)
        tickv = np.select([PC < 200, PC < 500, PC < 2000, PC < 5000], [1.0, 2.0, 5.0, 10.0], 25.0)
        tick_frac = np.divide(tickv, np.where(PC > 0, PC, np.nan), out=np.full_like(C, np.nan))
        eligible = liquid & (tick_frac <= TICK_MAX)

        def book(keep):
            r = np.where(keep, C / O - 1.0, np.nan)
            g = np.where(keep, O / np.roll(C, 1, axis=0) - 1.0, np.nan)
            g[0] = np.nan
            ws = np.nansum(np.where(keep, W60, 0.0), axis=1)
            with np.errstate(divide="ignore", invalid="ignore"):
                w = np.where(keep & (ws[:, None] > 0),
                             np.divide(W60, np.where(ws[:, None] > 0, ws[:, None], 1.0)), 0.0)
            return (pd.Series(np.nansum(w * r, axis=1), index=cal),
                    pd.Series(np.nansum(w * g, axis=1), index=cal))

        oc_e, gap_e = book(eligible)             # PRIMARY (tick-eligible)
        oc_a, gap_a = book(liquid)               # co-equal lens (all rows)
        tl = tix.get("TLKM")
        oc_tlkm = pd.Series(np.where(eligible[:, tl], C[:, tl] / O[:, tl] - 1.0, np.nan), index=cal)
        gap_tlkm = pd.Series(np.where(eligible[:, tl],
                                      O[:, tl] / np.r_[np.nan, C[:-1, tl]] - 1.0, np.nan), index=cal)
        ihsg_oc = ihsg.assign(oc=ihsg["close"] / ihsg["open"] - 1.0).set_index("date")["oc"]

        # ------------------------------------------------------- signal series
        DATA = HERE / "data"
        fx = pd.read_csv(DATA / "usdidr.csv", parse_dates=["date"]).set_index("date")["close"]
        jk = pd.read_csv(DATA / "jkse.csv", parse_dates=["date"]).set_index("date")["close"]
        fx_ok = np.array([d in fx.index for d in cal])
        pair_ok = np.array([d in jk.index for d in cal]) & fx_ok
        pair_ok[0] = False

        arms_src = {"EIDO": "eido.csv", "TLK": "tlk.csv", "SPY": "spy.csv"}
        sig = {}
        for nm, fn in arms_src.items():
            s = pd.read_csv(DATA / fn, parse_dates=["date"]).set_index("date")["close"]
            us_dates = pd.DatetimeIndex(s.index)
            has_prev = pd.Series(np.arange(len(s)), index=us_dates).shift(1)  # prev US index
            avail = has_prev.notna()
            y = {}                                  # session j -> compounded US return
            kcount = {}
            for j in range(1, T):
                d, D = cal[j - 1], cal[j]
                idxs = us_dates[(us_dates >= d) & (us_dates < D)]
                if len(idxs) == 0:
                    continue
                pos = s.index.get_indexer(idxs)
                if (pos < 1).any():
                    continue                        # needs a previous US close
                rets = s.values[pos] / s.values[pos - 1] - 1.0
                y[j] = float(np.prod(1.0 + rets) - 1.0)
                kcount[j] = len(idxs)
            x = pd.Series(np.where(pair_ok[1:], jk.values[1:] / jk.values[:-1] *
                                   fx.reindex(cal[1:]).values / fx.reindex(cal[:-1]).values - 1.0,
                                   np.nan), index=cal[1:])
            sig[nm] = {"y": y, "x": x, "k": kcount, "us_n": len(s)}

        # ------------------------------------------- beta / sigma / R / terciles
        CUT = 0.430727
        res_signals = {}
        for nm, st in sig.items():
            pairs = [(j, st["y"][j], float(st["x"].iloc[j - 1])) for j in sorted(st["y"])
                     if np.isfinite(st["x"].iloc[j - 1])]
            beta = {}; sR = {}
            xs = np.array([p[2] for p in pairs]); ys = np.array([p[1] for p in pairs])
            js = np.array([p[0] for p in pairs])
            for i in range(len(pairs)):
                j = js[i]
                lo = max(0, i - 250)
                xv, yv = xs[lo:i + 1], ys[lo:i + 1]
                if len(xv) < 120:
                    continue
                beta[j] = float(np.polyfit(xv, yv, 1)[0])
            # R series (PIT): R_j = y_j - beta_{j-1} * x_j  (beta from pairs ending <= j-1)
            R = {}
            for j in sorted(st["y"]):
                b = beta.get(j - 1)
                if b is None:
                    continue
                R[j] = st["y"][j] - b * float(st["x"].iloc[j - 1])
            Rj = np.array([R[j] for j in sorted(R)]); Rjd = np.array(sorted(R))
            sRd = {}
            for i in range(len(Rj)):
                lo = max(0, i - 250)
                if i + 1 < 120:
                    continue
                sRd[Rjd[i]] = float(Rj[max(0, i - 249):i + 1].std(ddof=1))
            sig_out = {}
            for j, r in R.items():
                s = sRd.get(j - 1)
                if s and s > 0:
                    sig_out[j] = {"R_std": r / s, "k": st["k"].get(j, 1)}
            res_signals[nm] = sig_out

        # ------------------------------------------------------------- runs
        def run_arm(nm, oc, gap, sp, k1_only=False):
            lo_s, hi_s = ((SPLIT_DATE, None) if sp == "confirmation" else (None, SPLIT_DATE))
            ys, xs, ds, ks = [], [], [], []
            for j, v in res_signals[nm].items():
                D = cal[j]
                if (lo_s and D < lo_s) or (hi_s and D >= hi_s) or D > END_FROZEN:
                    continue
                if k1_only and v["k"] != 1:
                    continue
                o = oc.iloc[j]
                if not np.isfinite(o):
                    continue
                ys.append(o); xs.append(v["R_std"]); ds.append(D); ks.append(v["k"])
            ys, xs = np.array(ys), np.array(xs)
            prim = nw_t(ys, xs)
            tb = ys[xs <= -CUT]; tt = ys[xs >= CUT]
            yrs = {}
            for yy in sorted({d.year for d in ds}):
                m = np.array([d.year == yy for d in ds])
                yrs[str(yy)] = {"n": int(m.sum()),
                                "slope": nw_t(ys[m], xs[m])["slope"],
                                "mean_oc_pct": round(100 * float(ys[m].mean()), 3)}
            return {"split": sp, "signal": nm, "n": prim["n"],
                    "slope_bp_per_1sigma": round(1e4 * prim["slope"], 2) if np.isfinite(prim["slope"]) else None,
                    "t": round(prim["t"], 3) if np.isfinite(prim["t"]) else None,
                    "tercile_bottom_mean_bp": round(1e4 * tb.mean(), 2) if len(tb) else None,
                    "tercile_top_mean_bp": round(1e4 * tt.mean(), 2) if len(tt) else None,
                    "n_bottom": int(len(tb)), "n_top": int(len(tt)),
                    "year_by_year": yrs, "k1_only_t": None,
                    "_ys": ys, "_xs": xs, "_ds": ds}

        res = {}
        for nm in arms_src:
            sp = "confirmation"
            res[f"{nm}-C"] = run_arm(nm, oc_e, gap_e, sp)
            res[f"{nm}-D"] = run_arm(nm, oc_e, gap_e, "discovery")
            res[f"{nm}-C_allrows"] = run_arm(nm, oc_a, gap_a, sp)
            res[f"{nm}-D_allrows"] = run_arm(nm, oc_a, gap_a, "discovery")
        res["TLK-C_tlkm"] = run_arm("TLK", oc_tlkm, gap_tlkm, "confirmation")
        res["TLK-D_tlkm"] = run_arm("TLK", oc_tlkm, gap_tlkm, "discovery")

        # absorption share (primary book, confirmation arms)
        for nm in ("EIDO", "TLK", "SPY"):
            key = f"{nm}-C" if nm != "TLK" else "TLK-C_tlkm"
            g = run_arm(nm, (gap_e if nm != "TLK" else gap_tlkm), gap_e, "confirmation")
            so = res[key]["slope_bp_per_1sigma"]
            sg = g["slope_bp_per_1sigma"]
            res[key]["absorption_share"] = (
                round(sg / (sg + so), 3) if (so is not None and sg is not None and (sg + so) != 0) else None)

        # k=1-only sensitivity (primary, confirmation)
        for nm in ("EIDO", "TLK", "SPY"):
            key = f"{nm}-C" if nm != "TLK" else "TLK-C_tlkm"
            k1 = run_arm(nm, oc_e if nm != "TLK" else oc_tlkm, gap_e, "confirmation", k1_only=True)
            res[key]["k1_only_t"] = k1["t"]

        # ------------------------------------------------------------ economics
        econ = {}
        for nm in ("EIDO", "TLK", "SPY"):
            key = f"{nm}-C" if nm != "TLK" else "TLK-C_tlkm"
            a = res[key]
            ys, xs, ds = a["_ys"], a["_xs"], a["_ds"]
            if len(ys):
                tb = ys[xs <= -CUT]; tt = ys[xs >= CUT]
                econ[nm] = {
                    "overlay_bottom_buy_bp": round(1e4 * -tb.mean(), 2) if len(tb) else None,
                    "overlay_top_sell_bp": round(1e4 * tt.mean(), 2) if len(tt) else None,
                    "affected_share_bottom": round(len(tb) / len(ys), 3),
                    "affected_share_top": round(len(tt) / len(ys), 3),
                    "standalone_top_net_060_bp": round(1e4 * tt.mean() - 1e4 * RT_FLOOR, 2) if len(tt) else None,
                }
            a.pop("_ys"); a.pop("_xs"); a.pop("_ds")
        for k, v in res.items():
            if isinstance(v, dict):
                for kk in ("_ys", "_xs", "_ds"):
                    v.pop(kk, None)
        out["economics_overlay_and_standalone"] = econ
        # D-059 modeled cost (book-level, top-tercile days), via committed cost functions
        try:
            spec = importlib.util.spec_from_file_location(
                "cost_by_adv", ROOT / "docs" / "research_programs" / "P-M" / "cost_liquidity" / "cost_by_adv.py")
            cb = importlib.util.module_from_spec(spec); spec.loader.exec_module(cb)
            fees = cb.FEES
            ar_terms = np.log(C) - (np.log(H) + np.log(L)) / 2
            ar_t = 4 * ar_terms * (np.r_[ar_terms[1:], np.full((1, ar_terms.shape[1]), np.nan)])
            ar_s = pd.DataFrame(ar_t, index=cal).rolling(21, min_periods=10).mean().apply(
                lambda col: np.sqrt(np.maximum(col, 0)))
            s_spread = np.maximum(ar_s.values, tickv)          # floored at one tick
            sig_d = pd.DataFrame(np.log(C), index=cal).diff().rolling(21, min_periods=10).std().values
            impact = 2.0 * sig_d * np.sqrt(Q_POS / np.maximum(A20, 1.0))
            cost_rt = fees + s_spread + impact                 # round trip per name-day
            # book-level modeled cost on top-tercile days (primary book weights)
            ws = np.nansum(np.where(eligible, W60, 0.0), axis=1)
            with np.errstate(divide="ignore", invalid="ignore"):
                w = np.where(eligible & (ws[:, None] > 0),
                             np.divide(W60, np.where(ws[:, None] > 0, ws[:, None], 1.0)), 0.0)
            cost_book = pd.Series(np.nansum(w * np.where(eligible, cost_rt, np.nan), axis=1), index=cal)
            for nm in ("EIDO", "SPY"):
                tt_days = [j for j, v in res_signals[nm].items()
                           if v["R_std"] >= CUT and cal[j] <= END_FROZEN
                           and cal[j] >= SPLIT_DATE and np.isfinite(oc_e.iloc[j])]
                mc = float(np.mean([cost_book.iloc[j] for j in tt_days])) if tt_days else np.nan
                tt = np.array([oc_e.iloc[j] for j in tt_days])
                econ[nm]["standalone_top_net_D059_bp"] = (
                    round(1e4 * tt.mean() - 1e4 * mc, 2) if len(tt) else None)
                econ[nm]["D059_book_cost_bp"] = round(1e4 * mc, 2) if np.isfinite(mc) else None
        except Exception as e:  # noqa: BLE001
            econ["D059_error"] = f"{type(e).__name__}: {e}"[:200]
        # TLKM standalone
        tlk_days = [j for j, v in res_signals["TLK"].items()
                    if v["R_std"] >= CUT and cal[j] <= END_FROZEN and cal[j] >= SPLIT_DATE
                    and np.isfinite(oc_tlkm.iloc[j])]
        if tlk_days:
            tt = np.array([oc_tlkm.iloc[j] for j in tlk_days])
            mc_tl = float(np.nanmean([cost_rt[cal[j], tl] for j in tlk_days]))
            econ.setdefault("TLK", {})["standalone_top_net_060_bp"] = round(1e4 * tt.mean() - 1e4 * RT_FLOOR, 2)
            econ["TLK"]["standalone_top_net_D059_bp"] = round(1e4 * tt.mean() - 1e4 * mc_tl, 2)
            econ["TLK"]["D059_cost_bp"] = round(1e4 * mc_tl, 2)

        # ------------------------------------------------- recorder correlation
        corr = {}
        for name, p in (("FADE-001", ROOT / "docs/research_programs/P-M/forward_fade/ledger.json"),
                        ("REGIME-002", ROOT / "docs/research_programs/P-M/forward_regime/ledger.json"),
                        ("VOLEX-001", ROOT / "docs/research_programs/P-M/forward_exclusion/ledger.json")):
            try:
                tr = json.loads(Path(p).read_text()).get("trades", [])
                cnt = pd.Series([str(t["entry_date"]) for t in tr]).value_counts()
                pairs = [(res_signals["EIDO"][j]["R_std"], float(cnt.get(str(cal[j].date()), 0.0)))
                         for j in res_signals["EIDO"] if str(cal[j].date()) in set(cnt.index)]
                if len(pairs) > 10:
                    a_, b_ = zip(*pairs)
                    corr[name] = {"n_days": len(pairs), "corr": round(float(np.corrcoef(a_, b_)[0, 1]), 3)}
                else:
                    corr[name] = {"n_days": len(pairs), "corr": None}
            except Exception as e:  # noqa: BLE001
                corr[name] = f"ERROR {type(e).__name__}: {e}"[:120]
        out["recorder_corr"] = corr
        out["arms"] = res
        out["ihsg_oc_confirmation_sigma_pct"] = round(100 * float(ihsg_oc[ihsg_oc.index >= SPLIT_DATE].std()), 3)

        run.metrics = {"arms_n": {k: v.get("n") for k, v in res.items() if isinstance(v, dict)}}
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        (HERE / f"RESULT_X1_{stamp}.json").write_text(json.dumps(out, indent=1, default=str))
        print("WROTE", HERE / f"RESULT_X1_{stamp}.json")
        for k in ("EIDO-C", "EIDO-D", "TLK-C_tlkm", "SPY-C"):
            a = res[k]
            print(k, "n", a["n"], "slope", a["slope_bp_per_1sigma"], "t", a["t"],
                  "absorb", a.get("absorption_share"))


def _tracking():
    from research.tracking import track_run
    return track_run(kind="x1_screen", params=out["params"])


if __name__ == "__main__":
    main()
