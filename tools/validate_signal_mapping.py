#!/usr/bin/env python3
"""G-7 signal-mapping validation for the P-M prospective protocol.

The protocol's G-7 section specifies this check and names this script; until
2026-09-16 the script did not exist and gate G-5 in `prospective_gate.py` was
`ok = os.path.exists(done_flag)` with a hardcoded result string. The gate built
to catch a wrong signal mapping could not run, and did not catch one.

WHAT IT CHECKS
--------------
Whether the protocol's declared signal formula, evaluated on the frozen raw
payload corpus, reproduces the production quantity the historical observation
was actually computed on.

    declared formula   Sigma_buy(bval) + Sigma_sell(sval)   (marketdetectors broker_summary)
    comparison target  stockbit_flow.net_value              (order-trade/trade-book/chart)

It also reports the ZERO-SUM INVARIANT explicitly, because a low match rate and
a structurally impossible signal are different failures and only the second one
tells you the endpoint is wrong. `broker_summary` returns the complete broker
population for a ticker-day, whose signed values necessarily sum to zero; a
signal defined on it is identically zero and can never fire.

OUTPUT
------
`mapping_validation_report.json` + `.sha256` next to the protocol, written
deterministically (full corpus, no sampling, sorted keys) so an independent
checker re-running this script reproduces a byte-identical report.

EXIT CODE
---------
0 = PASS, 1 = FAIL. The gate consumes the exit code and the report verdict,
never a flag file.

Usage:
    python3 tools/validate_signal_mapping.py
    python3 tools/validate_signal_mapping.py --out-dir <dir>
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import sqlite3
import sys
from collections import Counter
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

STORE = os.path.join(ROOT, "docs", "research_programs", "P-M", "dataset_b",
                     "store", "DATASET_B_BROKER_FLOW_STORE_v1.sqlite")
WF = os.path.join(ROOT, "data", "walkforward.db")
OUT_DIR = os.path.join(ROOT, "docs", "research_programs", "P-M", "prospective_validation")

TOLERANCE = 0.005          # protocol G-7
MATCH_THRESHOLD = 0.99     # protocol G-7 pass bar, among EVALUABLE with a target
EVALUABLE_SHARE_MIN = 0.50  # protocol G-7 coverage bar


def ro(path: str):
    if not os.path.exists(path):
        raise SystemExit(f"missing required store: {path}")
    c = sqlite3.connect("file:" + path + "?mode=ro", uri=True)
    c.execute("PRAGMA query_only = ON;")
    return c


def classify(payload: bytes):
    """-> (class, computed_or_None). Classes per protocol G-7."""
    try:
        j = json.loads(gzip.decompress(payload))
    except Exception:
        return "UNPARSEABLE", None
    bs = ((j.get("data") or {}).get("broker_summary") or {})
    buys = bs.get("brokers_buy") or []
    sells = bs.get("brokers_sell") or []
    if not buys and not sells:
        return "EMPTY", None
    if not all("bval" in x for x in buys) or not all("sval" in x for x in sells):
        return "INCOMPLETE", None
    try:
        total = sum(float(x["bval"]) for x in buys) + sum(float(x["sval"]) for x in sells)
    except (TypeError, ValueError):
        return "INCOMPLETE", None
    return "EVALUABLE", total


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default=OUT_DIR)
    a = ap.parse_args()

    store, wf = ro(STORE), ro(WF)
    target = {(t, str(d)[:10]): v for t, d, v in
              wf.execute("SELECT ticker, trade_date, net_value FROM stockbit_flow")}
    wf.close()

    classes: Counter = Counter()
    matched = mismatched = no_target = 0
    zero_valued = 0
    sessions: set[str] = set()
    examples: list[dict] = []

    rows = store.execute(
        "SELECT ticker, session_date, raw_json_gz FROM raw_responses "
        "ORDER BY session_date, ticker")
    n_rows = 0
    for ticker, session, blob in rows:
        n_rows += 1
        day = str(session)[:10]
        sessions.add(day)
        if blob is None:
            classes["UNPARSEABLE"] += 1
            continue
        cls, computed = classify(blob)
        classes[cls] += 1
        if cls != "EVALUABLE":
            continue
        if computed == 0:
            zero_valued += 1
        tgt = target.get((ticker, day))
        if tgt is None:
            no_target += 1
            continue
        tgt = float(tgt)
        if abs(computed - tgt) / max(1.0, abs(tgt)) <= TOLERANCE:
            matched += 1
        else:
            mismatched += 1
            if len(examples) < 10:
                examples.append({"ticker": ticker, "session": day,
                                 "computed": computed, "target": tgt})
    store.close()

    evaluable = classes["EVALUABLE"]
    comparable = matched + mismatched
    match_rate = (matched / comparable) if comparable else 0.0
    evaluable_share = (evaluable / n_rows) if n_rows else 0.0
    zero_share = (zero_valued / evaluable) if evaluable else 0.0

    failures = []
    if match_rate < MATCH_THRESHOLD:
        failures.append(
            f"match rate {match_rate:.4%} < {MATCH_THRESHOLD:.0%} among EVALUABLE cells with a target")
    if evaluable_share < EVALUABLE_SHARE_MIN:
        failures.append(
            f"EVALUABLE share {evaluable_share:.2%} < {EVALUABLE_SHARE_MIN:.0%} (coverage)")
    if zero_share > 0.99:
        failures.append(
            f"ZERO-SUM INVARIANT: the declared formula evaluates to exactly 0 on "
            f"{zero_share:.2%} of EVALUABLE cells. broker_summary returns the complete "
            f"broker population, whose signed values sum to zero by construction, so this "
            f"signal is identically zero and can never fire. The endpoint is wrong, not the "
            f"tolerance.")

    report = {
        "spec": "G-7 signal-mapping validation",
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "store": os.path.relpath(STORE, ROOT),
        "declared_formula": "sum_buy(bval) + sum_sell(sval)  [marketdetectors broker_summary]",
        "comparison_target": "stockbit_flow.net_value  [order-trade/trade-book/chart]",
        "corpus": {"rows": n_rows, "sessions": len(sessions)},
        "classes": {k: classes[k] for k in sorted(classes)},
        "evaluable_share": round(evaluable_share, 6),
        "comparison": {"matched": matched, "mismatched": mismatched,
                       "no_target": no_target, "match_rate": round(match_rate, 6)},
        "zero_sum": {"evaluable_cells_equal_zero": zero_valued,
                     "share_of_evaluable": round(zero_share, 6)},
        "thresholds": {"tolerance": TOLERANCE, "match_rate_min": MATCH_THRESHOLD,
                       "evaluable_share_min": EVALUABLE_SHARE_MIN},
        "mismatch_examples": sorted(examples, key=lambda e: (e["session"], e["ticker"])),
        "verdict": "PASS" if not failures else "FAIL",
        "failures": failures,
    }

    # G-7 requires an independent checker to reproduce this report byte-for-byte.
    # `generated_utc` is wall-clock and would defeat that, so the digest covers
    # the CONTENT only, with the timestamp held outside the hashed payload.
    content = {k: v for k, v in report.items() if k != "generated_utc"}
    canonical = json.dumps(content, indent=1, sort_keys=True, ensure_ascii=False).encode()
    digest = hashlib.sha256(canonical).hexdigest()
    report["content_sha256"] = digest

    os.makedirs(a.out_dir, exist_ok=True)
    path = os.path.join(a.out_dir, "mapping_validation_report.json")
    with open(path, "wb") as f:
        f.write(json.dumps(report, indent=1, sort_keys=True, ensure_ascii=False).encode())
    with open(path + ".sha256", "w") as f:
        f.write(f"{digest}  mapping_validation_report.json (content only; "
                f"generated_utc excluded so the report is byte-reproducible)\n")

    print(f"corpus {n_rows} rows / {len(sessions)} sessions")
    print(f"classes: {dict(sorted(classes.items()))}")
    print(f"EVALUABLE share {evaluable_share:.2%}   match rate {match_rate:.4%} "
          f"({matched} matched / {mismatched} mismatched / {no_target} no-target)")
    print(f"formula evaluates to exactly 0 on {zero_valued} of {evaluable} EVALUABLE cells "
          f"({zero_share:.2%})")
    print(f"\nVERDICT: {report['verdict']}")
    for f_ in failures:
        print(f"  FAIL: {f_}")
    print(f"\nreport: {os.path.relpath(path, ROOT)}\nsha256: {digest}")
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
