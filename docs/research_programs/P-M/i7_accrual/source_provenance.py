#!/usr/bin/env python3
"""Source-state provenance fingerprint for the v004 freeze (R7 remediation).

The v004 manifest records `source_production_db` as a PATH ONLY. The source is
a live 13.7 GB database under continuous cron writes, so the frozen artifact is
not reproducible from the manifest alone. Hashing 13.7 GB is not part of the
established workflow and would not help anyway: the file changes every day.

This records the strongest fingerprint obtainable WITHOUT touching the source:

  * file size + mtime                       -- NOT a content hash
  * schema fingerprint                      -- sha256 over sqlite_master SQL
                                               for the two source tables ONLY
  * per-table min/max trade_date            -- index-served
  * stockbit_flow row count                 -- small table, exact
  * SOURCE-AGREEMENT SPOT CHECK             -- the load-bearing one: for a
                                               deterministic sample of frozen
                                               admitted cells, recompute the
                                               bar count from production and
                                               compare it to the frozen ledger

The spot check is what actually speaks to reproducibility: it demonstrates the
source still agrees with the freeze for the sampled cells. Everything else is
context. Every field is labelled with its evidential strength; nothing here is
presented as a cryptographic content hash of the database.

STRICTLY READ-ONLY. `mode=ro` + `PRAGMA query_only`. Writes only its own
addendum artifact next to the freeze, and refuses to overwrite it.

  python3 source_provenance.py            # print
  python3 source_provenance.py --write    # emit the addendum artifact
"""
from __future__ import annotations

import argparse, datetime as _dt, hashlib, json, os, sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
PROD = os.path.join(REPO, "data", "walkforward.db")
STORE = os.path.join(HERE, "store")
V004 = os.path.join(STORE, "I7_V004_ADMISSIBLE_v1.sqlite")
OUT = os.path.join(STORE, "I7_V004_SOURCE_PROVENANCE_v1.json")

SAMPLE_N = 200          # deterministic, evenly spaced across the cohort


def ro(p):
    c = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
    c.execute("PRAGMA query_only = ON;")
    return c


