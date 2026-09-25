"""Exploratory in-sample split of the T1 (HYP-PM-0010, spec 002) reference trades by the
retail universe screen of SCREEN_HYPOTHESIS_2026-09-25.md.

Filters and interpretation rules are frozen in PREDECLARATION.md (D-058) and must not be edited
here: P200 (close >= 200), A5 (adv20 >= Rp 5e9), P200+A5. Trades come unchanged from the audited
replication `overlap_audit.t1_trades`, registration-era corpus only (data <= 2026-09-16).

DESCRIPTIVE ONLY. Nothing here changes FWD-PM-REGIME-002's frozen universe, ledger or decision rule.

    venv/bin/python docs/research_programs/P-M/universe_screen/screen_split.py
"""
import importlib.util
import json
import os
from datetime import datetime, timezone

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
OA_PATH = os.path.join(HERE, "..", "overlap_audit", "overlap_audit.py")
DATA_CUTOFF = "2026-09-16"
FILTERS = {
    "P200": lambda t: t.close >= 200,
    "A5": lambda t: t.adv20 >= 5e9,
    "P200+A5": lambda t: (t.close >= 200) & (t.adv20 >= 5e9),
}


def overlap_audit():
    spec = importlib.util.spec_from_file_location("overlap_audit", OA_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def diff_t_month(y, dummy, months):
    """OLS y = a + b*dummy; CR1 standard error of b clustered by month."""
    y = np.asarray(y, float)
    X = np.column_stack([np.ones(len(y)), np.asarray(dummy, float)])
    XtX_inv = np.linalg.inv(X.T @ X)
    beta = XtX_inv @ X.T @ y
    e = y - X @ beta
    meat = np.zeros((2, 2))
    groups = pd.Series(np.arange(len(y))).groupby(np.asarray(months)).indices
    for idx in groups.values():
        s = X[idx].T @ e[idx]
        meat += np.outer(s, s)
    G, n, k = len(groups), len(y), 2
    V = XtX_inv @ meat @ XtX_inv * (G / (G - 1)) * ((n - 1) / (n - k))
    return 100 * beta[1], beta[1] / np.sqrt(V[1, 1])


def stats(OA, S, cal):
    if len(S) < 3:
        return {"N": int(len(S))}
    x, dates = S.exc.values, S.date.values
    months = pd.DatetimeIndex(dates).to_period("M").astype(str)
    mu, t_reg = OA.cluster_t(x, dates)
    _, t_month = OA.cluster_t(x, months)
    _, t_dk = OA.dk_t(x, dates, cal, 60)
    return {"N": int(len(S)), "mean_pct": round(100 * mu, 3), "t_entrydate_ref": round(t_reg, 2),
            "t_month": round(t_month, 2), "t_dk60": round(t_dk, 2)}


def main():
    OA = overlap_audit()
    D, ca = OA.load(DATA_CUTOFF)
    T, d, _ = OA.t1_trades(D, ca)
    T = T.merge(d[["ticker", "date", "close", "adv20"]], on=["ticker", "date"], how="left")
    assert T.close.notna().all() and T.adv20.notna().all(), "entry close/adv20 missing"
    cal = pd.DatetimeIndex(np.sort(d.date.unique()))

    out = {"generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "data_cutoff": DATA_CUTOFF, "predeclaration": "PREDECLARATION.md", "descriptive_only": True,
           "trades": int(len(T)),
           "entry_close_quantiles": T.close.quantile([.1, .25, .5, .75, .9]).round(0).to_dict(),
           "entry_adv20_bn_quantiles": (T.adv20 / 1e9).quantile([.1, .25, .5, .75, .9]).round(2).to_dict(),
           "periods": {}, "verdicts": {}}
    periods = {"FULL": T, "ex-2025": T[pd.DatetimeIndex(T.date).year != 2025]}
    for pname, P in periods.items():
        months = pd.DatetimeIndex(P.date).to_period("M").astype(str)
        res = {"universe": stats(OA, P, cal)}
        for fname, f in FILTERS.items():
            m = f(P).values
            dm, dt = diff_t_month(P.exc.values, m, months)
            res[fname] = {"in": stats(OA, P[m], cal), "out": stats(OA, P[~m], cal),
                          "share_in": round(float(m.mean()), 3),
                          "diff_in_minus_out_pct": round(dm, 3), "diff_t_month": round(dt, 2)}
        out["periods"][pname] = res

    for fname in FILTERS:
        ge = [out["periods"][p][fname]["in"]["mean_pct"] >= out["periods"][p]["universe"]["mean_pct"]
              for p in periods]
        label = ("filter does no harm" if all(ge) else
                 "filter costs return" if not any(ge) else "mixed")
        detected = all(abs(out["periods"][p][fname]["diff_t_month"]) >= 2.0 for p in periods)
        out["verdicts"][fname] = {"label": label, "in_minus_out": "detected" if detected
                                  else "no detectable difference"}

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = os.path.join(HERE, f"RESULT_{stamp}.json")
    with open(path, "w") as fh:
        json.dump(out, fh, indent=1, default=str)
    print(json.dumps(out, indent=1, default=str))
    print(f"\nwritten {path}")


if __name__ == "__main__":
    main()
