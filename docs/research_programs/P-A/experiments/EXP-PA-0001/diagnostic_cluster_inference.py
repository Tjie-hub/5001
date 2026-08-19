#!/usr/bin/env python3
"""
EXP-PA-0001 — post-hoc INFERENCE DIAGNOSTIC (not a re-run).

Purpose: EXP-PA-0001's verdict (REFUTED, F2) is already sealed and TERMINAL (HL-3).
This script does not touch that verdict. It only asks a narrower question: with
G=13 clusters, how much should we trust CR1 asymptotic inference on the reported
figures -- in particular the ADD-side gross figure (+1.8911%, CI95 [+0.6677%,
+3.1144%]), whose lower bound sits close to zero and which is not itself a
capturable/decision-basis claim in the confirmatory test.

Inputs:  docs/research_programs/P-A/experiments/EXP-PA-0001/results.json (read-only)
Outputs: docs/research_programs/P-A/experiments/EXP-PA-0001/diagnostic_cluster_inference.json

Does NOT modify run_exp_pa_0001.py, results.json, or execution.log.
Does NOT touch the database. Does NOT create close-out artifacts.

Methods:
  (A) Exact wild cluster bootstrap (Rademacher, null-imposed), G=13 -> enumerate
      all 2^13 = 8192 sign vectors exactly (zero Monte Carlo error).
  (B) Leave-one-cluster-out jackknife (13 review dates, drop one at a time).
  (C) Per-review-date descriptive breakdown (n, n_ADD, n_DELETE, means).
"""
import hashlib
import itertools
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy import stats

HERE = Path(__file__).resolve().parent
RESULTS_PATH = HERE / "results.json"
OUT_JSON = HERE / "diagnostic_cluster_inference.json"

ALPHA = 0.05


# ── CR1 (Liang-Zeger sandwich) for a mean, X = ones, K = 1 ──────────────────────
# Mirrors run_exp_pa_0001.py::cr1_mean exactly (same formula), plus an asymptotic
# p-value derived from the same t/df via scipy.
def cr1_mean(y, clusters):
    y = np.asarray(y, dtype=float)
    n = y.size
    groups = sorted(set(clusters))
    G = len(groups)
    mu = float(y.mean())
    resid = y - mu

    meat = 0.0
    for g in groups:
        idx = [i for i, c in enumerate(clusters) if c == g]
        meat += float(resid[idx].sum()) ** 2

    if n < 2 or G < 2:
        return dict(n=n, n_clusters=G, mean=mu, se=float("nan"), t=float("nan"),
                    df=max(G - 1, 0), ci95=[float("nan"), float("nan")],
                    excludes_zero=False, p_asymptotic=float("nan"))

    v = meat / (n ** 2)
    c = (G / (G - 1.0)) * ((n - 1.0) / (n - 1.0))  # K=1 -> second factor == 1
    se = math.sqrt(v * c)
    tstat = mu / se if se > 0 else float("nan")
    df = G - 1
    tcrit = float(stats.t.ppf(1 - ALPHA / 2.0, df))
    lo, hi = mu - tcrit * se, mu + tcrit * se
    p_asym = float(2.0 * stats.t.sf(abs(tstat), df)) if se > 0 else float("nan")
    return dict(n=n, n_clusters=G, mean=mu, se=se, t=tstat, df=df, t_crit=tcrit,
                ci95=[lo, hi], excludes_zero=bool(lo > 0 or hi < 0),
                p_asymptotic=p_asym)


# ── (A) Exact wild cluster bootstrap, Rademacher, null-imposed ─────────────────
def exact_wcb(y, clusters, t_obs):
    """Enumerate all 2^G Rademacher sign vectors exactly (null-imposed: since
    H0: mu=0, the restricted residual e_i = y_i, so y*_i = w_g * y_i).

    For each replication, mu* and SE_CR1(y*) are recomputed unrestricted (i.e.
    centered on mu*, not on 0) -- this is the standard WCR (restricted wild
    cluster bootstrap) construction: null imposed on the DGP, not on the
    test-statistic formula.
    """
    y = np.asarray(y, dtype=float)
    groups = sorted(set(clusters))
    G = len(groups)
    gidx = {g: i for i, g in enumerate(groups)}
    N = y.size

    S = np.zeros(G)   # per-cluster sum of y
    n_g = np.zeros(G)  # per-cluster count
    for yi, ci in zip(y, clusters):
        gi = gidx[ci]
        S[gi] += yi
        n_g[gi] += 1

    c_factor = G / (G - 1.0)

    count_ge = 0
    total = 0
    t_obs_abs = abs(t_obs)
    for signs in itertools.product((1.0, -1.0), repeat=G):
        w = np.array(signs)
        Sstar = w * S                      # per-cluster sum of y*
        mu_star = float(Sstar.sum() / N)
        resid_cluster_sum = Sstar - n_g * mu_star   # sum_{i in g} (y*_i - mu*)
        meat_star = float(np.sum(resid_cluster_sum ** 2))
        v_star = meat_star / (N ** 2)
        se_star = math.sqrt(v_star * c_factor)
        if se_star > 0:
            t_star = mu_star / se_star
        else:
            t_star = 0.0 if mu_star == 0.0 else math.copysign(float("inf"), mu_star)
        if abs(t_star) >= t_obs_abs:
            count_ge += 1
        total += 1

    return dict(p_wcb=count_ge / total, n_sign_vectors=total, n_ge_obs=count_ge)