def build():
    st = os.stat(PROD)
    src = ro(PROD)
    frz = ro(V004)

    schema = src.execute(
        "SELECT name, sql FROM sqlite_master WHERE type='table' "
        "AND name IN ('stockbit_flow','stockbit_flow_bars') ORDER BY name"
    ).fetchall()
    schema_fp = hashlib.sha256(
        json.dumps(schema, sort_keys=True).encode()).hexdigest()

    flow_min, flow_max, flow_rows = src.execute(
        "SELECT MIN(trade_date), MAX(trade_date), COUNT(*) FROM stockbit_flow "
        "WHERE trade_date != ''").fetchone()
    bars_min = src.execute("SELECT trade_date FROM stockbit_flow_bars "
                           "ORDER BY trade_date ASC LIMIT 1").fetchone()[0]
    bars_max = src.execute("SELECT trade_date FROM stockbit_flow_bars "
                           "ORDER BY trade_date DESC LIMIT 1").fetchone()[0]

    cells = frz.execute(
        "SELECT ticker, session_date, n_bars FROM admissibility_ledger "
        "WHERE admissible=1 ORDER BY ticker, session_date").fetchall()
    step = max(1, len(cells) // SAMPLE_N)
    sample = cells[::step][:SAMPLE_N]

    agree, disagree = 0, []
    for tk, sd, nb in sample:
        # PK-prefix range scan (ticker, trade_date, bar_time) -- covering
        live = src.execute("SELECT COUNT(*) FROM stockbit_flow_bars "
                           "WHERE ticker=? AND trade_date=?", (tk, sd)).fetchone()[0]
        if live == nb:
            agree += 1
        else:
            disagree.append({"ticker": tk, "session": sd,
                             "frozen_n_bars": nb, "live_n_bars": live})
    src.close(); frz.close()

    return {
        "artifact": "I7_V004_SOURCE_PROVENANCE",
        "version": "v1",
        "purpose": "records the v004 source-state dependency explicitly "
                   "(forensic audit reservation R7); NOT a content hash of the "
                   "source database",
        "describes_freeze": {
            "store": "I7_V004_ADMISSIBLE_v1.sqlite",
            "store_sha256": json.load(open(
                os.path.join(STORE, "I7_V004_MANIFEST.json")))["store_sha256"],
        },
        "source_database": {
            "path": PROD,
            "evidential_strength": "WEAK — mutable, live, continuously written "
                                   "by production cron. Size and mtime are "
                                   "NOT content hashes and do not pin state.",
            "byte_size": st.st_size,
            "mtime_utc": _dt.datetime.fromtimestamp(
                st.st_mtime, _dt.timezone.utc).isoformat(),
            "content_hash": None,
            "content_hash_note": "deliberately not computed: 13.7 GB, live, "
                                 "and changes daily — a hash would be stale "
                                 "before it could be used",
        },
        "schema_fingerprint": {
            "evidential_strength": "STRONG for schema, silent on content",
            "tables": [n for n, _ in schema],
            "sha256_over_sqlite_master_sql": schema_fp,
        },
        "source_extents_at_check_time": {
            "evidential_strength": "MODERATE — pins the observed span, not the "
                                   "values inside it",
            "stockbit_flow": {"min_trade_date": flow_min,
                              "max_trade_date": flow_max,
                              "rows": flow_rows},
            "stockbit_flow_bars": {"min_trade_date": bars_min,
                                   "max_trade_date": bars_max,
                                   "rows": "not counted — ~98M rows, no "
                                           "covering index for a windowed count"},
        },
        "source_agreement_spot_check": {
            "evidential_strength": "STRONGEST AVAILABLE — directly compares "
                                   "frozen content against live source",
            "method": "deterministic evenly-spaced sample of frozen ADMITTED "
                      "cells; recompute bar count from production via the "
                      "primary-key range scan and compare to the frozen ledger",
            "sample_size": len(sample),
            "cells_agreeing": agree,
            "cells_disagreeing": len(disagree),
            "disagreements": disagree,
        },
        "reproducibility_statement": (
            "v004 CANNOT be reproduced byte-for-byte from the recorded inputs: "
            "its source is mutable and unhashed, and the builder stamps "
            "built_utc. It CAN be re-derived in content for any cell whose "
            "source rows are unchanged, which the spot check evidences for the "
            "sampled cells. This is a known, declared limitation, not a defect "
            "introduced by the v004 correction — it is inherent to accruing "
            "from a live vendor-fed table, and is the gap the prospective "
            "capture service closes for future sessions."),
        "checked_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    doc = build()
    s = doc["source_agreement_spot_check"]
    print("=== v004 SOURCE PROVENANCE ===")
    print(f"  source size/mtime : {doc['source_database']['byte_size']:,} / "
          f"{doc['source_database']['mtime_utc']}  (NOT a content hash)")
    print(f"  schema fingerprint: {doc['schema_fingerprint']['sha256_over_sqlite_master_sql'][:32]}…")
    print(f"  spot check        : {s['cells_agreeing']}/{s['sample_size']} cells agree "
          f"with live source; {s['cells_disagreeing']} disagree")
    if s["disagreements"]:
        print(f"    {json.dumps(s['disagreements'][:5])}")
    if not a.write:
        print("\nDRY RUN — pass --write to emit the addendum artifact.")
        return 0 if not s["disagreements"] else 1
    if os.path.exists(OUT):
        print(f"\nREFUSING: {OUT} exists; addenda are immutable.")
        return 2
    with open(OUT, "w") as f:
        json.dump(doc, f, indent=1, sort_keys=True)
        f.write("\n")
    with open(OUT + ".sha256", "w") as f:
        f.write(hashlib.sha256(open(OUT, "rb").read()).hexdigest() + "\n")
    os.chmod(OUT, 0o444)
    print(f"\nWROTE {OUT}")
    return 0 if not s["disagreements"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
