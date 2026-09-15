#!/usr/bin/env python3
"""EXP-PM-0009 — confirmatory experiment for HYP-PM-0009 (I7 · intraday execution timing).

Runs the REGISTERED specification EXACTLY, once:
docs/research_programs/P-M/HYP-PM-0009_REGISTERED.md (preregistration_sha256 d19dfd0f…).

Every substantive field below is frozen by that record and is reproduced verbatim:
  - cohort:   I7 v004 admissible store, fingerprint-bound (store_sha256 e1375264…fba),
              76 sessions 2026-04-28..2026-09-11, 61,335 admitted ticker-days.
  - signal:   nbuy(seg) = SUM(buy_lot) - SUM(sell_lot);
              OPEN := 09:00..09:59; LATE := 14:50..15:49; 16:00-16:14 bars excluded everywhere;
              daily_net := nbuy over 09:00..15:49 (continuous session only);
              POPULATION := daily_net > 0;
              LATE_TILTED if nbuy(LATE)/daily_net >= 0.50 (frozen structural midpoint), else EARLY_TILTED.
  - estimand: step_1  per formation date d with >= 1 LATE_TILTED and >= 1 EARLY_TILTED surviving cell:
                      m(d) = mean(fwd | LATE) - mean(fwd | EARLY);  one-sided dates SKIPPED AND COUNTED.
              step_2  theta_primary = mean of the daily series m(d).
  - outcome:  fwd_return = close(t+2)/close(t+1) - 1 (k=1 primary; k in {2,3} robustness ONLY);
              entry reference close(t+1).
  - inference: Newey-West HAC lag = 5 (g1_harness.nw_t BFI-001 convention — the daily series IS the
              date clustering), two-sided p via erfc; Holm at the single primary = identity.
  - X5 (estimation layer, counted): corporate_actions row with date in [t, t+2]; ticker RAJA;
              close(t) < Rp 100; PIT liquidity floor unmet — program term (HYP-PM-0008_SPEC §4):
              trailing-60-session median traded value (close x volume), shift(1), >= Rp 1,000,000,000.
  - X6 (estimation layer, counted): t, t+1, t+2 strictly consecutive admitted sessions
              (effective calendar = DATASET_B_SESSION_CALENDAR_v2 ∪ I7_SESSION_CALENDAR_EXTENSION_v1).
  - cost:     theta_net = theta_primary - 0.006 — SENSITIVITY ONLY, never a statistical verdict.
  - kill rule: PASS iff theta_primary > 0 AND two-sided p < 0.05; otherwise FAILED (F2).
              No power claim exists (D-050): a non-rejection is NOT evidence of absence.

No tuning, no parameter variation, no rescue, no post-hoc repair. Reads the frozen store via a
read-only URI and data/walkforward.db via a read-only URI + PRAGMA query_only. Writes
execution.log + results.json ONLY when actually executed. Performs no DB writes.

--consistency-check runs ONLY the pre-execution identity/integrity verification and exits; it
computes NO flow-vs-return statistic and is safe to run before the single execution.
"""
import sqlite3, json, sys, datetime, hashlib, math, argparse, platform

ROOT = "/home/tjiesar/10 Projects/idx-walkforward-5001"
REG_PATH = f"{ROOT}/docs/research_programs/P-M/HYP-PM-0009_REGISTERED.md"
SPEC_PATH = f"{ROOT}/docs/research_programs/P-M/BRANCH_A_NEW_MECHANISM_AUDIT_2026-09-14.md"
STORE = f"{ROOT}/docs/research_programs/P-M/i7_accrual/store/I7_V004_ADMISSIBLE_v1.sqlite"
CAL_BASE = f"{ROOT}/docs/research_programs/P-M/dataset_b/artifacts/DATASET_B_SESSION_CALENDAR_v2.json"
CAL_EXT = f"{ROOT}/docs/research_programs/P-M/i7_accrual/store/I7_SESSION_CALENDAR_EXTENSION_v1.json"
PROD_DB = f"{ROOT}/data/walkforward.db"
OUT = f"{ROOT}/docs/research_programs/P-M/experiments/EXP-PM-0009"