# ── (B) Leave-one-cluster-out jackknife ─────────────────────────────────────────
def leave_one_cluster_out(y, clusters):
    y = np.asarray(y, dtype=float)
    clusters = list(clusters)
    dates = sorted(set(clusters))
    out = []
    for d in dates:
        keep = [i for i, c in enumerate(clusters) if c != d]
        y_sub = y[keep]
        c_sub = [clusters[i] for i in keep]
        res = cr1_mean(y_sub, c_sub)
        out.append(dict(dropped_review_date=d, **res))
    return out


def jackknife_flags(full_result, jk_rows):
    full_sign_positive = full_result["mean"] > 0
    full_excludes_zero = full_result["excludes_zero"]
    flips = []
    for row in jk_rows:
        sign_flip = (row["mean"] > 0) != full_sign_positive
        ci_status_change = row["excludes_zero"] != full_excludes_zero
        if sign_flip or ci_status_change:
            flips.append(dict(dropped_review_date=row["dropped_review_date"],
                               sign_flip=sign_flip,
                               ci_status_change=ci_status_change,
                               mean=row["mean"], ci95=row["ci95"]))
    return dict(any_single_cluster_drives_result=len(flips) > 0, flips=flips)


# ── (C) Per-review-date descriptives ────────────────────────────────────────────
def cluster_descriptives(events):
    by_date = defaultdict(lambda: {"all": [], "ADD": [], "DELETE": []})
    for e in events:
        d = e["effective_date"]
        by_date[d]["all"].append(e["signed_reversal"])
        by_date[d][e["event_type"]].append(e["signed_reversal"])

    rows = []
    for d in sorted(by_date):
        bucket = by_date[d]
        n_all, n_add, n_del = len(bucket["all"]), len(bucket["ADD"]), len(bucket["DELETE"])

        def m(xs):
            return float(np.mean(xs)) if xs else None

        rows.append(dict(
            review_date=d, n_events=n_all, n_add=n_add, n_delete=n_del,
            mean_signed_reversal_all=m(bucket["all"]),
            mean_signed_reversal_add=m(bucket["ADD"]),
            mean_signed_reversal_delete=m(bucket["DELETE"]),
        ))
    return rows


def print_descriptives_table(rows):
    hdr = f"{'review_date':<12} {'n':>3} {'nADD':>5} {'nDEL':>5} {'mean_all':>10} {'mean_ADD':>10} {'mean_DEL':>10}"
    print(hdr)
    print("-" * len(hdr))
    for r in rows:
        def f(v):
            return f"{v*100:+.3f}%" if v is not None else "n/a"
        print(f"{r['review_date']:<12} {r['n_events']:>3} {r['n_add']:>5} {r['n_delete']:>5} "
              f"{f(r['mean_signed_reversal_all']):>10} {f(r['mean_signed_reversal_add']):>10} "
              f"{f(r['mean_signed_reversal_delete']):>10}")


def print_jackknife_table(sample_name, rows, flags):
    print(f"\nleave-one-cluster-out jackknife -- {sample_name}")
    hdr = f"{'dropped_date':<14} {'n':>3} {'clusters':>8} {'mean':>10} {'SE':>9} {'t':>7} {'CI95 lo':>10} {'CI95 hi':>10} {'excl_zero':>10}"
    print(hdr)
    print("-" * len(hdr))
    for r in rows:
        lo, hi = r["ci95"]
        print(f"{r['dropped_review_date']:<14} {r['n']:>3} {r['n_clusters']:>8} "
              f"{r['mean']*100:>+9.4f}% {r['se']*100:>8.4f}% {r['t']:>7.3f} "
              f"{lo*100:>+9.4f}% {hi*100:>+9.4f}% {str(r['excludes_zero']):>10}")
    if flags["any_single_cluster_drives_result"]:
        print(f"  FLAG: dropping a single review date changes sign and/or CI-zero status for {sample_name}:")
        for f in flags["flips"]:
            print(f"    - drop {f['dropped_review_date']}: sign_flip={f['sign_flip']} "
                  f"ci_status_change={f['ci_status_change']} mean={f['mean']*100:+.4f}% "
                  f"CI95=[{f['ci95'][0]*100:+.4f}%, {f['ci95'][1]*100:+.4f}%]")
    else:
        print(f"  No single dropped review date flips sign or CI-zero status for {sample_name}.")


