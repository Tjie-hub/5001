"""Phase 0 counts for the cross-asset overnight screen (X1 brief P0-D) · 2026-10-05.

COUNTS + UNCONDITIONAL statistics only. This script never computes a signal VALUE: no
R_D, no beta-hat regression against outcomes, nothing conditioned on the signal. It
counts (signal-calendar x outcome) day availability per arm/split, reads the
UNCONDITIONAL sigma of open->close outcomes (explicitly permitted by the brief for MDE
sizing), and produces the pre-2021 open-quality table, the survivorship line, and the
MDE per arm at the recomputed deflation bar (W0 recount: census 515 + 6 arms = 521).

Data rules honored:
- corpus prices through research.rulecard.data.load_extended_ohlcv(issuance=True)
  (D-064 D: new research runs set issuance=True and record it in params);
- ^JKSE and FX from the acquired cross_asset CSVs (signal/alignment side only);
- local walkforward.db is the corpus here (snapshot .zst not present on this host):
  its fingerprint + max(date) are recorded via research.tracking and disclosed.

Run from WSL:  DB_PATH=/mnt/d/IDX/data/walkforward.db ~/venv-x/bin/python ./phase0_counts_x1.py
Writes PHASE0_COUNTS.json next to this file.
"""
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]                      # broad_search_v2/x1 -> repo root
sys.path.insert(0, str(ROOT))

DATA = HERE / "data"
SPLIT_DATE = pd.Timestamp("2021-07-05")     # pre-declared halves (X1 brief)
BRIEF_SPLIT_START = pd.Timestamp("2010-05-01")  # brief's discovery start (EIDO-anchored)
ADV_MIN = 5e9                               # D-065/brief: adv20 >= Rp 5bn
BAR_N_CENSUS = 555                          # W0 recount + REVIEW_R1 1 additions (245+20+20)
BAR_N_WITH_X1 = 555 + 6                     # + this screen's 6 arms
out = {"params": {"issuance": True, "adv_min": ADV_MIN, "split_date": str(SPLIT_DATE),
                  "tick_max_frac": 0.005,
                  "db": "local walkforward.db (snapshot .zst NOT present on this host)",
                  "beta_warmup_min_pairs": 120, "beta_rolling": 250,
                  "max_us_sessions_in_gap": 3}}

# DrvFS hardening: the sanctioned connector gets mmap_size=0 (WSL/DrvFS SQLite
# requirement); the loader itself is not bypassed.
import data.db as _ddb                                      # noqa: E402
_orig_connect = _ddb.connect
def _connect_drvfs(*a, **k):
    c = _orig_connect(*a, **k)
    try:
        c.execute("PRAGMA mmap_size=0")
    except Exception:
        pass
    return c
_ddb.connect = _connect_drvfs

from research.tracking import track_run                     # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "bar_v2", ROOT / "docs" / "research_programs" / "deflation_audit" / "bar_v2.py")
_barm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_barm)
out["bar"] = {"at_recorded_census_276": round(_barm.e_max_abs_z(276), 4),
              "at_w0_recount_521": round(_barm.e_max_abs_z(521), 4),
              "at_w0_plus_r1_additions_555": round(_barm.e_max_abs_z(BAR_N_CENSUS), 4),
              "at_plus_x1_arms_561": round(_barm.e_max_abs_z(BAR_N_WITH_X1), 4)}


def _nth_sun_vec(years, mm, n):
    res = np.empty(len(years), dtype=int)
    for i, yy in enumerate(years):
        w = pd.Timestamp(year=yy, month=mm, day=1).weekday()
        res[i] = 1 + ((6 - w) % 7) + 7 * (n - 1)
    return res


def load_csv(name):
    df = pd.read_csv(DATA / name, parse_dates=["date"])
    return df.sort_values("date").reset_index(drop=True)


