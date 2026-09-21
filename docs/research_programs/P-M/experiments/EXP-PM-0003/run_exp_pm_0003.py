#!/usr/bin/env python3
"""EXP-PM-0003 — confirmatory experiment for HYP-PM-0003
(frozen registration sha256 a2db92047e5e23f8c0bb8949797e7750706b6bfe33fa744509ef6a782f6f53f5).

Runs the registered spec EXACTLY. No tuning, no optimisation, no parameter search,
no clustered inference, no new statistical methodology beyond what was CRO-adopted.

- net_flow(ticker,date) = SUM(lot)  -- already-signed, no BUY-minus-SELL subtraction
  (HYP-PM-0003_REGISTERED.md `signed_lot_convention`)
- fwd_ret_k  = close_{t+k} / close_t - 1        within (ticker, calendar order)
  (k trading days ahead, formation on day t)
- signed_continuation_k = sign(net_flow_t) * fwd_ret_k
  (>0 == continuation == M2.1 permanence; this is the OPPOSITE sign convention from
  EXP-PM-0001's signed_reversal, which used -sign(OFI)*rev for a REVERSION prediction --
  HYP-PM-0003 predicts CONTINUATION, so the sign is NOT negated)
- friction = 0.60% round-trip (engine/exits/costs.py -- same authority as EXP-PM-0001)
- inference: bootstrap_ci (research/statistics.py) on the pooled k=7 signed_continuation
  sample -- the REGISTERED primary test (HYP-PM-0003_REGISTERED.md `statistical_test`).
  NOT double-clustered, NOT a new method -- no clustered-inference code exists in this
  repository and none is introduced here.
- dependence diagnostic: HYP-PM-0001 deflation ladder (N, N/10, N/100), reported as a
  labeled SENSITIVITY DIAGNOSTIC ONLY, not a formal correction (HYP-PM-0003_POWER.md §5).
  Implemented as systematic thinning of the pooled sample, re-running bootstrap_ci at
  each thinned size with the SAME fixed seed.
- unit of analysis: one (ticker, formation-date) pair with net_flow != 0
  (HYP-PM-0003_REGISTERED.md `unit_of_analysis`) -- NOT a trade, NOT min_n=100's unit.

Read-only on data/walkforward.db (opened via a read-only URI, belt-and-suspenders).
Writes results JSON + a text log ONLY when actually executed. No DB writes, no prod code.

--consistency-check runs ONLY the pre-execution identity/integrity verification
(dataset fingerprint, roster, window, exclusion) against the frozen registration and
exits -- it computes NO flow-vs-return statistic and is safe to run under G2 review.
"""
import sqlite3, json, sys, datetime, hashlib, argparse
import numpy as np, pandas as pd

sys.path.insert(0, "/home/tjiesar/10 Projects/idx-walkforward-5001")
from tools.broker_flow_idx80_gap import idx80_universe, canonical_trading_dates
from research.statistics import bootstrap_ci, SEED

DB = "file:data/walkforward.db?mode=ro"
FRICTION = 0.0060                  # 0.60% round-trip -- registered friction model, engine/exits/costs.py
KS = [3, 7, 15]                    # k=7 PRIMARY; 3/15 robustness-gradient consistency (declared, not selection)
KPRIMARY = 7
WIN_START, WIN_END = "2025-01-02", "2026-08-27"
EXCLUDED_DATE = "2026-08-25"
OUT = "docs/research_programs/P-M/experiments/EXP-PM-0003"

REGISTERED_FINGERPRINT = "329b22e49f0ef882b6da031f437e9d87084d2863837ebf8c830de362b7942558"
REGISTERED_ROSTER_SHA256 = "7d4eb1004e7d1e83153eede9a5d4e458ab5298ac1a4a4d7fa301f095f665eee0"
REGISTERED_ROW_COUNT = 1_222_713
REGISTERED_HYPOTHESIS_SHA256 = "a2db92047e5e23f8c0bb8949797e7750706b6bfe33fa744509ef6a782f6f53f5"


def log(m, f):
    print(m)
    if f is not None:
        f.write(m + "\n")


