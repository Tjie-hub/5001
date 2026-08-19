#!/usr/bin/env python3
"""EXP-PA-0001 — confirmatory experiment for HYP-PA-0001 (frozen sha256 3692e69a...).

Mechanism: index-reconstitution / closing-auction dislocation (MECH-recon-dislocation).
Structural barrier M6 (market design): index-tracking rebalancing is a MANDATE, not a
mispricing — arbitrage can shift its timing but the flow must still clear.

Runs the registered spec EXACTLY. No tuning, no optimisation, no parameter search.
k is CRO-fixed at 5 td and is NOT re-tunable post-hoc (X1). Run once; a near-miss does
not license a second run with different settings (R15/X4).

  estimator            event-study CAR, market-model abnormal returns vs IHSG
  estimation window    230 td ending 20 td before announcement_date (CRO-fixed 2026-07-19)
  run-up window        [announcement .. effective]        DESCRIPTIVE ONLY, not tested
  reversal window      [t+1 .. t+k], k=5 td               THE TESTED QUANTITY
  signed reversal      ADD: -CAR   DELETE: +CAR           (signed against event direction)
  inference            cluster-robust CR1 (Liang-Zeger) by review date (effective_date)
  alpha                0.05, two-sided, H0: mean signed reversal (gross) = 0
  friction             round-trip imported from engine/exits/costs.py (asserted == 0.60%)
  dedup (A-PA6)        one economic event per (ticker, effective_date, event_type)

DECISION RULE (HARNESS_SPEC §2, applied verbatim):
  Test 1  PRIMARY   gross, both directions, all events, CR1.
                    Survives iff CR1 CI excludes zero AND sign matches prediction (>0).
  Test 2  SECONDARY net-of-cost, DELETE-only (long-only capturable side).
                    Survives iff gross - friction > 0.
  Robust  crosschecked-only, Test 1 form. Reported as a consistency check ONLY.
          Disagreement does NOT license re-running Test 1 with a filter.
  REFUTED iff Test 1 fails OR Test 2 fails.
  F-mode at close-out (R1, exactly one): Test-1 miss -> F2 (prediction failure);
          Test-1 pass + Test-2 miss -> F4 (cost destruction).

ADD-side note: ADD-side reversal capture requires SHORTING the inflated close, which is
execution-constrained on IDX for most names (readiness-review C-4). ADD-side is therefore
reported GROSS-ONLY and is NEVER claimed as a net/capturable edge.

Read-only on data/walkforward.db (opened mode=ro — structurally, not by convention, so no
WAL/SHM sidecars are created next to a Syncthing-managed file). Writes results JSON + log
only. No DB writes, no gatekeeper invocation, no production code touched.

This script does NOT create the frozen MANIFEST — that is a separate act (T5).
"""
import datetime
import json
import math
import os
import sqlite3
import sys
from collections import defaultdict

import numpy as np

# ── Registered constants (frozen — do not edit to chase a result) ────────────────
HYPOTHESIS_ID = "HYP-PA-0001"
EXPERIMENT_ID = "EXP-PA-0001"
REGISTRATION_SHA256_PREFIX = "3692e69a"
K_REVERSAL = 5            # trading days, CRO-fixed 2026-07-19. NOT tunable.
EST_WINDOW = 230          # trading days
EST_GAP = 20              # trading days between estimation-window end and announcement
ALPHA = 0.05
MDE_STAT_RAW = 0.0497     # pre-registered detection floor, reported for comparison only
MDE_STAT_HAIRCUT = 0.0422 # (HYP-PA-0001_POWER.md §4) — NOT recomputed here

DB = "data/walkforward.db"
EVENTS_CSV = "docs/research_programs/P-A/WP-D/reconstitution_events.csv"
OUT = "docs/research_programs/P-A/experiments/EXP-PA-0001"

# Sign convention: prediction is displacement INTO the effective close, then reversal.
#   ADD    -> priced UP into the close, expected to revert DOWN  => signed = -CAR
#   DELETE -> priced DOWN into the close, expected to revert UP  => signed = +CAR
# A positive signed reversal therefore means "the mechanism behaved as predicted",
# in both directions.
SIGN = {"ADD": -1.0, "DELETE": +1.0}