# ---- frozen registered constants (HYP-PM-0009_REGISTERED.md — none may be varied) ----
PREREG_SHA256 = "d19dfd0f6b059a4b4c564361087bf9aa59e327c8105c5229e166afa64f76b75a"
STORE_SHA256 = "e1375264133b42f417d8e74f48a48646197d15b8961e3bdf431d6eebc8784fba"
SPEC_SHA256 = "76a965459425e7c1006569d05d8e43fe2e877164e605d0e2d9a9caeb92bba03f"
CAL_BASE_SHA256 = "5012be2315dc82ccfd65a2b117e1977753f0a7d3214693821b39077cd18043fa"
CAL_EXT_SHA256 = "a7a4eedf45f3d4b2ced4f9a9f2d90d28e011ef0425b115c127a04fcdda0f189e"
N_SESSIONS = 76
N_ADMITTED = 61335
N_TICKERS = 868
N_BAR_ROWS = 19_793_865
LEDGER = {"X3": 7038, "E-PIT-2": 2044, "E-PIT-3": 1507, "E-PIT-4": 10890}
N_CANDIDATE = 82814
SESSION_WINDOW = ("2026-04-28", "2026-09-11")
X3_EXCLUDED = ["2026-05-01", "2026-05-14", "2026-05-15", "2026-05-28", "2026-06-16",
               "2026-07-09", "2026-07-24", "2026-09-14"]
STATE_THRESHOLD = 0.50
PRICE_FLOOR = 100            # close(t) < Rp 100 excluded (X5)
TV_WINDOW = 60               # trailing-60-session median traded value, shift(1)
TV_FLOOR = 1_000_000_000     # >= Rp 1,000,000,000 (PIT liquidity floor, program term)
NW_LAG = 5
FRICTION = 0.0060            # 0.60% round-trip — sensitivity only
KPRIMARY = 1
KS = [1, 2, 3]               # k=1 PRIMARY; 2/3 robustness ONLY, never primary


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_frozen_block():
    import re
    raw = open(REG_PATH, "rb").read()
    m = re.search(rb"<!--FROZEN-START-->\n(.*?)<!--FROZEN-END-->", raw, re.S)
    return hashlib.sha256(m.group(1).rstrip(b"\n")).hexdigest()


def nw_t(x, lag):
    """Newey-West t-stat of the mean of a daily series (g1_harness BFI-001 convention).
    The daily series IS the date clustering: one observation per date."""
    xs = [v for v in x if v is not None and math.isfinite(v)]
    n = len(xs)
    if n < 10:
        return (float("nan"), n)
    xm = sum(xs) / n
    u = [v - xm for v in xs]
    s = sum(v * v for v in u)
    for L in range(1, min(lag, n - 1) + 1):
        s += 2.0 * (1.0 - L / (lag + 1.0)) * sum(a * b for a, b in zip(u[L:], u[:-L]))
    var = s / n
    if var <= 0:
        return (float("nan"), n)
    return (xm / math.sqrt(var / n), n)


def two_sided_p(t):
    if not math.isfinite(t):
        return float("nan")
    return math.erfc(abs(t) / math.sqrt(2.0))


def log(m, f):
    print(m)
    if f is not None:
        f.write(m + "\n")