def _dataset_a_fingerprint(conn, roster):
    """Reproduces the exact F-1 fingerprint method (per-ticker aggregate, SHA-256).
    Read-only. Returns (fingerprint_hex, total_rows) -- no flow-vs-return computation."""
    placeholders = ",".join("?" for _ in roster)
    q = (f"SELECT ticker, COUNT(*), MIN(trade_date), MAX(trade_date), "
         f"SUM(CAST(lot AS INTEGER)), SUM(CAST(lot_value AS INTEGER)) "
         f"FROM broker_flow WHERE ticker IN ({placeholders}) "
         f"AND trade_date BETWEEN ? AND ? AND trade_date != ? "
         f"GROUP BY ticker ORDER BY ticker")
    params = list(roster) + [WIN_START, "2026-08-27", EXCLUDED_DATE]
    rows = conn.execute(q, params).fetchall()
    h = hashlib.sha256()
    for r in rows:
        h.update("|".join(str(x) for x in r).encode())
        h.update(b"\n")
    total = sum(r[1] for r in rows)
    return h.hexdigest(), total


def consistency_check(conn, f=None):
    """Pre-execution identity/integrity gate (mirrors EXP-PM-0001 MANIFEST's
    'Consistency check' section, performed in-script here rather than only in the
    manifest). Computes NO flow-vs-return statistic. Returns (n_pass, n_total, details)."""
    checks = []

    roster = idx80_universe(conn)
    # Newline-joined + trailing newline -- reproduces the ORIGINAL R-3 receipt method
    # (sqlite3 CLI "... > file.txt" redirect, then sha256sum on the file), which is
    # the convention actually sealed into HYP-PM-0003_REGISTERED.md's frozen record.
    # NOTE: a later turn's cross-check used comma-joined text and got a DIFFERENT hash
    # (5f2afa70…) -- that was an inconsistent, uncorrected method, not a data change.
    # This script deliberately reproduces the SEALED convention, not that later one.
    roster_str = "\n".join(sorted(roster)) + "\n"
    roster_hash = hashlib.sha256(roster_str.encode()).hexdigest()
    checks.append(("roster == 79 tickers", len(roster) == 79, f"got {len(roster)}"))
    checks.append(("roster sha256 matches registration", roster_hash == REGISTERED_ROSTER_SHA256,
                    f"got {roster_hash[:16]}…"))

    fp, total_rows = _dataset_a_fingerprint(conn, roster)
    checks.append(("dataset fingerprint matches registration", fp == REGISTERED_FINGERPRINT,
                    f"got {fp[:16]}…"))
    checks.append(("row count matches registration (1,222,713)", total_rows == REGISTERED_ROW_COUNT,
                    f"got {total_rows}"))

    excl = conn.execute("SELECT COUNT(*) FROM broker_flow WHERE trade_date=?",
                         (EXCLUDED_DATE,)).fetchone()[0]
    checks.append((f"{EXCLUDED_DATE} exclusion clean (0 rows)", excl == 0, f"got {excl}"))

    confirmed, _ = canonical_trading_dates(conn, WIN_START, "2026-08-28")
    checks.append(("388 canonical trading dates in window", len(confirmed) == 388,
                    f"got {len(confirmed)}"))

    checks.append(("k_primary == 7 (registered)", KPRIMARY == 7, f"got {KPRIMARY}"))
    checks.append(("friction == 0.60% (registered)", FRICTION == 0.0060, f"got {FRICTION}"))
    checks.append(("robustness gradient == {3,7,15} (registered)", KS == [3, 7, 15], f"got {KS}"))
    checks.append(("statistical test == bootstrap_ci (registered, no clustered inference)",
                    True, "static: script imports research.statistics.bootstrap_ci only"))
    checks.append(("bootstrap seed reused from research.statistics.SEED (20260711)",
                    SEED == 20260711, f"got {SEED}"))

    n_pass = sum(1 for _, ok, _ in checks if ok)
    n_total = len(checks)
    log(f"\n=== EXP-PM-0003 consistency check (pre-execution gate) ===", f)
    for name, ok, detail in checks:
        log(f"  [{'PASS' if ok else 'FAIL'}] {name} ({detail})", f)
    log(f"Result: {n_pass}/{n_total} PASS", f)
    if n_pass != n_total:
        log("STOPPED -- mismatch against frozen registration. Execution would not proceed.", f)
    return n_pass, n_total, checks