# ── Spec ambiguities resolved here, recorded explicitly in results.json ──────────
# The registered validation_criteria do not pin these down. They are fixed BEFORE
# seeing any result, stated here, and reported in the output so a reviewer can see
# exactly what was chosen and re-derive it.
RESOLVED_CHOICES = {
    "return_type": "simple (P_t/P_{t-1} - 1) — standard event-study convention "
                   "(MacKinlay 1997); CARs are arithmetic sums of daily ARs",
    "bar_filter": "is_final = 1 only — matches the research/backtest convention; "
                  "live partial bars (is_final=0) are excluded",
    "event_day_alignment": "t0 = last trading day <= effective_date for that ticker "
                           "(handles non-trading effective dates and date_precision='month')",
    "runup_window": "AR summed over [idx_announcement .. idx_effective] inclusive — "
                    "descriptive only, never used in the decision",
    "insufficient_data": "events lacking a full 230td estimation window or a full "
                         "k=5 reversal window are EXCLUDED and individually reported "
                         "with a reason — never imputed, never silently dropped",
    "cr1_dof": "t-critical uses df = G - 1 (number of review-date clusters minus one)",
}


def log(msg, fh):
    print(msg)
    fh.write(msg + "\n")
    fh.flush()


# ── Friction: imported, never re-derived (single cost authority, shared with P-M) ──
def load_friction():
    sys.path.insert(0, os.getcwd())
    from engine.exits.costs import COMMISSION_BUY, COMMISSION_SELL, SLIPPAGE
    rt = COMMISSION_BUY + COMMISSION_SELL + 2 * SLIPPAGE
    # The registration froze 0.60% round-trip. If the cost authority has since moved,
    # that is a spec divergence a reviewer must adjudicate — not something this script
    # silently absorbs.
    if abs(rt - 0.0060) > 1e-9:
        raise SystemExit(
            f"FATAL: cost authority round-trip = {rt:.6f}, but HYP-PA-0001 was "
            f"registered against 0.006000. Registration and code have diverged; "
            f"this requires adjudication (T12 supersession), not a silent re-run.")
    return rt, {"COMMISSION_BUY": COMMISSION_BUY, "COMMISSION_SELL": COMMISSION_SELL,
                "SLIPPAGE": SLIPPAGE, "round_trip": rt}


# ── Cluster-robust CR1 (Liang-Zeger sandwich) for a mean ────────────────────────
def cr1_mean(y, clusters):
    """Mean of y with a cluster-robust CR1 standard error.

    Regression form: y_i = mu + e_i (X = column of ones, K = 1).
      meat  = sum_g ( sum_{i in g} e_i )^2
      V     = meat / N^2
      CR1 c = [G/(G-1)] * [(N-1)/(N-K)]      (with K=1 the second factor is 1)
      t     = mu / SE,  df = G - 1
    """
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
                    ci95=[float("nan"), float("nan")], df=max(G - 1, 0),
                    excludes_zero=False)

    v = meat / (n ** 2)
    c = (G / (G - 1.0)) * ((n - 1.0) / (n - 1.0))   # K=1 -> second factor == 1
    se = math.sqrt(v * c)
    tstat = mu / se if se > 0 else float("nan")
    df = G - 1
    tcrit = _t_crit_two_sided(df, ALPHA)
    lo, hi = mu - tcrit * se, mu + tcrit * se
    return dict(n=n, n_clusters=G, mean=mu, se=se, t=tstat, df=df, t_crit=tcrit,
                ci95=[lo, hi], excludes_zero=bool(lo > 0 or hi < 0))


def _t_crit_two_sided(df, alpha):
    """Two-sided t critical value. Uses scipy when available; else a small exact table
    (the df here is G-1, which is small and known in advance)."""
    try:
        from scipy import stats
        return float(stats.t.ppf(1 - alpha / 2.0, df))
    except Exception:
        table = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447,
                 7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228, 11: 2.201, 12: 2.179,
                 13: 2.160, 14: 2.145, 15: 2.131, 16: 2.120, 17: 2.110, 18: 2.101,
                 19: 2.093, 20: 2.086, 25: 2.060, 30: 2.042}
        if df in table:
            return table[df]
        keys = sorted(table)
        return table[min(keys, key=lambda k: abs(k - df))]