def consistency_check(store, f=None):
    checks = []
    checks.append(("preregistration sha256 over FROZEN block", sha256_frozen_block() == PREREG_SHA256,
                   sha256_frozen_block()[:16] + "…"))
    checks.append(("candidate spec sha256 (76a96545…)", sha256_file(SPEC_PATH) == SPEC_SHA256,
                   sha256_file(SPEC_PATH)[:16] + "…"))
    checks.append(("cohort store sha256 (e1375264…fba)", sha256_file(STORE) == STORE_SHA256,
                   sha256_file(STORE)[:16] + "…"))
    checks.append(("extension calendar sha256 (a7a4eedf…)", sha256_file(CAL_EXT) == CAL_EXT_SHA256,
                   sha256_file(CAL_EXT)[:16] + "…"))
    base = json.load(open(CAL_BASE))
    ext = json.load(open(CAL_EXT))
    checks.append(("base calendar embedded sha256 (5012be23…)", base.get("sha256") == CAL_BASE_SHA256,
                   str(base.get("sha256"))[:16] + "…"))
    eff = sorted(set(base["sessions"]) | set(ext["admitted_sessions"]))
    checks.append(("effective calendar = base 386 ∪ ext 11 = 397",
                   len(base["sessions"]) == 386 and len(ext["admitted_sessions"]) == 11 and len(eff) == 397,
                   f"{len(base['sessions'])}+{len(ext['admitted_sessions'])}->{len(eff)}"))

    cur = store.cursor()
    led_counts = dict(cur.execute(
        "SELECT COALESCE(exclusion_rule,'ADMITTED'), COUNT(*) FROM admissibility_ledger "
        "GROUP BY admissible, exclusion_rule").fetchall())
    checks.append(("ledger admitted == 61335", led_counts.get("ADMITTED") == N_ADMITTED,
                   str(led_counts.get("ADMITTED"))))
    for rule, n_reg in LEDGER.items():
        checks.append((f"ledger {rule} == {n_reg}", led_counts.get(rule) == n_reg,
                       str(led_counts.get(rule))))
    total = cur.execute("SELECT COUNT(*) FROM admissibility_ledger").fetchone()[0]
    checks.append((f"ledger total == {N_CANDIDATE} (exact, MECE)", total == N_CANDIDATE, str(total)))
    n_ses, lo, hi = cur.execute("SELECT COUNT(DISTINCT session_date), MIN(session_date), "
                                "MAX(session_date) FROM admissibility_ledger WHERE admissible=1").fetchone()
    checks.append(("76 admitted sessions in 2026-04-28..2026-09-11",
                   n_ses == N_SESSIONS and (lo, hi) == SESSION_WINDOW, f"{n_ses} {lo}..{hi}"))
    n_tk = cur.execute("SELECT COUNT(DISTINCT ticker) FROM admissibility_ledger WHERE admissible=1").fetchone()[0]
    checks.append(("868 admitted tickers", n_tk == N_TICKERS, str(n_tk)))
    n_bars = cur.execute("SELECT COUNT(*) FROM flow_bars_v004").fetchone()[0]
    checks.append(("19,793,865 bar rows", n_bars == N_BAR_ROWS, str(n_bars)))
    led_ses = [r[0] for r in cur.execute(
        "SELECT DISTINCT session_date FROM admissibility_ledger WHERE admissible=1")]
    checks.append(("every admitted session in effective calendar", set(led_ses) <= set(eff), ""))
    in_eff = [d for d in X3_EXCLUDED if d in set(eff)]
    checks.append(("the 8 X3-excluded sessions absent from effective calendar", in_eff == [], str(in_eff)))
    n, nd = cur.execute("SELECT COUNT(*), COUNT(DISTINCT ticker||'|'||session_date) "
                        "FROM admissibility_ledger WHERE admissible=1").fetchone()
    checks.append(("admitted cells unique per (ticker, session)", n == nd, f"{n}/{nd}"))
    fm = dict(cur.execute("SELECT key, value FROM freeze_manifest").fetchall())
    checks.append(("store freeze_status == FROZEN", fm.get("freeze_status") == '"FROZEN"',
                   str(fm.get("freeze_status"))))

    n_pass = sum(1 for _, ok, _ in checks if ok)
    log("\n=== EXP-PM-0009 pre-execution integrity gate (no outcome statistic computed) ===", f)
    for name, ok, detail in checks:
        log(f"  [{'PASS' if ok else 'FAIL'}] {name} ({detail})", f)
    log(f"Result: {n_pass}/{len(checks)} PASS", f)
    return n_pass, len(checks)


