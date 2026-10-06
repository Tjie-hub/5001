"""Real-corpus PIT check for HYP-PM-0015 at G0 — reads NO outcomes.

Re-runs the three predeclared PIT claims of PREDECLARATION.md §7 on the actual
frozen dataset (load_extended_ohlcv(issuance=True) + IHSG read-only):

  (a) features bit-identical when the panel is truncated at the feature cutoff
      t, for sampled rebalance dates across all eras;
  (c) the universe at each entry date D is identical when computed from the
      truncated panel (uses only data ≤ D−1);
  (b) the embargo holds on the REAL calendar: every training label window ends
      strictly before its refit year's first prediction month; December is
      never a training label of a January refit.

Monthly returns are never computed here; no model is fit. Run from the repo
root (data artifacts resolve via ML_RANK_HIST_PKL / ML_RANK_SPLITS_PKL when
executed from a code-only worktree). Output: PIT_CHECK_G0.json next to this
file + a stdout summary. Nothing else is written.
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
REPO_ROOT = HERE.parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np  # noqa: E402

import ml_rank_model as M  # noqa: E402

# sampled feature-cutoff dates across eras (one per ~2.5 years, all eras)
SAMPLE_MONTHS = ("2003-01", "2006-01", "2009-01", "2012-01", "2015-01",
                 "2017-06", "2019-01", "2021-06", "2023-06", "2025-06")


def main() -> dict:
    t0 = time.time()
    P, ihsg = M.load_panel()
    dates = P["close"].index
    n_sessions, n_tickers = len(dates), P["close"].shape[1]
    F = M.compute_features(P)
    elig = M.eligibility_mask(P["close"], P["volume"])
    schedule = {r["month"]: r for r in M.build_schedule(P)}

    results = {"panel": {"n_sessions": int(n_sessions), "n_tickers": int(n_tickers),
                         "first": str(dates[0].date()), "last": str(dates[-1].date())},
               "checks": [], "all_pass": True}

    for m in SAMPLE_MONTHS:
        if m not in schedule:
            # nearest later sampled month present in the calendar
            later = [k for k in schedule if k >= m]
            if not later:
                continue
            m = later[0]
        rec = schedule[m]
        t = rec["t"]
        Pt = {k: v.iloc[: t + 1] for k, v in P.items()}
        Ft = M.compute_features(Pt)
        et = M.eligibility_mask(Pt["close"], Pt["volume"])
        entry = {"month": m, "cutoff_date": str(dates[t].date())}
        ok = True
        for f in M.FEATURES:
            same = np.array_equal(F[f].iloc[: t + 1].values, Ft[f].values,
                                  equal_nan=True)
            entry[f] = bool(same)
            ok &= same
        same_uni = np.array_equal(elig.iloc[: t + 1].values, et.values)
        entry["universe_truncated_identity"] = bool(same_uni)
        ok &= same_uni
        entry["pass"] = bool(ok)
        results["all_pass"] &= ok
        results["checks"].append(entry)
        print(f"[pit] {m} cutoff {dates[t].date()} -> {'PASS' if ok else 'FAIL'}")

    # (b) embargo on the real calendar (dates only, no returns)
    embargo = {"violations": 0, "refits": 0}
    for year in sorted({r["year"] for r in schedule.values()}):
        train, pred = M.refit_split(list(schedule.values()), year)
        if not pred:
            continue
        embargo["refits"] += 1
        first_pred = min(pred)
        for tm in train:
            if not (M.month_key_next(tm) < first_pred):
                embargo["violations"] += 1
        if first_pred.endswith("-01") and train:
            assert max(train).endswith("-11"), (year, max(train))
    results["embargo"] = embargo
    results["all_pass"] &= (embargo["violations"] == 0)

    with M.db_connect(read_only=True) as c:
        results["dataset_fingerprint"] = M.dataset_fingerprint(c)
    results["ihsg_rows"] = int(len(ihsg))
    results["ihsg_first"] = str(ihsg.index[0].date())
    results["elapsed_s"] = round(time.time() - t0, 1)
    results["generated_utc"] = datetime.now(timezone.utc).isoformat()

    out = HERE / "PIT_CHECK_G0.json"
    out.write_text(json.dumps(results, indent=1))
    print(json.dumps({k: results[k] for k in
                      ("panel", "embargo", "all_pass", "elapsed_s")}, indent=1))
    print(f"fingerprint: {results['dataset_fingerprint']['sha256'][:16]}… "
          f"max_date {results['dataset_fingerprint']['max_date']} "
          f"rows {results['dataset_fingerprint']['total_rows']}")
    return results


if __name__ == "__main__":
    r = main()
    sys.exit(0 if r["all_pass"] else 1)