def pooled_iid_mean(y):
    """Pre-registered SECONDARY sensitivity figure only. Reported, never substituted
    as the decision basis (validation_criteria: 'cluster-robust CR1-only')."""
    y = np.asarray(y, dtype=float)
    n = y.size
    if n < 2:
        return dict(n=n, mean=float(y.mean()) if n else float("nan"), se=float("nan"))
    mu = float(y.mean())
    se = float(y.std(ddof=1) / math.sqrt(n))
    return dict(n=n, mean=mu, se=se, t=mu / se if se > 0 else float("nan"))


# ── Data loading ────────────────────────────────────────────────────────────────
def load_events(path):
    import csv
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def dedup_events(rows):
    """A-PA6: a ticker entering/leaving several indices on the SAME effective date is
    ONE economic event, not one independent draw per index row. Key =
    (ticker, effective_date, event_type). Index membership is collapsed into a list."""
    by_key = {}
    for r in rows:
        key = (r["ticker"], r["effective_date"], r["event_type"])
        if key not in by_key:
            by_key[key] = dict(
                ticker=r["ticker"], effective_date=r["effective_date"],
                event_type=r["event_type"], announcements=[r["announcement_date"]],
                review_period=r["review_period"], date_precision=r["date_precision"],
                indices=[r["index"]], verification=[r["verification_status"]],
                event_ids=[r["event_id"]])
        else:
            by_key[key]["announcements"].append(r["announcement_date"])
            by_key[key]["indices"].append(r["index"])
            by_key[key]["verification"].append(r["verification_status"])
            by_key[key]["event_ids"].append(r["event_id"])
    out = []
    for e in by_key.values():
        # An event counts as crosschecked if ANY of its collapsed source rows was.
        e["crosschecked"] = "SECONDARY_CROSSCHECKED" in e["verification"]
        # Earliest announcement across collapsed rows. Deterministic, and conservative
        # in the sense that it starts the (descriptive) run-up window earliest; it does
        # not affect the tested reversal window, which is anchored on effective_date.
        e["announcement_date"] = min(e["announcements"])
        out.append(e)
    return sorted(out, key=lambda e: (e["effective_date"], e["ticker"], e["event_type"]))


def load_series(conn, ticker):
    """(dates, simple returns) for a ticker, is_final=1 only, chronological.
    Returns are aligned so ret[i] is the return REALISED ON dates[i]."""
    rows = conn.execute(
        "SELECT date, close FROM ohlcv "
        "WHERE ticker = ? AND COALESCE(is_final, 1) = 1 AND close > 0 "
        "ORDER BY date", (ticker,)).fetchall()
    if len(rows) < 2:
        return [], np.array([])
    dates = [r[0] for r in rows]
    close = np.array([float(r[1]) for r in rows])
    ret = np.empty(len(close))
    ret[0] = np.nan
    ret[1:] = close[1:] / close[:-1] - 1.0
    return dates, ret


def idx_on_or_before(dates, target):
    """Position of the last trading day <= target; -1 if none."""
    lo, hi, best = 0, len(dates) - 1, -1
    while lo <= hi:
        mid = (lo + hi) // 2
        if dates[mid] <= target:
            best, lo = mid, mid + 1
        else:
            hi = mid - 1
    return best