def load_ohlcv(conn):
    """ohlcv outcome leg + liquidity history. Program convention COALESCE(is_final,1)=1,
    close > 0 (HYP-PM-0008_SPEC §4). Buffer 2025-09-01..2026-09-30 covers 60 sessions
    before the first formation date and the k-ahead lookup legs."""
    rows = conn.execute(
        "SELECT ticker, date, close, volume FROM ohlcv "
        "WHERE date BETWEEN '2025-09-01' AND '2026-09-30' AND COALESCE(is_final,1)=1 "
        "AND close > 0 AND volume > 0 ORDER BY ticker, date").fetchall()
    close, tv_dates = {}, {}
    for tk, d, c, v in rows:
        close[(tk, d)] = float(c)
        tv_dates.setdefault(tk, []).append((d, float(c) * float(v)))
    return close, tv_dates, len(rows)


def trailing_tv_median(tv_dates, tk, t, window=TV_WINDOW):
    """Median traded value over the `window` ticker-sessions strictly before t (shift(1)).
    Harness convention (g1_harness c7_build_panel): sorted window, median = w[len(w)//2].
    Returns None if fewer than `window` prior observations exist (floor unmet)."""
    s = tv_dates.get(tk)
    if not s:
        return None
    vals = [v for d, v in s if d < t]
    if len(vals) < window:
        return None
    w = sorted(vals[-window:])
    return w[len(w) // 2]


def run(store, conn, f):
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    script_sha = sha256_file(__file__)
    log(f"EXP-PM-0009 confirmatory run @ {ts}", f)
    n_pass, n_total = consistency_check(store, f)
    if n_pass != n_total:
        log("ABORTING: integrity gate failed. No statistic computed.", f)
        sys.exit(1)

    base = json.load(open(CAL_BASE))
    ext = json.load(open(CAL_EXT))
    eff = sorted(set(base["sessions"]) | set(ext["admitted_sessions"]))
    eff_idx = {d: i for i, d in enumerate(eff)}

    # --- formation leg: per admitted cell, segment nets (16:00-16:14 bars never touched) ---
    log("\naggregating segment nets from flow_bars_v004 (admitted cells only)...", f)
    seg = store.execute(
        "SELECT l.ticker, l.session_date, "
        " SUM(CASE WHEN b.bar_time BETWEEN '09:00' AND '09:59' THEN b.buy_lot ELSE 0 END"
        "   - CASE WHEN b.bar_time BETWEEN '09:00' AND '09:59' THEN b.sell_lot ELSE 0 END),"
        " SUM(CASE WHEN b.bar_time BETWEEN '14:50' AND '15:49' THEN b.buy_lot ELSE 0 END"
        "   - CASE WHEN b.bar_time BETWEEN '14:50' AND '15:49' THEN b.sell_lot ELSE 0 END),"
        " SUM(CASE WHEN b.bar_time BETWEEN '09:00' AND '15:49' THEN b.buy_lot ELSE 0 END"
        "   - CASE WHEN b.bar_time BETWEEN '09:00' AND '15:49' THEN b.sell_lot ELSE 0 END) "
        "FROM admissibility_ledger l JOIN flow_bars_v004 b "
        "  ON b.ticker = l.ticker AND b.trade_date = l.session_date "
        "WHERE l.admissible = 1 GROUP BY l.ticker, l.session_date").fetchall()
    population = [(tk, d, o, late, dn) for tk, d, o, late, dn in seg if dn > 0]
    log(f"admitted cells: {len(seg):,}; population (daily_net > 0): {len(population):,}", f)

    # --- outcome leg inputs ---
    close, tv_dates, n_px = load_ohlcv(conn)
    log(f"ohlcv rows read (2025-09-01..2026-09-30, is_final, close>0, volume>0): {n_px:,}", f)
    ca = set(conn.execute("SELECT ticker, date FROM corporate_actions "
                          "WHERE date BETWEEN '2026-04-28' AND '2026-09-30'").fetchall())
    log(f"corporate_actions rows in window: {len(ca):,}", f)

    res = {
        "experiment_id": "EXP-PM-0009", "hypothesis_id": "HYP-PM-0009",
        "run_id": "EXP-PM-0009/R2", "run_utc": ts,
        "registered_specification": {
            "record": "docs/research_programs/P-M/HYP-PM-0009_REGISTERED.md",
            "preregistration_sha256": PREREG_SHA256,
            "candidate_spec_sha256": SPEC_SHA256,
            "cohort_store_sha256": STORE_SHA256},
        "provenance": {
            "git_commit_at_registration": "e0e3f915cbcd80c06caa87f00cf2f7611d82f6e9",
            "script_sha256": script_sha,
            "python": platform.python_version(),
            "cohort_store": "I7_V004_ADMISSIBLE_v1.sqlite",
            "outcome_source": "data/walkforward.db ohlcv / corporate_actions (read-only)"},
        "cohort": {"sessions": N_SESSIONS, "window": list(SESSION_WINDOW),
                   "admitted_ticker_days": N_ADMITTED, "tickers": N_TICKERS,
                   "bar_rows": N_BAR_ROWS, "candidate_cells": N_CANDIDATE,
                   "ledger": {"admitted": N_ADMITTED, **LEDGER}},
        "estimator": "daily-series-first (BFI-001 §G/§I); Newey-West HAC lag 5; two-sided p (erfc)",
        "cost_convention": "theta_net = theta_primary - 0.006 (sensitivity only)",
    }

    # --- estimation layer per horizon ---
    def estimate(k):
        acc = {"population": len(population), "x6_consecutivity": 0,
               "x5_total": 0, "x5_ca": 0, "x5_raja": 0, "x5_missing_close": 0,
               "x5_price_floor": 0, "x5_liquidity_floor": 0}
        surv = []
        for tk, t, _o, _l, _dn in population:
            i = eff_idx.get(t)
            # X6: t, t+1, ..., t+1+k (entry t+1, exit t+1+k) must exist as strictly
            # consecutive admitted sessions on the effective calendar
            if i is None or i + 1 + k >= len(eff):
                acc["x6_consecutivity"] += 1
                continue
            t1, tk_ = eff[i + 1], eff[i + 1 + k]   # entry reference close(t+1); exit close(t+1+k)
            # X5 in registered order: CA on t..t+1+k; RAJA; closes; price floor; liquidity floor
            if any((tk, eff[j]) in ca for j in range(i, i + k + 2)):
                acc["x5_ca"] += 1; continue
            if tk == "RAJA":
                acc["x5_raja"] += 1; continue
            ct, c1, ck = close.get((tk, t)), close.get((tk, t1)), close.get((tk, tk_))
            if ct is None or c1 is None or ck is None:
                acc["x5_missing_close"] += 1; continue
            if ct < PRICE_FLOOR:
                acc["x5_price_floor"] += 1; continue
            med = trailing_tv_median(tv_dates, tk, t)
            if med is None or med < TV_FLOOR:
                acc["x5_liquidity_floor"] += 1; continue
            # state from registered signal construction (computed at accrual quantities)
            late_frac = _l / _dn
            state = "LATE_TILTED" if late_frac >= STATE_THRESHOLD else "EARLY_TILTED"
            fwd = ck / c1 - 1.0
            surv.append((t, state, fwd))
        acc["surviving_cells"] = len(surv)
        acc["x5_total"] = acc["x5_ca"] + acc["x5_raja"] + acc["x5_missing_close"] + \
            acc["x5_price_floor"] + acc["x5_liquidity_floor"]

        by_date = {}
        for t, state, fwd in surv:
            by_date.setdefault(t, {"LATE_TILTED": [], "EARLY_TILTED": []})[state].append(fwd)
        m, skipped = [], []
        for d in sorted(by_date):
            sides = by_date[d]
            if len(sides["LATE_TILTED"]) >= 1 and len(sides["EARLY_TILTED"]) >= 1:
                m.append(sum(sides["LATE_TILTED"]) / len(sides["LATE_TILTED"])
                         - sum(sides["EARLY_TILTED"]) / len(sides["EARLY_TILTED"]))
            else:
                skipped.append(d)
        theta = sum(m) / len(m) if m else float("nan")
        tstat, n = nw_t(m, NW_LAG)
        p = two_sided_p(tstat)
        return {"k": k, "accounting": acc, "n_dates_m": len(m), "n_dates_skipped": len(skipped),
                "skipped_dates": skipped, "n_dates_below_min10_for_nw": (n if n < 10 else None),
                "theta_primary": theta, "nw_t": tstat, "nw_n": n,
                "two_sided_p": p, "holm_p": p,  # single cell: Holm at the primary is the identity
                "theta_net_sensitivity": theta - FRICTION}

    for k in KS:
        r = estimate(k)
        res["primary" if k == KPRIMARY else f"robustness_k{k}"] = r
        tag = "PRIMARY" if k == KPRIMARY else "robustness"
        log(f"\n[k={k} {tag}] dates m(d)={r['n_dates_m']} skipped={r['n_dates_skipped']} "
            f"surviving cells={r['accounting']['surviving_cells']:,}", f)
        log(f"  accounting: X6={r['accounting']['x6_consecutivity']:,} X5={r['accounting']['x5_total']:,} "
            f"(ca={r['accounting']['x5_ca']:,} raja={r['accounting']['x5_raja']:,} "
            f"missing_close={r['accounting']['x5_missing_close']:,} "
            f"price_floor={r['accounting']['x5_price_floor']:,} "
            f"liquidity_floor={r['accounting']['x5_liquidity_floor']:,})", f)
        log(f"  theta_primary = {r['theta_primary']:.6f}  ({r['theta_primary']*100:.4f}%)  "
            f"NW_t(lag5) = {r['nw_t']:.4f}  two-sided p = {r['two_sided_p']:.6f}", f)
        log(f"  theta_net sensitivity = {r['theta_net_sensitivity']*100:.4f}%", f)

    prim = res["primary"]
    passed = (prim["theta_primary"] > 0) and (prim["two_sided_p"] < 0.05)
    res["decision"] = {
        "rule": "PASS iff theta_primary > 0 AND two-sided p < 0.05 (registered kill rule)",
        "theta_primary_positive": prim["theta_primary"] > 0,
        "two_sided_p_below_0.05": prim["two_sided_p"] < 0.05,
        "classification": "PASS" if passed else "FAIL (F2 · prediction failure)",
        "interpretation_limit": "I7 carries NO power claim (D-050). If not rejected, this is NOT "
                                "evidence of absence and must not be reported as one. A negative "
                                "theta falls inside H0 as a non-rejection, never a reversed finding.",
        "r7_provenance_limitation": "PIT provenance is TRUE WITH QUALIFICATION (R7): rests on "
                                    "stockbit_flow.updated_at written by this system's own writer in "
                                    "the same commit; supports contemporaneous custody, NOT "
                                    "independent re-verification of the original vendor response. "
                                    "Verification limitation, not availability. 200/200 source "
                                    "spot-check matches (I7_V004_SOURCE_PROVENANCE_v1.json).",
    }

    with open(f"{OUT}/results.json", "w") as jf:
        json.dump(res, jf, indent=2)
    log(f"\nresults.json + execution.log written to {OUT}", f)
    log(f"CLASSIFICATION: {res['decision']['classification']}", f)


def main(consistency_only):
    store = sqlite3.connect(f"file:{STORE}?mode=ro", uri=True)
    store.execute("PRAGMA query_only = ON;")
    conn = sqlite3.connect(f"file:{PROD_DB}?mode=ro", uri=True)
    conn.execute("PRAGMA query_only = ON;")
    if consistency_only:
        consistency_check(store, f=None)
        store.close(); conn.close()
        return
    f = open(f"{OUT}/execution.log", "w")
    try:
        run(store, conn, f)
    finally:
        f.close()
        store.close(); conn.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--consistency-check", action="store_true",
                    help="Run ONLY the pre-execution integrity gate. Computes no "
                         "flow-vs-return statistic.")
    args = ap.parse_args()
    main(consistency_only=args.consistency_check)