def main():
    run_utc = datetime.now(timezone.utc).isoformat()
    raw = RESULTS_PATH.read_bytes()
    results_sha256 = hashlib.sha256(raw).hexdigest()
    results = json.loads(raw)
    events = results["events"]

    samples = {
        "ALL": events,
        "ADD": [e for e in events if e["event_type"] == "ADD"],
        "DELETE": [e for e in events if e["event_type"] == "DELETE"],
    }

    print("EXP-PA-0001 post-hoc INFERENCE DIAGNOSTIC (does not alter the sealed REFUTED verdict)")
    print(f"run_utc={run_utc}")
    print(f"source results.json sha256={results_sha256}")
    print(f"source verdict (unchanged, terminal): {results['decision'].get('verdict') if isinstance(results.get('decision'), dict) else results.get('decision')}")
    print()

    out = {
        "diagnostic_id": "EXP-PA-0001-DIAG-CLUSTER-INFERENCE",
        "purpose": "post-hoc small-G (G=13) cluster inference robustness check; informational only, does not alter the sealed REFUTED verdict of EXP-PA-0001",
        "run_utc": run_utc,
        "source_results_json": str(RESULTS_PATH.name),
        "source_results_sha256": results_sha256,
        "source_verdict_unchanged": results.get("decision"),
        "alpha": ALPHA,
        "samples": {},
        "cluster_descriptives": None,
    }

    for name, evs in samples.items():
        y = np.array([e["signed_reversal"] for e in evs], dtype=float)
        clusters = [e["effective_date"] for e in evs]

        observed = cr1_mean(y, clusters)
        wcb = exact_wcb(y, clusters, observed["t"])
        jk_rows = leave_one_cluster_out(y, clusters)
        flags = jackknife_flags(observed, jk_rows)

        agree = (observed["excludes_zero"]) == (wcb["p_wcb"] < ALPHA)

        print(f"=== sample: {name} (n={observed['n']}, clusters={observed['n_clusters']}, df={observed['df']}) ===")
        print(f"  mean={observed['mean']*100:+.4f}%  SE(CR1)={observed['se']*100:.4f}%  "
              f"t={observed['t']:.3f}  CI95=[{observed['ci95'][0]*100:+.4f}%, {observed['ci95'][1]*100:+.4f}%]  "
              f"excludes_zero={observed['excludes_zero']}")
        print(f"  CR1 asymptotic p (t-dist, df={observed['df']}) = {observed['p_asymptotic']:.4f}")
        print(f"  exact WCB p (Rademacher, {wcb['n_sign_vectors']} sign vectors, null-imposed) = {wcb['p_wcb']:.4f}"
              f"  ({wcb['n_ge_obs']}/{wcb['n_sign_vectors']} with |t*| >= |t_obs|)")
        print(f"  asymptotic-vs-exact agreement at alpha={ALPHA}: "
              f"{'AGREE' if agree else 'DISAGREE'} "
              f"(asymptotic {'rejects' if observed['excludes_zero'] else 'does not reject'} H0; "
              f"WCB {'rejects' if wcb['p_wcb'] < ALPHA else 'does not reject'} H0)")

        print_jackknife_table(name, jk_rows, flags)
        print()

        out["samples"][name] = {
            "observed": observed,
            "wild_cluster_bootstrap": wcb,
            "asymptotic_vs_exact_agree_at_alpha": agree,
            "leave_one_cluster_out": jk_rows,
            "jackknife_flags": flags,
        }

    desc_rows = cluster_descriptives(events)
    out["cluster_descriptives"] = desc_rows
    print("=== per-review-date descriptives (all 13 clusters) ===")
    print_descriptives_table(desc_rows)

    OUT_JSON.write_text(json.dumps(out, indent=2, default=str))
    print(f"\ndiagnostic written to {OUT_JSON}")


if __name__ == "__main__":
    main()