# ── Per-event market model + CARs ───────────────────────────────────────────────
def measure_event(ev, tdates, tret, mret_by_date):
    """Returns (record, None) on success or (None, reason) on exclusion."""
    i_ann = idx_on_or_before(tdates, ev["announcement_date"])
    i_eff = idx_on_or_before(tdates, ev["effective_date"])
    if i_ann < 0 or i_eff < 0:
        return None, "no trading day on/before announcement or effective date"
    if i_eff <= i_ann:
        return None, "effective date not after announcement in this ticker's calendar"

    est_end = i_ann - EST_GAP
    est_start = est_end - EST_WINDOW + 1
    if est_start < 1:
        return None, (f"insufficient history for a {EST_WINDOW}td estimation window "
                      f"ending {EST_GAP}td before announcement "
                      f"(need index >= 1, got {est_start})")
    if i_eff + K_REVERSAL >= len(tdates):
        return None, f"incomplete k={K_REVERSAL} reversal window after effective date"

    # Align market returns onto the ticker's own trading calendar.
    mret = np.array([mret_by_date.get(d, np.nan) for d in tdates])

    est = slice(est_start, est_end + 1)
    y, x = tret[est], mret[est]
    ok = ~(np.isnan(y) | np.isnan(x))
    if ok.sum() < EST_WINDOW * 0.8:
        return None, (f"estimation window has only {int(ok.sum())} usable paired "
                      f"observations (< 80% of {EST_WINDOW})")

    # OLS market model: r_i = alpha + beta * r_m
    xm, ym = x[ok], y[ok]
    var_x = float(((xm - xm.mean()) ** 2).sum())
    if var_x <= 0:
        return None, "degenerate market variance in estimation window"
    beta = float(((xm - xm.mean()) * (ym - ym.mean())).sum() / var_x)
    alpha_hat = float(ym.mean() - beta * xm.mean())

    def car(a, b):
        """Sum of abnormal returns over ticker-calendar positions [a, b] inclusive."""
        seg_y, seg_x = tret[a:b + 1], mret[a:b + 1]
        ar = seg_y - (alpha_hat + beta * seg_x)
        if np.isnan(ar).any():
            return None
        return float(ar.sum())

    car_rev = car(i_eff + 1, i_eff + K_REVERSAL)     # THE TESTED QUANTITY
    car_run = car(i_ann, i_eff)                       # descriptive only
    if car_rev is None:
        return None, "NaN abnormal return inside the reversal window"

    signed = SIGN[ev["event_type"]] * car_rev
    return dict(
        ticker=ev["ticker"], event_type=ev["event_type"],
        effective_date=ev["effective_date"], announcement_date=ev["announcement_date"],
        review_period=ev["review_period"], indices=sorted(set(ev["indices"])),
        crosschecked=ev["crosschecked"], date_precision=ev["date_precision"],
        t0_trading_day=tdates[i_eff], t0_exact=(tdates[i_eff] == ev["effective_date"]),
        alpha=alpha_hat, beta=beta, est_obs=int(ok.sum()),
        car_runup=car_run, car_reversal=car_rev, signed_reversal=signed,
    ), None


