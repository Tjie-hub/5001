# HANDOFF G0: online-retail broker imbalance {RF} (2026-10-09)

**State: STOP RULE FIRED. No G1, and no outcome read.**
- Power is 3.1% to detect 0.30% a week; the MDE is 0.86% a week. Both are computed only from
  pre-sample (2023–2024) random sorts on the same 98 names.

**Provenance:**
- Snapshots: walkforward `a2d7e675…` and history_long `7d298068…`, both verified in-run.
- Verbatim module copies:
  - `ownership.py` 856afe18… (b7f84ac)
  - `cost_realised.py` 65051253… (3bacdcc)

**Tests:** `test_pit_flow.py` 4 passed. With the boundary, fence and DB-centralisation tests,
14 passed.

**Census:**
- 98 names; 76 testable weeks (38 / 38 between the halves).
- Median universe 91 names, 18 per quintile.
- R-broker presence 99.3%.
- RI correlates −0.37 with foreign imbalance and −0.36 with the formation-week return.
- Data gap: week 2026-07-24 has 0 price bars in `history_long`.

**Recommendation:** option (a), WITHDRAWN (uncounted).
- Rebuild the G0 on the breadth panel when `~/idx_external/broker_flow` completes (nightly, about a
  week).
- The breadth backfill data is read-only, so the new G0 pins its files by sha256.
