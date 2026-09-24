"""Summary statistics and the central verdict for a Rule Card run (D-055).

The verdict is computed here from the frozen card, never by the rule script, so a
script cannot move its own goalposts. Order of precedence:

  INVALID                              any mandatory check failed (implementation/data)
  INCONCLUSIVE_UNDERPOWERED            would be FAIL, but fewer than 80% of the planned months
                                       were realised — not a failure, not evidence
  FAIL                                 primary misses the tier hurdle, or a half / ex-2025
                                       has the wrong sign, or (tier N) DSR < 0.95
  FAIL_NOT_MONOTONE                    primary clears but no dose-response over the declared
                                       shape (R6: full range, or median-to-tail) — a pattern
  EFFECT_PRESENT_MECHANISM_UNCONFIRMED a pre-declared fingerprint has the wrong sign (R7)
  PASS_NOT_DEPLOYABLE                  effect exists, long-only deployment test fails
  PASS                                 all of the above hold
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from research.rulecard.card import TIER_N_MIN_DSR, hurdle_t
from research.rulecard.stats import minimum_bayes_factor_p_null, mr_test, nw_t

MIN_MONTHS_PER_HALF = 12
REALIZED_POWER_FLOOR = 0.80
MIN_PRIOR_STATE_MONTHS = 12
PRIOR_TRUE = {"R": 0.5, "N": 0.1}


def _sgn(card, key="estimand"):
    return -1.0 if card[key]["predicted_sign"] == "negative" else 1.0


def mr_direction(card) -> str:
    s = _sgn(card)
    if card["estimand"]["primary_kind"] == "top_minus_bottom":
        return "increasing" if s > 0 else "decreasing"
    high = card["portfolio"]["use_end"] == "high"
    return "increasing" if (s > 0) == high else "decreasing"


def _window(v, lag):
    if not v:
        return {"n": 0}
    p = np.array([m["primary"] for m in v], float)
    d = np.array([m["deployment"] for m in v], float)
    u = np.array([m["uplift_net"] for m in v], float)
    return {"n": len(v), "primary_mean": float(np.nanmean(p)),
            "primary_sd": float(np.nanstd(p, ddof=1)) if len(v) > 1 else float("nan"),
            "primary_t": nw_t(p, lag), "deployment_mean": float(np.nanmean(d)),
            "deployment_t": nw_t(d, lag), "uplift_net_mean": float(np.nanmean(u)),
            "turn_book_mean": float(np.mean([m["turn_book"] for m in v]))}


def _fingerprint(name, v, lag):
    if name in ("adv_tercile", "price_tercile"):
        k = "adv" if name == "adv_tercile" else "price"
        diff = np.array([m[f"fp_{k}_low"] - m[f"fp_{k}_high"] for m in v], float)
        diff = diff[~np.isnan(diff)]
        return {"observed": float(diff.mean()) if diff.size else float("nan"),
                "t": nw_t(diff, lag), "n": int(diff.size),
                "definition": f"spread(lowest {k} tercile) - spread(highest {k} tercile)"}
    # market_state: expanding terciles of the ex-ante 63-session EW universe return,
    # each month classified only against months strictly before it
    states = [m["state"] for m in v]
    hi, lo = [], []
    for i, m in enumerate(v):
        past = [s for s in states[:i] if not np.isnan(s)]
        if len(past) < MIN_PRIOR_STATE_MONTHS or np.isnan(m["state"]):
            continue
        q1, q2 = np.quantile(past, [1 / 3, 2 / 3])
        if m["state"] >= q2:
            hi.append(m["deployment"])
        elif m["state"] <= q1:
            lo.append(m["deployment"])
    obs = float(np.mean(hi) - np.mean(lo)) if hi and lo else float("nan")
    return {"observed": obs, "n_high": len(hi), "n_low": len(lo),
            "definition": "deployment spread in high-state months - low-state months"}


def summarize(months: list[dict], card: dict) -> dict:
    lag = int(card["estimand"].get("nw_lag", 3))
    v = [m for m in months if m.get("valid") and "primary" in m]
    split = pd.Timestamp(card["windows"]["split"])
    disc = [m for m in v if pd.Timestamp(m["formation"]) < split]
    conf = [m for m in v if pd.Timestamp(m["formation"]) >= split]
    ex25 = [m for m in v if not m["month"].startswith("2025")]
    out = {"windows": {"FULL": _window(v, lag), "DISCOVERY": _window(disc, lag),
                       "CONFIRMATION": _window(conf, lag), "EX2025": _window(ex25, lag)},
           "skipped_months": [{"month": m["month"], "reason": m.get("reason")}
                              for m in months if not m.get("valid")]}
    years = {}
    for m in v:
        years.setdefault(m["month"][:4], []).append(m)
    out["per_year"] = {y: {"n": len(ms), "primary_mean": float(np.mean([x["primary"] for x in ms])),
                           "deployment_mean": float(np.mean([x["deployment"] for x in ms]))}
                       for y, ms in sorted(years.items())}
    if card["portfolio"]["bucketing"] == "flag":
        out["monotonicity"] = {"applicable": False, "reason": "flag bucketing has two groups"}
    else:
        mono = card.get("monotonicity") or {}
        shape = mono.get("shape", "full")
        R = np.array([m["bucket_means"] for m in v], float)
        # MR is tested on quintiles by default: with ~150-300 names, adjacent deciles are
        # too noisy for a min-over-all-differences test (power, not leniency)
        if mono.get("grid", "quintile") == "quintile" and R.ndim == 2 and R.shape[1] == 10:
            R = R.reshape(R.shape[0], 5, 2).mean(axis=2)
        K = R.shape[1] if R.ndim == 2 else 0
        cols = list(range(K))
        if shape == "tail":
            # graded from the median bucket to the used end (a tail mechanism such as
            # lottery demand); a pure step in the extreme bucket still fails
            half = K // 2
            cols = cols[half:] if card["portfolio"]["use_end"] == "high" else cols[:K - half]
        out["monotonicity"] = {"applicable": True, "shape": shape, "grid": mono.get("grid", "quintile"),
                               "buckets_tested": [c + 1 for c in cols],
                               "direction": mr_direction(card),
                               "alpha": float(mono.get("alpha", 0.10)),
                               **mr_test(R[:, cols] if K else R, mr_direction(card),
                                         int(mono.get("n_boot", 1000)), float(mono.get("block", 6.0)))}
    out["fingerprints"] = [{"name": fp["name"], "predicted_sign": fp["predicted_sign"],
                            **_fingerprint(fp["name"], v, lag)} for fp in card.get("fingerprints", [])]
    out["primary_series"] = [float(m["primary"]) for m in v]
    out["stale_exits"] = int(sum(m.get("stale_exits", 0) for m in v))
    out["not_tradeable_at_entry"] = int(sum(m.get("not_tradeable_at_entry", 0) for m in v))
    return out


def verdict(card: dict, summary: dict, checks: list[dict]) -> dict:
    failed = [c for c in checks if c["status"] != "PASS"]
    if failed:
        return {"verdict": "INVALID", "reasons": [f"{c['code']} {c['check']} FAIL" for c in failed],
                "criteria": []}
    s = _sgn(card)
    W = summary["windows"]
    t_req = hurdle_t(card)
    crit = []

    def add(name, required, observed, ok):
        crit.append({"criterion": name, "required": required, "observed": observed, "pass": ok})
        return ok

    tf = W["FULL"].get("primary_t", float("nan"))
    c1 = add("primary NW t, predicted sign", f"{'<= -' if s < 0 else '>= '}{t_req:.2f}",
             tf, bool(not np.isnan(tf) and s * tf >= t_req))
    halves = True
    for w in ("DISCOVERY", "CONFIRMATION"):
        n, mu = W[w].get("n", 0), W[w].get("primary_mean", float("nan"))
        halves &= add(f"{w.lower()} mean has predicted sign (n>={MIN_MONTHS_PER_HALF})",
                      "sign match", {"n": n, "mean": mu},
                      bool(n >= MIN_MONTHS_PER_HALF and s * mu > 0))
    c3 = add("ex-2025 mean has predicted sign", "sign match", W["EX2025"].get("primary_mean"),
             bool(s * W["EX2025"].get("primary_mean", float("nan")) > 0))
    c_dsr = True
    if card["tier"] == "N":
        from research.statistics import deflated_sharpe_ratio
        # the primary series is re-signed so the predicted direction is positive
        prim = [s * m for m in summary.get("primary_series", [])]
        n_tr = int(card["trials"]["n_trials"])
        sd = card["trials"].get("sr_trials_std") or (1.0 / np.sqrt(max(len(prim), 2)))
        d = deflated_sharpe_ratio(prim, n_tr, float(sd))
        c_dsr = add("tier N: DSR", f">= {TIER_N_MIN_DSR}", d["dsr"], bool(d["dsr"] >= TIER_N_MIN_DSR))
    mono = summary["monotonicity"]
    c_mr = None
    if mono.get("applicable"):
        c_mr = add(f"monotonicity MR test ({mono['direction']})", f"p < {mono['alpha']}",
                   mono.get("p"), bool(mono.get("p") is not None and mono["p"] < mono["alpha"]))
    c_fp = True
    for fp in summary["fingerprints"]:
        want = -1.0 if fp["predicted_sign"] == "negative" else 1.0
        ok = bool(not np.isnan(fp["observed"]) and want * fp["observed"] > 0)
        c_fp &= add(f"fingerprint {fp['name']} sign", fp["predicted_sign"], fp["observed"], ok)
    sd_ = _sgn(card, "deployment")
    td = W["FULL"].get("deployment_t", float("nan"))
    d_req = float((card.get("deployment") or {}).get("hurdle_t", t_req))
    c_dep = add("deployment (bucket - rest) NW t", f"{'<= -' if sd_ < 0 else '>= '}{d_req:.2f}",
                td, bool(not np.isnan(td) and sd_ * td >= d_req))

    planned = int((card.get("power") or {}).get("n_months") or 0)
    realized = int(W["FULL"].get("n", 0))
    short = planned > 0 and realized < REALIZED_POWER_FLOOR * planned
    add("realized months vs planned (power)", f">= {REALIZED_POWER_FLOOR:.0%} of {planned}",
        realized, not short)
    if not (c1 and halves and c3 and c_dsr):
        # a miss on a sample much shorter than the power plan could not have refuted
        # the rule — rule R2 of the evidence model: no evidential weight either way
        v = "INCONCLUSIVE_UNDERPOWERED" if short else "FAIL"
    elif c_mr is False:
        v = "FAIL_NOT_MONOTONE"
    elif not c_fp:
        v = "EFFECT_PRESENT_MECHANISM_UNCONFIRMED"
    elif not c_dep:
        v = "PASS_NOT_DEPLOYABLE"
    else:
        v = "PASS"
    post = (minimum_bayes_factor_p_null(abs(tf), PRIOR_TRUE[card["tier"]])
            if not np.isnan(tf) else float("nan"))
    return {"verdict": v, "criteria": crit,
            "posterior_p_null_lower_bound": post, "prior_true_assumed": PRIOR_TRUE[card["tier"]]}