def main(consistency_only: bool):
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    conn = sqlite3.connect(DB, uri=True)
    conn.execute("PRAGMA query_only = ON;")

    if consistency_only:
        consistency_check(conn, f=None)
        conn.close()
        return

    f = open(f"{OUT}/execution.log", "w")
    log(f"EXP-PM-0003 confirmatory run @ {ts}", f)
    n_pass, n_total, checks = consistency_check(conn, f)
    if n_pass != n_total:
        log("ABORTING: consistency check failed.", f)
        f.close()
        conn.close()
        sys.exit(1)

    roster = idx80_universe(conn)
    placeholders = ",".join("?" for _ in roster)

    log("\nloading broker_flow (Dataset A exact scope)...", f)
    bf = pd.read_sql(
        f"SELECT ticker, trade_date, lot FROM broker_flow "
        f"WHERE ticker IN ({placeholders}) AND trade_date BETWEEN ? AND ? "
        f"AND trade_date != ?",
        conn, params=list(roster) + [WIN_START, "2026-08-27", EXCLUDED_DATE])
    log(f"loaded {len(bf):,} raw broker_flow rows", f)

    net = bf.groupby(["ticker", "trade_date"], as_index=False)["lot"].sum()
    net = net.rename(columns={"lot": "net_flow"})
    net = net[net.net_flow != 0].copy()
    log(f"nonzero net_flow (ticker,date) observations: {len(net):,}", f)

    log("loading ohlcv close series...", f)
    px = pd.read_sql(
        f"SELECT ticker, date, close FROM ohlcv WHERE ticker IN ({placeholders}) "
        f"AND date BETWEEN ? AND ?",
        conn, params=list(roster) + [WIN_START, "2026-09-30"])  # trailing buffer for k-ahead lookups
    px = px.sort_values(["ticker", "date"]).reset_index(drop=True)

    res = {"experiment_id": "EXP-PM-0003", "hypothesis_id": "HYP-PM-0003",
           "registration_sha256": REGISTERED_HYPOTHESIS_SHA256,
           "run_utc": ts, "friction_roundtrip": FRICTION, "k_primary": KPRIMARY,
           "statistical_test": "bootstrap_ci",
           "dataset": {"table": "broker_flow", "scope": "Dataset A (frozen)",
                       "fingerprint": REGISTERED_FINGERPRINT,
                       "range": [WIN_START, "2026-08-27"], "rows": REGISTERED_ROW_COUNT,
                       "tickers": len(roster)},
           "n_analysis_observations": int(len(net))}

    res["continuation"] = {}
    for k in KS:
        rows = []
        for ticker, g in px.groupby("ticker"):
            g = g.reset_index(drop=True)
            g["fwd_ret"] = g["close"].shift(-k) / g["close"] - 1.0
            g["ticker"] = ticker
            rows.append(g[["ticker", "date", "fwd_ret"]])
        fwd = pd.concat(rows, ignore_index=True).rename(columns={"date": "trade_date"})

        merged = net.merge(fwd, on=["ticker", "trade_date"], how="inner").dropna(subset=["fwd_ret"])
        signed_cont = np.sign(merged.net_flow.to_numpy()) * merged.fwd_ret.to_numpy()

        ci = bootstrap_ci(signed_cont)  # registered test, default n_boot/ci/seed (SEED=20260711)
        gross_pct = ci["point"] * 100
        net_of_cost_pct = (ci["point"] - FRICTION) * 100
        entry = {**ci, "gross_mean_pct": gross_pct, "net_of_cost_pct": net_of_cost_pct}

        # dependence sensitivity diagnostic ONLY -- HYP-PM-0001 deflation ladder,
        # NOT a formal correction (HYP-PM-0003_POWER.md §5)
        entry["dependence_sensitivity"] = {}
        rng = np.random.default_rng(SEED)
        n_full = signed_cont.size
        for label, frac in (("N", 1.0), ("N_10", 0.1), ("N_100", 0.01)):
            n_sub = max(2, int(n_full * frac))
            idx = rng.choice(n_full, size=n_sub, replace=False)
            sub_ci = bootstrap_ci(signed_cont[idx])
            entry["dependence_sensitivity"][label] = {
                "n": sub_ci["n"], "point_pct": sub_ci["point"] * 100,
                "lo_pct": sub_ci["lo"] * 100, "hi_pct": sub_ci["hi"] * 100}

        res["continuation"][f"k{k}"] = entry
        tag = "PRIMARY" if k == KPRIMARY else "robustness"
        log(f"\n[k={k} {tag}] signed_continuation gross={gross_pct:.4f}%  "
            f"CI95=[{ci['lo']*100:.4f},{ci['hi']*100:.4f}]%  n={ci['n']}", f)
        log(f"   NET of 0.60% friction = {net_of_cost_pct:.4f}%", f)

    json.dump(res, open(f"{OUT}/results.json", "w"), indent=2)
    log(f"\nresults.json + execution.log written to {OUT}", f)
    f.close()
    conn.close()


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--consistency-check", action="store_true",
                    help="Run ONLY the pre-execution identity/integrity gate. "
                         "Computes no flow-vs-return statistic. Safe for G2 review.")
    args = p.parse_args()
    main(consistency_only=args.consistency_check)
