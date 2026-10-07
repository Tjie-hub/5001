"""G1 one-shot runner — gated, WRITTEN AT G0 (Revision 1), NOT RUN on real data.

Executes only after owner/planner approval (SNIPER_FILTER_G1_APPROVED=1) and
only from the frozen tree. One run: features (frozen, fill-aware reference
sets), X1 outcomes via the frozen E.simulate_trade, the yearly-expanding
embargoed refits, the frozen selection rule computed ONCE per configuration on
the FULL score series (R1) and indexed into val/test/PBO, the five TEST pass
conditions as COMPUTED booleans (R3), the mandatory also-report list (R4),
and PBO over the validation-months matrix only (R2).

Revision 1 (R6): the fingerprint gate runs BEFORE any outcome is computed,
against the frozen read-only DB SNAPSHOT, and SystemExit's on a mismatch.

`--synthetic`: a dry run on a synthetic panel with fake R — proves the RESULT
schema without touching real outcomes (allowed per the revision brief; writes
RESULT_SYNTHETIC_<utc>.json and nothing else).
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
if str(HERE.parents[3]) not in sys.path:
    sys.path.insert(0, str(HERE.parents[3]))

import sniper_filter as SF  # noqa: E402
import exit_study as E      # noqa: E402
from research.statistics import pbo_cscv  # noqa: E402
from sklearn.linear_model import LogisticRegression       # noqa: E402
from sklearn.ensemble import HistGradientBoostingClassifier  # noqa: E402

CONFIGS = ("M0", "M1a", "M1b", "M2")


def to_pure(o):
    if isinstance(o, dict):
        return {str(k): to_pure(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [to_pure(v) for v in o]
    if isinstance(o, bool) or isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, int) or isinstance(o, np.integer):
        return int(o)
    if isinstance(o, (float, np.floating)):
        v = float(o)
        return v if np.isfinite(v) else None
    if o is None or isinstance(o, str):
        return o
    return str(o)


def nw_t(series: np.ndarray, lag: int = 3) -> float:
    """Newey-West t (lag 3) that the mean of `series` is > 0."""
    x = np.asarray([v for v in series if np.isfinite(v)], dtype=float)
    n = len(x)
    if n < 3 or np.allclose(x, 0):
        return float("nan")
    mu = x.mean()
    e = x - mu
    g0 = float(np.sum(e * e)) / n
    g = g0
    for l in range(1, lag + 1):
        if n > l:
            g += 2.0 * (1.0 - l / (lag + 1.0)) * float(np.sum(e[l:] * e[:-l])) / n
    var = g / n
    return float(mu / np.sqrt(var)) if var > 0 else float("nan")


def monthly_diff_series(df: pd.DataFrame, sel: pd.Series, mask: pd.Series):
    """(months, diff) — the monthly mean R of SELECTED minus ALL setups, keyed
    on the setup month within `mask`."""
    sel_by_m, all_by_m = {}, {}
    sub = df[mask]
    for k, row in sub.iterrows():
        m = row["month"]
        all_by_m.setdefault(m, []).append(row["R"])
        if bool(sel.get(k, False)):
            sel_by_m.setdefault(m, []).append(row["R"])
    months = sorted(all_by_m)
    diff = np.array([np.nanmean(sel_by_m.get(m, [np.nan])) - np.nanmean(all_by_m[m])
                     for m in months])
    return months, diff


def run_pipeline(df: pd.DataFrame, first_pos: dict, val_mask: pd.Series,
                 test_mask: pd.Series, synth: bool = False) -> dict:
    """The frozen pipeline on a prepared frame (features+labels+exit_pos).
    Returns the full RESULT payload (no I/O)."""
    feat_cols = [f + "_r" for f in SF.FEATURES]
    score_years = range(2016, 2027)
    scores = {c: pd.Series(np.nan, index=df.index) for c in CONFIGS}
    for y in score_years:
        tr_mask = SF.train_mask_for(df, y, first_pos[y])
        pred_mask = df["month"].str.startswith(str(y))
        if not pred_mask.any():
            continue
        scores["M0"][pred_mask] = SF.m0_score(df)[pred_mask]
        Xtr_all = df.loc[tr_mask, feat_cols]
        ytr = df.loc[tr_mask, "label"]
        med = Xtr_all.median(numeric_only=True)
        for c, C in zip(("M1a", "M1b"), SF.M1_C_VALUES):
            clf = LogisticRegression(penalty="l2", C=C, solver="lbfgs",
                                     max_iter=1000, random_state=SF.SEED)
            clf.fit(Xtr_all.fillna(med).values, ytr.values)
            Xp = df.loc[pred_mask, feat_cols].fillna(med)
            scores[c][pred_mask] = clf.predict_proba(Xp.values)[:, 1]
        hgb = HistGradientBoostingClassifier(**SF.M2_PARAMS)
        hgb.fit(Xtr_all.values, ytr.values)
        scores["M2"][pred_mask] = hgb.predict_proba(
            df.loc[pred_mask, feat_cols].values)[:, 1]

    # R1: selection computed ONCE per configuration on the FULL score series,
    # then indexed into val/test (no subset windows).
    sel_full = {c: SF.select_mask(scores[c], df["pos"], df["fill_pos"])
                for c in CONFIGS}
    sel_val = {c: sel_full[c][val_mask] for c in CONFIGS}
    sel_test = {c: sel_full[c][test_mask] for c in CONFIGS}
    # Revision 2 V2: per-configuration fallback-tier usage
    tier_counts = {}
    for c in CONFIGS:
        t = SF.select_tiers(scores[c], df["pos"], df["fill_pos"])
        tier_counts[c] = {
            "window": int((t == SF.SELECT_TIER_WINDOW).sum()),
            "all_known": int((t == SF.SELECT_TIER_ALL_KNOWN).sum()),
            "unselected": int((t == SF.SELECT_TIER_UNSELECTED).sum()),
            "unscored": int(scores[c].isna().sum()),
        }

    # M1 C choice on validation mean R of selected setups (frozen rule)
    val_choice = {}
    for c in ("M1a", "M1b"):
        r = df.loc[val_mask, "R"][sel_val[c]]
        val_choice[c] = float(np.nanmean(r)) if sel_val[c].any() else float("nan")
    finite = {c: v for c, v in val_choice.items() if np.isfinite(v)}
    chosen = (max(finite, key=finite.get) if finite
              else "M1a")  # degenerate synthetic fallback; disclosed if hit

    results = {}
    for c in CONFIGS:
        sel = sel_test[c]
        sel_R = df.loc[test_mask, "R"][sel]
        all_R = df.loc[test_mask, "R"]
        months, diff = monthly_diff_series(df, sel_full[c], test_mask)
        n_sel = int(sel.sum())
        res = {
            "n_selected": n_sel,
            "n_test": int(test_mask.sum()),
            "selected_mean_R": float(np.nanmean(sel_R)) if n_sel else float("nan"),
            "selected_win_rate": float((sel_R > 0).mean()) if n_sel else float("nan"),
            "all_mean_R": float(np.nanmean(all_R)),
            "nw_t_diff": nw_t(diff),
            "h1_diff": float(np.nanmean([d for m, d in zip(months, diff)
                                         if m <= "2023-12"])) if months else float("nan"),
            "h2_diff": float(np.nanmean([d for m, d in zip(months, diff)
                                         if m >= "2024-01"])) if months else float("nan"),
        }
        # R4.3 robustness row: drop fill-bar exits (hold == 0)
        hold = df.loc[test_mask, "exit_pos"] - df.loc[test_mask, "pos"]
        keep = hold > 0
        sel_rb = sel[keep]
        sel_R_rb = df.loc[test_mask, "R"][keep][sel_rb]
        months_rb, diff_rb = monthly_diff_series(
            df, sel_full[c] & keep, test_mask & keep)
        res["robust_no_fillbar"] = {
            "n_dropped_fillbar": int((~keep).sum()),
            "n_selected": int(sel_rb.sum()),
            "selected_mean_R": float(np.nanmean(sel_R_rb)) if sel_rb.any() else float("nan"),
            "nw_t_diff": nw_t(diff_rb),
        }
        results[c] = res

    # R3: computed pass flags. Condition 4 uses the validation-chosen M1 only.
    pbo = None
    # R2: PBO matrix = the 4 configurations' monthly selected-mean-R over the
    # VALIDATION months only (all four have out-of-sample scores there); drop
    # months where any configuration has no selection; assert no NaN remains.
    val_months = sorted({m for m in df.loc[val_mask, "month"]})
    rows = []
    kept_months = []
    dropped = 0
    for m in val_months:
        mm = df["month"] == m
        row = []
        ok = True
        for c in CONFIGS:
            r = df.loc[mm, "R"][sel_full[c][mm]]
            if not len(r):
                ok = False
                break
            row.append(float(np.nanmean(r)))
        if ok:
            rows.append(row)
            kept_months.append(m)
        else:
            dropped += 1
    mat = np.array(rows, dtype=float)
    assert not np.isnan(mat).any(), "PBO matrix still has NaN after month drop"
    n_splits = 16
    while n_splits > 2 and len(mat) // n_splits < 2:
        n_splits -= 2
    if len(mat) >= 4 and len(mat) // n_splits >= 2:
        pbo = pbo_cscv(mat, n_splits=n_splits)
        pbo = to_pure(pbo)
        pbo["n_rows"] = len(mat)
        pbo["n_months_dropped_no_selection"] = dropped
        pbo["n_splits_frozen"] = n_splits
    else:
        # degenerate (synthetic-schema runs); the real panel has ~69 val months
        pbo = {"pbo": None, "n_rows": len(mat),
               "n_months_dropped_no_selection": dropped,
               "reason": "fewer than 4 usable months — PBO not computable"}

    for c in CONFIGS:
        r = results[c]
        c1_t_ok = bool(np.isfinite(r["nw_t_diff"]) and r["nw_t_diff"] >= SF.BAR_PRIMARY)
        c2_ok = bool(np.isfinite(r["selected_mean_R"]) and r["selected_mean_R"] > 0)
        c3_ok = bool(np.isfinite(r["h1_diff"]) and r["h1_diff"] > 0
                     and np.isfinite(r["h2_diff"]) and r["h2_diff"] > 0)
        r["pass_conditions"] = {
            "c1_nw_t_ge_bar_primary": c1_t_ok,
            "c1_nw_t_value": r["nw_t_diff"],
            "c1_bar_primary": SF.BAR_PRIMARY,
            "c1_bar_secondary_line": {          # R8 secondary reporting line
                "bar": SF.BAR_SECONDARY,
                "would_pass": bool(np.isfinite(r["nw_t_diff"])
                                   and r["nw_t_diff"] >= SF.BAR_SECONDARY),
            },
            "c2_selected_mean_R_gt_0": c2_ok,
            "c3_both_halves_gt_0": c3_ok,
        }
        if c in ("M1a", "M1b") and c != chosen:
            r["pass_conditions"]["c4_beats_M0"] = False
            r["pass_conditions"]["c4_note"] = "not the validation-chosen M1; cannot pass"
        r["pass_conditions"]["c5_pbo_lt_05"] = bool(pbo["pbo"] is not None
                                                    and pbo["pbo"] < 0.5)
        r["passes"] = bool(all(v for k, v in r["pass_conditions"].items()
                               if isinstance(v, bool)))

    # condition 4: chosen M1 / M2 vs M0, paired monthly t on selected mean R
    mm = {c: dict(zip(*monthly_diff_series(df, sel_full[c], df["month"] != "")))
          for c in CONFIGS}
    common_m = sorted(set.intersection(*[{m for m in mm[c] if np.isfinite(mm[c][m])}
                                         for c in CONFIGS]))
    paired = {c: nw_t(np.array([mm[c][m] - mm["M0"][m] for m in common_m]))
              for c in ("M1a", "M1b", "M2")}
    results[chosen]["pass_conditions"]["c4_beats_M0_nw_t"] = paired[chosen]
    results[chosen]["pass_conditions"]["c4_beats_M0"] = bool(
        np.isfinite(paired[chosen]) and paired[chosen] >= 2.0)
    results["M2"]["pass_conditions"]["c4_beats_M0_nw_t"] = paired["M2"]
    results["M2"]["pass_conditions"]["c4_beats_M0"] = bool(
        np.isfinite(paired["M2"]) and paired["M2"] >= 2.0)
    for c in CONFIGS:   # recompute `passes` with c4 resolved
        r = results[c]
        flags = r["pass_conditions"]
        bools = [v for k, v in flags.items() if isinstance(v, bool)]
        r["passes"] = bool(all(bools))
        # Owner ruling 560522a: the secondary (3.07 / N=280) line is report-only
        # and can never pass a configuration; this field is information only.
        r["would_pass_under_secondary_bar_report_only"] = bool(
            not flags["c1_nw_t_ge_bar_primary"]
            and flags["c1_bar_secondary_line"]["would_pass"]
            and all(v for k, v in flags.items()
                    if isinstance(v, bool) and k != "c1_nw_t_ge_bar_primary"))

    # R4.1 year-by-year table per configuration
    year_table = {}
    years = sorted({m[:4] for m in df["month"]})
    for c in CONFIGS:
        per_year = {}
        for y in years:
            msk = df["month"].str.startswith(y)
            per_year[y] = {
                "n_all": int(msk.sum()),
                "n_selected": int(sel_full[c][msk].sum()),
                "mean_R_selected": float(np.nanmean(df.loc[msk, "R"][sel_full[c][msk]]))
                if sel_full[c][msk].any() else None,
                "mean_R_all": float(np.nanmean(df.loc[msk, "R"])),
            }
        year_table[c] = per_year

    # R4.2 per-feature R-quintile spreads, val and test reported separately
    quintiles = {}
    for period_name, msk in (("validation", val_mask), ("test", test_mask)):
        sub = df[msk]
        q = {}
        for f in SF.FEATURES:
            fr = sub[f + "_r"]
            spreads = {}
            for c in CONFIGS:
                sel = sel_full[c][msk]
                top = sub.loc[sel, "R"][fr[sel] >= np.nanquantile(fr[sel], 0.8)] \
                    if sel.any() else pd.Series(dtype=float)
                bot = sub.loc[sel, "R"][fr[sel] <= np.nanquantile(fr[sel], 0.2)] \
                    if sel.any() else pd.Series(dtype=float)
                spreads[c] = {
                    "q5_minus_q1_selected_mean_R":
                        float(np.nanmean(top) - np.nanmean(bot))
                        if len(top) and len(bot) else None,
                }
            # raw (unselected) univariate spread — the brief's diagnostic
            ranks = fr.dropna()
            if len(ranks) >= 5:
                qs = np.nanquantile(ranks, [0.2, 0.4, 0.6, 0.8])
                lab = np.digitize(fr.values, qs)
                means = [float(np.nanmean(sub["R"][(lab == i) & np.isfinite(fr.values)]))
                         if ((lab == i) & np.isfinite(fr.values)).any() else None
                         for i in range(5)]
                spreads["all_setups_quintile_mean_R"] = means
            q[f] = spreads
        quintiles[period_name] = q

    return {
        "configs": results,
        "m1_validation_choice": {"means": val_choice, "chosen": chosen},
        "pbo": pbo,
        "paired_vs_M0_nw_t_all_configs": paired,
        "year_by_year": year_table,
        "feature_quintile_spreads": quintiles,
        "selection_tier_counts": tier_counts,
        "bars": {"primary": {"n": SF.CENSUS_N_PRIMARY, "bar": SF.BAR_PRIMARY},
                 "secondary": {"n": SF.CENSUS_N_SECONDARY, "bar": SF.BAR_SECONDARY}},
        "synthetic": synth,
    }


def build_real_frame() -> pd.DataFrame:
    """Real data: features (no outcome read before this point), then X1
    outcomes — called ONLY under the approval gate."""
    P = SF.load_dataset()
    owner, I_by_stock, pop = SF.build_population(P)
    mkt = SF.market_index(P, owner)
    mkt_ma200 = mkt.rolling(200, min_periods=200).mean()
    rows = {}
    for tr in pop["sniper"]:
        oc = E.simulate_trade(tr, "X1", P, I_by_stock)
        tr = dict(tr, R=oc["R"], exit_idx=oc["exit_idx"])
        rows[(tr["ticker"], tr["s"])] = tr
    ft = SF.add_ranks(SF.feature_table(P, I_by_stock, pop, mkt, mkt_ma200))
    df = ft.copy()
    df["R"] = [rows[k]["R"] for k in df.index]
    df["exit_pos"] = [rows[k]["exit_idx"] for k in df.index]
    df["label"] = (df["R"] > 0).astype(float)
    return df


def build_synthetic_frame() -> pd.DataFrame:
    """Synthetic panel + FAKE R: proves the RESULT schema; no real outcomes."""
    rng = np.random.default_rng(SF.SEED)
    n = 4200
    idx = pd.bdate_range("2015-01-01", periods=n)
    n_tk = 6
    base = {tk: 100.0 * np.cumprod(1 + rng.normal(0.0004, 0.015, n))
            for tk in ("A", "B", "C", "D", "E", "F")[:n_tk]}
    P = {}
    for f, agg in (("open", lambda a: a), ("close", lambda a: a),
                   ("high", lambda a: a * 1.01), ("low", lambda a: a * 0.99)):
        P[f] = pd.DataFrame({tk: agg(a) for tk, a in base.items()}, index=idx)
    P["volume"] = pd.DataFrame({tk: np.full(n, 3.0e9) for tk in base}, index=idx)
    owner, I_by_stock, pop = SF.build_population(P)
    if len(pop["sniper"]) < 50:
        raise SystemExit("synthetic fixture produced too few setups "
                         f"({len(pop['sniper'])})")
    mkt = SF.market_index(P, owner)
    mkt_ma200 = mkt.rolling(200, min_periods=200).mean()
    # FAKE R: synthetic, deterministic, no relation to any real outcome
    rows = {}
    for i, tr in enumerate(pop["sniper"]):
        rows[(tr["ticker"], tr["s"])] = dict(tr, R=float(rng.normal(0.02, 0.3)),
                                             exit_idx=tr["s"] + 1 + int(rng.integers(0, 30)))
    ft = SF.add_ranks(SF.feature_table(P, I_by_stock, pop, mkt, mkt_ma200))
    df = ft.copy()
    df["R"] = [rows[k]["R"] for k in df.index]
    df["exit_pos"] = [rows[k]["exit_idx"] for k in df.index]
    df["label"] = (df["R"] > 0).astype(float)
    return df


def main() -> None:
    synth = "--synthetic" in sys.argv
    if not synth and os.environ.get(SF.G1_ENV) != "1":
        raise SystemExit("G1 is gated: set SNIPER_FILTER_G1_APPROVED=1 only after "
                         "owner/planner approval of the frozen G0.")
    t0 = time.time()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    sidecar = {}
    for line in (HERE / "PREDECLARATION.sha256").read_text().strip().splitlines():
        h, n = line.split()
        sidecar[n] = h
    for n in ("PREDECLARATION.md", "sniper_filter.py", "g0_census.py",
              "g1_run.py", "test_pit_sniper_filter.py"):
        got = hashlib.sha256((HERE / n).read_bytes()).hexdigest()
        if sidecar.get(n) != got:
            raise SystemExit(f"freeze check FAILED for {n}")
    print("freeze checks: OK (Revision 1 sidecar)")

    # R6: fingerprint gate BEFORE any outcome is computed; SystemExit on drift.
    fp = None
    if not synth:
        fp = SF.fingerprint_from_snapshot()      # raises SystemExit on mismatch
        print("snapshot fingerprint:", fp["sha256"][:16],
              "| matches freeze:", fp["sha256"] == SF.G1_FINGERPRINT)
        if fp["sha256"] != SF.G1_FINGERPRINT:
            raise SystemExit("STOP: snapshot fingerprint drifted from the frozen "
                             "f42275e3… — no outcome computed, run refused")

    if synth:
        df = build_synthetic_frame()
        # remap the synthetic frame's months onto the frozen schedule so the
        # split logic runs end-to-end (fake data, fake mapping — schema proof);
        # spread across 2008..2026 so the train era exists for the 2016 refits
        uniq = sorted({m for m in df["month"]})
        mapm = {m: f"{min(2008 + (i * 18) // len(uniq), 2026)}-{m[5:7]}"
                for i, m in enumerate(uniq)}
        df["month"] = [mapm[m] for m in df["month"]]
    else:
        df = build_real_frame()
    months = df["month"]
    cal = pd.bdate_range("2001-01-01", periods=8000)  # first-session-of-year positions
    first_pos = {y: SF.first_pos_of_year(cal, y) for y in range(2016, 2027)}
    val_mask = (months >= SF.VAL_START) & (months <= SF.VAL_END)
    test_mask = months >= SF.TEST_START
    if not test_mask.any():
        raise SystemExit("no test-month rows — refusing")

    result = run_pipeline(df, first_pos, val_mask, test_mask, synth=synth)
    result.update({
        "n_rows": int(len(df)),
        "n_val": int(val_mask.sum()),
        "n_test": int(test_mask.sum()),
        "dataset_fingerprint": fp,
        "g1_fingerprint": SF.G1_FINGERPRINT,
        "snapshot_path": SF.SNAPSHOT_PATH,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "runtime_seconds": round(time.time() - t0, 1),
        "gates": {"env": f"{SF.G1_ENV}=1 (owner approval, single run)"
                  if not synth else "SYNTHETIC dry run — no real outcome touched",
                  "single_run": not synth},
    })
    prefix = "RESULT_SYNTHETIC_" if synth else "RESULT_"
    out = HERE / f"{prefix}{stamp}.json"
    out.write_text(json.dumps(to_pure(result), indent=1) + "\n")
    print("WROTE", out.name)
    for c in CONFIGS:
        print(c, "passes:", result["configs"][c]["passes"],
              "| flags:", {k: v for k, v in
                           result["configs"][c]["pass_conditions"].items()
                           if isinstance(v, bool)})


if __name__ == "__main__":
    main()