def main():
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    os.makedirs(OUT, exist_ok=True)
    fh = open(f"{OUT}/execution.log", "w", encoding="utf-8")

    log(f"{EXPERIMENT_ID} confirmatory run @ {ts}", fh)
    log(f"hypothesis {HYPOTHESIS_ID} (registration sha256 {REGISTRATION_SHA256_PREFIX}...)", fh)
    log(f"k={K_REVERSAL} td (CRO-fixed, not tunable) | estimation {EST_WINDOW}td "
        f"ending {EST_GAP}td pre-announcement | alpha={ALPHA}", fh)

    friction, cost_detail = load_friction()
    log(f"friction round-trip = {friction:.4%} (imported from engine/exits/costs.py)", fh)

    raw = load_events(EVENTS_CSV)
    events = dedup_events(raw)
    log(f"\nevents: {len(raw)} raw rows -> {len(events)} distinct economic events "
        f"after A-PA6 dedup (ticker, effective_date, event_type)", fh)
    log("NOTE: the registration quotes N=210 / 105 / 98 (raw ROW counts). The harness "
        "spec mandates dedup BEFORE analysis, so realised analysis N is lower. Both are "
        "reported; the deduped N is what the tests use.", fh)

    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    fp = conn.execute("SELECT COUNT(*), MIN(date), MAX(date) FROM ohlcv "
                      "WHERE COALESCE(is_final,1)=1").fetchone()
    log(f"corpus: ohlcv is_final=1 rows={fp[0]:,} range {fp[1]}..{fp[2]}", fh)

    mdates, mret = load_series(conn, "IHSG")
    if not mdates:
        raise SystemExit("FATAL: no IHSG series — the market model cannot be estimated.")
    mret_by_date = dict(zip(mdates, mret))
    log(f"market index IHSG: {len(mdates)} bars {mdates[0]}..{mdates[-1]}", fh)

    measured, excluded = [], []
    series_cache = {}
    for ev in events:
        tk = ev["ticker"]
        if tk not in series_cache:
            series_cache[tk] = load_series(conn, tk)
        tdates, tret = series_cache[tk]
        if not tdates:
            excluded.append({**{k: ev[k] for k in ("ticker", "effective_date", "event_type")},
                             "reason": "no ohlcv history for ticker"})
            continue
        rec, reason = measure_event(ev, tdates, tret, mret_by_date)
        if rec is None:
            excluded.append({**{k: ev[k] for k in ("ticker", "effective_date", "event_type")},
                             "reason": reason})
        else:
            measured.append(rec)
    conn.close()

    log(f"\nmeasured {len(measured)} events; excluded {len(excluded)} "
        f"(every exclusion is itemised in results.json — none imputed)", fh)
    if excluded:
        by_reason = defaultdict(int)
        for e in excluded:
            by_reason[e["reason"].split("(")[0].strip()] += 1
        for r, c in sorted(by_reason.items(), key=lambda kv: -kv[1]):
            log(f"   excluded {c:>3}  {r}", fh)

    if not measured:
        raise SystemExit("FATAL: no measurable events — cannot run the tests.")

    def fmt(res, label):
        log(f"\n[{label}] n={res['n']} clusters={res['n_clusters']} df={res.get('df')}", fh)
        log(f"   mean signed reversal = {res['mean']*100:+.4f}%  "
            f"SE(CR1)={res['se']*100:.4f}%  t={res['t']:.3f}", fh)
        log(f"   CI95 = [{res['ci95'][0]*100:+.4f}%, {res['ci95'][1]*100:+.4f}%]  "
            f"excludes_zero={res['excludes_zero']}", fh)

    # ── Test 1 — PRIMARY: gross, both directions, cluster-robust ────────────────
    y1 = [m["signed_reversal"] for m in measured]
    c1 = [m["effective_date"] for m in measured]
    t1 = cr1_mean(y1, c1)
    t1_iid = pooled_iid_mean(y1)
    fmt(t1, "TEST 1 · PRIMARY · gross · both directions · CR1")
    log(f"   secondary sensitivity (pooled iid, NOT the decision basis): "
        f"mean={t1_iid['mean']*100:+.4f}% SE={t1_iid['se']*100:.4f}% "
        f"t={t1_iid.get('t', float('nan')):.3f}", fh)
    log(f"   pre-registered MDE_stat for comparison only: "
        f"{MDE_STAT_RAW*100:.2f}% raw / {MDE_STAT_HAIRCUT*100:.2f}% haircut", fh)
    test1_pass = bool(t1["excludes_zero"] and t1["mean"] > 0)
    log(f"   => TEST 1 {'PASS' if test1_pass else 'FAIL'} "
        f"(requires CI excluding zero AND mean > 0)", fh)

    # ── Test 2 — SECONDARY: net-of-cost, DELETE-only (long-only capturable side) ─
    dele = [m for m in measured if m["event_type"] == "DELETE"]
    y2 = [m["signed_reversal"] for m in dele]
    c2 = [m["effective_date"] for m in dele]
    t2 = cr1_mean(y2, c2) if len(y2) >= 2 else None
    if t2:
        fmt(t2, "TEST 2 · SECONDARY · DELETE-only · gross · CR1")
        net = t2["mean"] - friction
        net_ci = [t2["ci95"][0] - friction, t2["ci95"][1] - friction]
        log(f"   NET of {friction:.2%} round-trip: {net*100:+.4f}%  "
            f"CI95=[{net_ci[0]*100:+.4f}%, {net_ci[1]*100:+.4f}%]", fh)
        test2_pass = bool(net > 0)
        log(f"   => TEST 2 {'PASS' if test2_pass else 'FAIL'} (requires gross - friction > 0)", fh)
    else:
        net, net_ci, test2_pass = float("nan"), [float("nan")] * 2, False
        log("\n[TEST 2] insufficient DELETE observations", fh)

    # ── ADD side: reported GROSS-ONLY, never claimed as capturable (C-4) ─────────
    adds = [m for m in measured if m["event_type"] == "ADD"]
    t_add = cr1_mean([m["signed_reversal"] for m in adds],
                     [m["effective_date"] for m in adds]) if len(adds) >= 2 else None
    if t_add:
        fmt(t_add, "ADD-side · GROSS ONLY · not a capturable claim (shorting-constrained)")

    # ── Robustness leg — crosschecked-only, consistency check ONLY ──────────────
    xs = [m for m in measured if m["crosschecked"]]
    t3 = cr1_mean([m["signed_reversal"] for m in xs],
                  [m["effective_date"] for m in xs]) if len(xs) >= 2 else None
    if t3:
        fmt(t3, "ROBUSTNESS · SECONDARY_CROSSCHECKED only · consistency check")
        agree = (t3["mean"] > 0) == (t1["mean"] > 0)
        log(f"   sign agreement with Test 1: {agree}", fh)
        log("   NOTE: disagreement does NOT license re-running Test 1 with a filter "
            "(R15/X4). This leg is a consistency check, not a rescue mechanism.", fh)
    else:
        agree = None

    # ── Verdict, applying the frozen rule verbatim ──────────────────────────────
    refuted = (not test1_pass) or (not test2_pass)
    if refuted:
        fmode = "F2 · Prediction failure" if not test1_pass else "F4 · Cost destruction"
        verdict, note = "REFUTED", f"proposed F-mode: {fmode} (R1 — exactly one, defended at close-out)"
    else:
        fmode = None
        verdict, note = "SURVIVES", ("both pre-registered tests passed; terminal reachable "
                                     "tier remains C2 (EV-9, N=1) pending independent review")

    log("\n" + "=" * 72, fh)
    log(f"VERDICT: {verdict}", fh)
    log(f"  Test 1 (mechanism, gross, CR1): {'PASS' if test1_pass else 'FAIL'}", fh)
    log(f"  Test 2 (capturable, DELETE net): {'PASS' if test2_pass else 'FAIL'}", fh)
    log(f"  {note}", fh)
    log("=" * 72, fh)
    log("\nNEXT (not done by this script): close-out — EVIDENCE_PACKAGE.md, a frozen "
        "MANIFEST.md (T5), and either an Accepted-Knowledge or Failure-Library entry, "
        "then update HYPOTHESIS_REGISTRY.md / FAILURE_REGISTRY.md. No re-runs (HL-3).", fh)

    results = {
        "experiment_id": EXPERIMENT_ID, "hypothesis_id": HYPOTHESIS_ID,
        "registration_sha256_prefix": REGISTRATION_SHA256_PREFIX,
        "run_utc": ts,
        "spec": {"k_reversal_td": K_REVERSAL, "estimation_window_td": EST_WINDOW,
                 "estimation_gap_td": EST_GAP, "alpha": ALPHA,
                 "market_index": "IHSG", "sign_convention": SIGN,
                 "mde_stat_raw": MDE_STAT_RAW, "mde_stat_haircut": MDE_STAT_HAIRCUT},
        "friction": cost_detail,
        "resolved_spec_ambiguities": RESOLVED_CHOICES,
        "corpus": {"db": DB, "ohlcv_is_final_rows": fp[0],
                   "range": [fp[1], fp[2]], "read_only": True},
        "counts": {"raw_csv_rows": len(raw), "distinct_events_after_dedup": len(events),
                   "measured": len(measured), "excluded": len(excluded),
                   "measured_add": len(adds), "measured_delete": len(dele),
                   "measured_crosschecked": len(xs),
                   "registration_quoted_raw_N": {"primary": 210, "delete_only": 105,
                                                 "robustness": 98}},
        "test1_primary_gross_cr1": t1,
        "test1_secondary_sensitivity_pooled_iid": t1_iid,
        "test2_delete_only_net": {"gross_cr1": t2, "friction": friction,
                                  "net_mean": net, "net_ci95": net_ci,
                                  "pass": test2_pass},
        "add_side_gross_only": t_add,
        "robustness_crosschecked_only": t3,
        "robustness_sign_agreement": agree,
        "decision": {"test1_pass": test1_pass, "test2_pass": test2_pass,
                     "verdict": verdict, "proposed_f_mode": fmode,
                     "rule": "REFUTED iff Test 1 fails OR Test 2 fails "
                             "(HARNESS_SPEC §2, applied verbatim)"},
        "events": measured,
        "excluded_events": excluded,
    }
    with open(f"{OUT}/results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)
    log(f"\nresults.json + execution.log written to {OUT}", fh)
    fh.close()


if __name__ == "__main__":
    main()