def main():
    with track_run(kind="x1_phase0_counts", params=out["params"]) as run:
        # ------------------------------------------------ corpus panel + outcomes
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
        g = P.groupby("ticker", sort=False)
        # adv20 / med60 of traded value, trailing (per ticker), then shifted one session
        tv = val.groupby(P["ticker"], sort=False)
        P["adv20"] = tv.transform(lambda x: x.rolling(20, min_periods=20).mean())
        P["med60"] = tv.transform(lambda x: x.rolling(60, min_periods=60).median())
        P["prev_close"] = P.groupby("ticker", sort=False)["close"].shift(1)
        P["adv20_d"] = P.groupby("ticker", sort=False)["adv20"].shift(1)   # known at d
        P["med60_d"] = P.groupby("ticker", sort=False)["med60"].shift(1)   # known at d
        P["prev_date"] = P.groupby("ticker", sort=False)["date"].shift(1)

        dates = np.sort(P["date"].unique())
        didx = {d: i for i, d in enumerate(dates)}
        T, N = len(dates), P["ticker"].nunique()
        tickers = np.sort(P["ticker"].unique())
        tix = {t: i for i, t in enumerate(tickers)}
        print(f"panel: {pd.Timestamp(dates[0]).date()} .. {pd.Timestamp(dates[-1]).date()}  T={T} N={N}", flush=True)

        def mat(col):
            M = np.full((T, N), np.nan)
            M[P["date"].map(didx).values, P["ticker"].map(tix).values] = P[col].values
            return M

        O, C, V = mat("open"), mat("close"), mat("volume")
        A20, W60 = mat("adv20_d"), mat("med60_d")
        PC = mat("prev_close")
        cal = pd.DatetimeIndex(dates)

        # ------------------------------------------- unconditional outcome series
        tl = tix.get("TLKM")
        liquid = (A20 >= ADV_MIN) & (V > 0) & (O > 0) & (C > 0)
        # TICK-ELIGIBILITY (REVIEW_R1 2.3, replaces the rejected valid-open filter):
        # ex-ante PIT rule computed at close(d) — a name joins the day-D book only
        # if tick(close_d)/close_d <= 0.5% (IDX tick schedule). Removes discreteness
        # noise without looking at day-D prints. The ALL-ROWS estimate is the
        # co-equal lens per the review.
        tickv = np.full_like(C, 1.0)
        tickv = np.where(PC < 200, 1.0, tickv)
        tickv = np.where((PC >= 200) & (PC < 500), 2.0, tickv)
        tickv = np.where((PC >= 500) & (PC < 2000), 5.0, tickv)
        tickv = np.where((PC >= 2000) & (PC < 5000), 10.0, tickv)
        tickv = np.where(PC >= 5000, 25.0, tickv)
        TICK_MAX = 0.005
        eligible = liquid & (np.divide(tickv, np.where(PC > 0, PC, np.nan),
                                       out=np.full_like(C, np.nan)) <= TICK_MAX)
        r_oc_v = np.where(eligible, C / O - 1.0, np.nan)
        wsum_v = np.nansum(np.where(eligible, W60, 0.0), axis=1)
        with np.errstate(divide="ignore", invalid="ignore"):
            w_v = np.where(eligible & (wsum_v[:, None] > 0),
                           np.divide(W60, np.where(wsum_v[:, None] > 0, wsum_v[:, None], 1.0)),
                           0.0)
        book_oc_v = pd.Series(np.nansum(w_v * r_oc_v, axis=1), index=cal)
        book_n_v = pd.Series(eligible.sum(axis=1), index=cal)
        tlkm_oc_v = (pd.Series(np.where(eligible[:, tl], C[:, tl] / O[:, tl] - 1.0, np.nan),
                               index=cal) if tl is not None else pd.Series(dtype=float))
        liquid = (A20 >= ADV_MIN) & (V > 0) & (O > 0) & (C > 0)
        r_oc = np.where(liquid, C / O - 1.0, np.nan)
        wsum = np.nansum(np.where(liquid, W60, 0.0), axis=1)
        with np.errstate(divide="ignore", invalid="ignore"):
            w_ = np.where(liquid & (wsum[:, None] > 0),
                          np.divide(W60, np.where(wsum[:, None] > 0, wsum[:, None], 1.0)),
                          0.0)
        book_oc = pd.Series(np.nansum(w_ * r_oc, axis=1), index=cal)
        book_n = pd.Series(liquid.sum(axis=1), index=cal)
        tlkm_oc = (pd.Series(C[:, tl] / O[:, tl] - 1.0, index=cal)
                   if tl is not None else pd.Series(dtype=float))
        ihsg_oc = ihsg.assign(oc=ihsg["close"] / ihsg["open"] - 1.0).set_index("date")["oc"]

        # ------------------------------------------------------- signal calendars
        eido = load_csv("eido.csv"); tlk = load_csv("tlk.csv"); spy = load_csv("spy.csv")
        jkse = load_csv("jkse.csv"); fx = load_csv("usdidr.csv")
        fx_dates = set(fx["date"])
        jkse_dates = set(jkse["date"])
        # signal availability per US-asset: session t usable iff t and t-1 (previous
        # US session in that CSV) exist -> a return over [t-1, t] exists.
        avail = {}
        for nm, df in (("EIDO", eido), ("TLK", tlk), ("SPY", spy)):
            d = pd.DatetimeIndex(df["date"])
            avail[nm] = set(d[1:])                       # has a previous US close
        n_us = {}
        for nm, df in (("EIDO", eido), ("TLK", tlk), ("SPY", spy)):
            d = pd.DatetimeIndex(df["date"])
            n_us[nm] = pd.Series(np.arange(len(d)), index=d)

        # warm-up: consecutive-pair availability for the JKSE-USD leg
        jk_ok = np.array([d in jkse_dates for d in cal])
        fx_ok = np.array([d in fx_dates for d in cal])
        pair_ok = jk_ok & fx_ok                          # pair (d-1 -> d) needs both
        pair_ok[0] = False
        cum_pairs = np.cumsum(pair_ok)                   # pairs ending <= this session

        # ------------------------------------------------------------- day loops
        splits = {"discovery": (None, SPLIT_DATE), "confirmation": (SPLIT_DATE, None)}
        arms = {"X1-A": ("EIDO", "book", "confirmation"), "X1-B": ("EIDO", "book", "discovery"),
                "X1-C": ("TLK", "TLKM", "confirmation"), "X1-D": ("TLK", "TLKM", "discovery"),
                "X1-E": ("SPY", "book", "confirmation"), "X1-F": ("SPY", "book", "discovery")}
        reasons = ["no_prev_idx_session", "us_holiday_no_signal", "fx_missing",
                   "beta_warmup", "gap_k_gt_3", "signal_leg_missing", "outcome_missing"]
        counts = {a: {r: 0 for r in reasons} for a in arms}
        usable = {a: {s: [] for s in splits} for a in arms}
        first_sig = {}
        for j in range(1, T):
            D = cal[j]; d = cal[j - 1]
            lo, hi = np.searchsorted(dates, d), np.searchsorted(dates, D)
            # US sessions t with d <= t <= D-1 (close 03:00/04:00 WIB inside window)
            win = {}
            for nm in n_us:
                s = n_us[nm]
                k = 0; last_t = None
                idxs = s.index[(s.index >= d) & (s.index < D)]
                k = len(idxs)
                if k:
                    last_t = idxs[-1]
                win[nm] = (k, last_t)
            for arm, (nm, oc, sp) in arms.items():
                lo_s, hi_s = splits[sp]
                if (lo_s and D < lo_s) or (hi_s and D >= hi_s):
                    continue
                k, last_t = win[nm]
                if last_t is None:
                    counts[arm]["us_holiday_no_signal"] += 1
                    continue
                if not (fx_ok[j - 1] and fx_ok[j]):
                    counts[arm]["fx_missing"] += 1
                    continue
                if cum_pairs[j - 1] < 120:
                    counts[arm]["beta_warmup"] += 1
                    first_sig.setdefault(arm, str(D.date()) + " (warm-up)")
                    continue
                if k > 3:
                    counts[arm]["gap_k_gt_3"] += 1
                    continue
                if avail[nm] and last_t not in avail[nm]:
                    counts[arm]["signal_leg_missing"] += 1
                    continue
                ok_oc = (book_n_v.iloc[j] >= 1) if oc == "book" else bool(
                    np.isfinite(tlkm_oc_v.iloc[j]))
                if not ok_oc:
                    counts[arm]["outcome_missing"] += 1
                    continue
                counts[arm].setdefault("usable", 0)
                counts[arm]["usable"] += 1
                usable[arm][sp].append(D)
                first_sig.setdefault(arm, str(D.date()))
        for arm in arms:
            for sp, lst in usable[arm].items():
                counts[arm][f"n_{sp}"] = len(lst)
                if sp == "discovery":
                    counts[arm]["n_discovery_brief_split_from_2010_05"] = int(
                        sum(1 for x in lst if x >= BRIEF_SPLIT_START))
                    counts[arm]["n_discovery_full_history"] = int(len(lst))

        # ------------------------------------------------------------ sigmas/MDE
        def sigma(series, lo, hi):
            s = series.dropna()
            if lo: s = s[s.index >= lo]
            if hi: s = s[s.index < hi]
            return float(s.std(ddof=1)), int(len(s))

        sig_book_c, n_book_c = sigma(book_oc_v, SPLIT_DATE, None)
        sig_book_d, n_book_d = sigma(book_oc_v, None, SPLIT_DATE)
        sig_tlkm_c, n_tlkm_c = sigma(tlkm_oc_v, SPLIT_DATE, None)
        sig_tlkm_d, n_tlkm_d = sigma(tlkm_oc_v, None, SPLIT_DATE)
        sig_ihsg_c, n_ihsg_c = sigma(ihsg_oc, SPLIT_DATE, None)
        sig_ihsg_d, n_ihsg_d = sigma(ihsg_oc, None, SPLIT_DATE)
        sig_book_c_u, n_book_c_u = sigma(book_oc, SPLIT_DATE, None)
        sig_book_d_u, n_book_d_u = sigma(book_oc, None, SPLIT_DATE)
        sig_tlkm_c_u, n_tlkm_c_u = sigma(tlkm_oc, SPLIT_DATE, None)
        sig_tlkm_d_u, n_tlkm_d_u = sigma(tlkm_oc, None, SPLIT_DATE)
        bar = out["bar"]["at_plus_x1_arms_561"]
        mde = {}
        for arm, (nm, oc, sp) in arms.items():
            s = sig_book_c if oc == "book" else sig_tlkm_c
            sd = sig_book_d if oc == "book" else sig_tlkm_d
            n = counts[arm].get("n_confirmation", 0)
            nd = counts[arm].get("n_discovery_brief_split_from_2010_05",
                                 counts[arm].get("n_discovery", 0))
            mde[arm] = {
                "mde_confirmation_bp_per_1sigma": round(1e4 * bar * s / np.sqrt(n), 2) if n else None,
                "mde_discovery_bp_per_1sigma": round(1e4 * bar * sd / np.sqrt(nd), 2) if nd else None,
                "mde_discovery_N_used": nd,
            }

        # ---------------------------------------------------- open-quality table
        oq = {}
        yr = cal.year
        liq_any = (A20 >= ADV_MIN)
        for y in range(cal.year.min(), cal.year.max() + 1):
            m = (np.asarray(yr) == y)
            rows = int(m.sum())
            if not rows:
                continue
            oq[str(y)] = {
                "session_rows": rows,
                "liquid_rows": int(liq_any[m].sum()),
                "open_eq_close_pct": round(float(np.nanmean(
                    (O[m] == C[m]).mean(axis=1)) * 100), 2),
                "open_eq_prev_close_pct": round(float(np.nanmean(
                    (O[m] == PC[m]).mean(axis=1)) * 100), 2),
                "zero_volume_rows_pct": round(float(np.mean(
                    (V[m] <= 0).mean(axis=1)) * 100), 2),
            }

        # ---------------------------------------------------------- survivorship
        longdb = ROOT / "data" / "history_long.db"
        if longdb.exists():
            import sqlite3
            con = sqlite3.connect(f"file:{longdb}?mode=ro", uri=True)
            L = pd.read_sql("SELECT ticker, MIN(date) f, MAX(date) l, COUNT(*) n "
                            "FROM ohlcv_long GROUP BY ticker", con)
            con.close()
            surv = {"tickers": int(len(L)),
                    "last_bar_before_2026": int((pd.to_datetime(L["l"]) < "2026-01-01").sum()),
                    "note": "history_long.db read-only; brief-standard survivorship line"}
        else:
            # history_long.db not present on this host: panel-derived fallback
            pre2021_any = np.isfinite(np.nanmax(
                np.where((cal < SPLIT_DATE)[:, None], C, np.nan), axis=0))
            last_idx = np.where(np.isfinite(C), np.arange(T)[:, None], -1).max(axis=0)
            last_date = pd.DatetimeIndex(dates[np.maximum(last_idx, 0)])
            dead26 = int((pre2021_any & (last_date < pd.Timestamp("2026-01-01"))).sum())
            n_pre = int(pre2021_any.sum())
            surv = {"history_long_db": "ABSENT on this host",
                    "panel_tickers_with_pre2021_data": n_pre,
                    "panel_pre2021_names_last_bar_before_2026": dead26,
                    "recorded_reference": ("memo 07 (2026-09-30): 54 of 929 ohlcv_long names "
                                           "end before 2026; delisted names are purged from "
                                           "Yahoo, so the blind spot is structural"),
                    "note": "panel-derived fallback; the recorded 54/929 line remains the brief-standard number"}

        fx_gap_days = int((~fx_ok[1:] & jk_ok[1:]).sum())
        out.update({
            "counts": counts, "first_signal_day_per_arm": first_sig,
            "unconditional_sigma_pct": {
                "book_open_to_close_TICK_ELIGIBLE": {"confirmation": round(100 * sig_book_c, 3), "n": n_book_c,
                                        "discovery": round(100 * sig_book_d, 3), "n_d": n_book_d},
                "TLKM_open_to_close_TICK_ELIGIBLE": {"confirmation": round(100 * sig_tlkm_c, 3), "n": n_tlkm_c,
                                        "discovery": round(100 * sig_tlkm_d, 3), "n_d": n_tlkm_d},
                "book_open_to_close_UNRESTRICTED_secondary": {"confirmation": round(100 * sig_book_c_u, 3),
                                        "n": n_book_c_u, "discovery": round(100 * sig_book_d_u, 3), "n_d": n_book_d_u},
                "TLKM_open_to_close_UNRESTRICTED_secondary": {"confirmation": round(100 * sig_tlkm_c_u, 3),
                                        "n": n_tlkm_c_u, "discovery": round(100 * sig_tlkm_d_u, 3), "n_d": n_tlkm_d_u},
                "IHSG_open_to_close": {"confirmation": round(100 * sig_ihsg_c, 3), "n": n_ihsg_c,
                                        "discovery": round(100 * sig_ihsg_d, 3), "n_d": n_ihsg_d,
                                        "note": "IHSG from corpus (2021-07+); discovery IHSG would come from ^JKSE (Yahoo, disclosed)"},
            },
            "mde_per_arm_bp_per_1sigma": mde,
            "open_quality_by_year": oq,
            "survivorship": surv,
            "fx_gap": {"idx_sessions_missing_fx_leg": fx_gap_days,
                       "note": "USDIDR=X gaps incl. 2003-05-01..2003-12-01 (214d) kill the USD-converted JKSE leg on those sessions"},
            "panel_end": str(cal[-1].date()),
        })
        run.metrics = {"usable_arms": {a: counts[a].get("usable", 0) for a in arms}}
        (HERE / "PHASE0_COUNTS.json").write_text(json.dumps(out, indent=1, default=str))
        print(json.dumps({k: out[k] for k in
                          ("bar", "counts", "first_signal_day_per_arm",
                           "unconditional_sigma_pct", "mde_per_arm_bp_per_1sigma")},
                         indent=1, default=str)[:4000])
        print("WROTE", HERE / "PHASE0_COUNTS.json")


if __name__ == "__main__":
    main()
