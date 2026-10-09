# HANDOFF G0: daily OIB continuation (2026-10-09)

**State:** G0 frozen, no outcome read, stop rule NOT fired. **STOPPED** for owner approval of G1.

## Census and power

| Item | Value |
|---|---|
| Testable days | 384 (2025-01-02 → 2026-09-23), halves 230 / 154 |
| Universe | median 377 names, 75 per quintile |
| Tradeable 5-day blocks | 76 spreads |
| Power | MDE 0.118% a day; power 57.8% at 0.10% a day (bar 3.2991, N = 612) |

## Provenance

- Snapshots: walkforward `a2d7e675…` and history_long `7d298068…` (prices end 2026-09-24).
- Daily-totals cache `73a06abf…`, built by `extract_daily.py` in 12.5 minutes.

## Tests

- `test_pit_oib.py`: 4 passed. With the boundary, fence and DB-centralisation tests, 14 passed.
- The G1 gate refuses without `OIB_G1_APPROVED=1`, and also refuses if the stop rule fired.

## At owner approval

1. File the D-entry registering **HYP-PM-0021**, the next free id, in P-M {I5,I6,I7,I12} at
   N = 612, bar 3.2991. Add its HYPOTHESIS_REGISTRY row.
2. `OIB_G1_APPROVED=1 venv/bin/python docs/research_programs/P-M/oib/g1_run.py`, run once (an
   estimated 5–10 minutes).
3. The VERDICT comes from the computed booleans only.

## Flagged separately

HYP-PM-0001's instrument used cumulative counters as 1-minute OFI. The owner decides whether a
superseding D-entry re-classifies FAIL-PM-0001.
