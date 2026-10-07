"""G1 one-shot runner — gated, WRITTEN AT G0, NOT RUN.

Executes only after owner/planner approval (SNIPER_FILTER_G1_APPROVED=1) and
only from the frozen tree. One run: features (frozen), X1 outcomes via the
frozen E.simulate_trade, the yearly-expanding embargoed refits, the frozen
selection rule, the five TEST pass-bar conditions and the also-report list ->
RESULT_<utc>.json. Any fix after the run is a new, disclosed, re-frozen run.
"""
from __future__ import annotations

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


def month_mean_r(rows: list, selected: dict, config: str) -> dict:
    """mean R of the SELECTED setups per setup month for one configuration."""
    per_month = {}
    for key, tr in rows.items():
        if selected[config].get(key):
            per_month.setdefault(tr["month"], []).append(tr["R"])
    return {m: float(np.nanmean(v)) for m, v in per_month.items()}


def main() -> None:
    if os.environ.get(SF.G1_ENV) != "1":
        raise SystemExit("G1 is gated: set SNIPER_FILTER_G1_APPROVED=1 only after "
                         "owner/planner approval of the frozen G0.")
    t0 = time.time()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    sidecar = {}
    for line in (HERE / "PREDECLARATION.sha256").read_text().strip().splitlines():
        h, n = line.split()
        sidecar[n] = h
    import hashlib
    for n in ("PREDECLARATION.md", "sniper_filter.py", "g0_census.py",
              "g1_run.py", "test_pit_sniper_filter.py"):
        got = hashlib.sha256((HERE / n).read_bytes()).hexdigest()
        if sidecar.get(n) != got:
            raise SystemExit(f"freeze check FAILED for {n}")

    P, ihsg_close, ihsg_ma200 = SF.load_dataset()
    owner, I_by_stock, pop = SF.build_population(P)
    rows = {}
    for tr in pop["sniper"]:
        oc = E.simulate_trade(tr, "X1", P, I_by_stock)
        tr = dict(tr, R=oc["R"], net_pct=oc["net_pct"], exit_idx=oc["exit_idx"])
        rows[(tr["ticker"], tr["s"])] = tr
    ft = SF.add_ranks(SF.feature_table(P, I_by_stock, pop, ihsg_close, ihsg_ma200))

    # outcomes-aware frame (labels + embargo fields); features are untouched
    df = ft.copy()
    df["R"] = [rows[k]["R"] for k in df.index]
    df["exit_pos"] = [rows[k]["exit_idx"] for k in df.index]
    df["label"] = (df["R"] > 0).astype(float)

    months = df["month"]
    first_pos = {y: SF.first_pos_of_year(P["close"].index, y) for y in range(2016, 2027)}

    def impute(X: pd.DataFrame, ref: pd.DataFrame) -> pd.DataFrame:
        med = ref.median(numeric_only=True)
        return X.fillna(med)

    configs = ["M0", "M1a", "M1b", "M2"]
    scores = {c: pd.Series(np.nan, index=df.index) for c in configs}
    for y in range(2016, 2027):
        tr_mask = SF.train_mask_for(df, y, first_pos[y])
        pred_mask = df["month"].str.startswith(str(y))
        if not pred_mask.any():
            continue
        # M0 needs no fit
        scores["M0"][pred_mask] = SF.m0_score(df)[pred_mask]
        Xtr_all = df[tr_mask]
        ytr = df.loc[tr_mask, "label"]
        for c, C in zip(("M1a", "M1b"), SF.M1_C_VALUES):
            clf = LogisticRegression(penalty="l2", C=C, solver="lbfgs",
                                     max_iter=1000, random_state=SF.SEED)
            Xtr = impute(Xtr_all[[f + "_r" for f in SF.FEATURES]], Xtr_all)
            clf.fit(Xtr.values, ytr.values)
            Xp = impute(df.loc[pred_mask, [f + "_r" for f in SF.FEATURES]], Xtr_all)
            scores[c][pred_mask] = clf.predict_proba(Xp.values)[:, 1]
        hgb = HistGradientBoostingClassifier(**SF.M2_PARAMS)
        hgb.fit(Xtr_all[[f + "_r" for f in SF.FEATURES]].values, ytr.values)
        scores["M2"][pred_mask] = hgb.predict_proba(
            df.loc[pred_mask, [f + "_r" for f in SF.FEATURES]].values)[:, 1]

    # M1 C choice on validation mean R of selected setups (frozen rule)
    val_mask = (months >= SF.VAL_START) & (months <= SF.VAL_END)
    val_choice = {}
    for c in ("M1a", "M1b"):
        sel = SF.select_mask(scores[c][val_mask], df.loc[val_mask, "pos"])
        val_choice[c] = float(np.nanmean(df.loc[val_mask, "R"][sel])) if sel.any() else float("nan")
    chosen = max(val_choice, key=lambda c: (val_choice[c] if np.isfinite(val_choice[c]) else -np.inf))

    test_mask = months >= SF.TEST_START
    results = {}
    for c in configs:
        sel = SF.select_mask(scores[c][test_mask], df.loc[test_mask, "pos"])
        sel_R = df.loc[test_mask, "R"][sel]
        all_R = df.loc[test_mask, "R"]
        # monthly selected vs all series (setup-month keyed)
        sel_by_m, all_by_m = {}, {}
        for k in df.index[test_mask]:
            m = df.loc[k, "month"]
            all_by_m.setdefault(m, []).append(df.loc[k, "R"])
            if bool(sel.get(k, False)):
                sel_by_m.setdefault(m, []).append(df.loc[k, "R"])
        months_sorted = sorted(all_by_m)
        diff = np.array([np.nanmean(sel_by_m.get(m, [np.nan]))
                         - np.nanmean(all_by_m[m]) for m in months_sorted])
        results[c] = {
            "n_selected": int(sel.sum()),
            "selected_mean_R": float(np.nanmean(sel_R)) if sel.any() else float("nan"),
            "all_mean_R": float(np.nanmean(all_R)),
            "win_rate_selected": float((sel_R > 0).mean()) if sel.any() else float("nan"),
            "nw_t_diff": nw_t(diff),
            "monthly_diff": {m: float(d) for m, d in zip(months_sorted, diff)},
            "h1": float(np.nanmean([d for m, d in zip(months_sorted, diff)
                                    if m <= "2023-12"])),
            "h2": float(np.nanmean([d for m, d in zip(months_sorted, diff)
                                    if m >= "2024-01"])),
        }
    # pass-bar condition 4: M1(chosen)/M2 vs M0 paired monthly t
    paired = {}
    for c in ("M1a", "M1b", "M2"):
        mm_c = month_mean_r({k: rows[k] for k in df.index},
                            {k: bool(SF.select_mask(scores[c][test_mask],
                                                     df.loc[test_mask, "pos"]).get(k, False))
                             for k in df.index}, c)
        mm_0 = month_mean_r({k: rows[k] for k in df.index},
                            {k: bool(SF.select_mask(scores["M0"][test_mask],
                                                    df.loc[test_mask, "pos"]).get(k, False))
                             for k in df.index}, "M0")
        common = sorted(set(mm_c) & set(mm_0))
        paired[c] = nw_t(np.array([mm_c[m] - mm_0[m] for m in common]))
    # PBO over the grid on the TRAIN+VAL months (frozen §7.5)
    pbo_rows = []
    grid_months = sorted({m for m in months if m <= SF.VAL_END})
    for c in configs:
        sel = SF.select_mask(scores[c][months <= SF.VAL_END],
                             df.loc[months <= SF.VAL_END, "pos"])
        by_m = {}
        for k in df.index[months <= SF.VAL_END]:
            if bool(sel.get(k, False)):
                by_m.setdefault(df.loc[k, "month"], []).append(df.loc[k, "R"])
        pbo_rows.append([np.nanmean(by_m.get(m, [np.nan])) for m in grid_months])
    pbo = pbo_cscv(np.array(pbo_rows).T, n_splits=16)

    result = {
        "populations": {"n_filled": len(rows)},
        "m1_validation_choice": {"means": val_choice, "chosen": chosen},
        "configs": results,
        "paired_vs_M0_nw_t": paired,
        "pbo": to_pure(pbo),
        "dataset_fingerprint": None,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "runtime_seconds": round(time.time() - t0, 1),
        "gates": {"env": f"{SF.G1_ENV}=1 (owner approval, single run)"},
    }
    with __import__("data.db", fromlist=["connect"]).connect(read_only=True) as conn:
        result["dataset_fingerprint"] = E.dataset_fingerprint(conn)
    out = HERE / f"RESULT_{stamp}.json"
    out.write_text(json.dumps(to_pure(result), indent=1) + "\n")
    print("WROTE", out.name)


if __name__ == "__main__":
    main()
