# HANDOFF G0: retail ownership (KSEI) {OC} (2026-10-09)

**State:** G0 frozen, no outcome read. **STOPPED** for owner approval of G1.

## Provenance

| Item | Value |
|---|---|
| Branch / base | `research/retail-ownership-2026-10` from hardening `a8d6a20` (D-081/D-082); D-083 is filed in the main checkout |
| history_long snapshot | `~/scratch/g0_snapshots_2026-10-08/history_long_snapshot_2026-10-08.db`, sha256 `7d298068…5714` (verified) |
| walkforward snapshot | `…/walkforward_snapshot_2026-10-08.db`, sha256 `a2d7e675…bc47` (verified) |
| KSEI | 211 zips, manifest `ae06e4a2…9a43`; CSV `~/idx_external/ksei/ksei_equity_holdings.csv` `38c8a90b…f781` |
| Cost model | `cost_realised.py`, a verbatim copy of `3bacdcc`, sha256 `65051253…0b7a` (D-082) |
| Regular-volume cache | `~/scratch/retail_ownership_regvol_2026-10-08.json`, derived from the walkforward snapshot and keyed by its sha256 |

## Census (CENSUS_G0.json)

- **Formations:**
  - 210 in total, 209 testable (2009-04-07 → 2026-08-07); halves 105 / 104.
  - 4 formations were delayed by a late zip stamp, so all stamps now precede their formation.
- **Universe:** median 150 names, min 61, max 503.
  - Yearly medians run from 75 (2009) to 401 (2026). It is thinner before 2017.
  - Drops: 45,621 no bar, 51,461 ADV, 756 price, 3,721 history.
- **Denominator:**

  | Measure | Median | p90 |
  |---|---|---|
  | s, custodied | 0.157 | 0.604 |
  | s, listed | 0.087 | 0.378 |

  - Spearman 0.856 between them.
  - Custody ratio median 0.84, p10 0.21.
  - Foreign individuals are negligible (median 0.08%).
- **Volume basis:** 40,698 post-break bars use regular volume; 5,652 keep consolidated volume where
  there are no minute bars.
- **Power:** random-sort σ 5.876% (64 pre-sample months), so MDE ≈ **1.68% a month** at bar 3.2987,
  N = 611.

## Tests

`test_pit_ownership.py`: **7 passed**. The G1 gate refuses without `OC_G1_APPROVED=1` (verified).

## G1 runtime estimate

About 3 minutes to build the panel (the census took 151 s), plus the arm loops. Under 10 minutes in
total.

## What the owner approves at G1

1. File D-084 (registration, N = 611), which adds HYP-PM-0020 to the registry.
2. Run `OC_G1_APPROVED=1 venv/bin/python docs/research_programs/P-M/retail_ownership/g1_run.py` once.
3. Write the VERDICT from the computed booleans only.
