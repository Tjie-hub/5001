# HANDOFF_G1 — exit & position-management practice study: G1 executed (the single run)

**Date:** 2026-10-06 · **Branch:** `research/exit-study-2026-10` · **Base:** G0-ter freeze
`c483886c380377c9b4d8ab196c4306e28f09a141` · **Gate:** owner approval of G0-ter, 2026-10-06
(`EXIT_STUDY_G1_APPROVED=1`). **G1 ran exactly once. There are no re-runs.**

## 1. What ran

```bash
cd <worktree>/docs/research_programs/P-M/exit_study
DB_PATH="<abs>/data/walkforward.db" \
EXIT_STUDY_HIST_PKL="<abs>/docs/research_programs/P-M/forward_volex/remeasure/work/hist_pre2021.pkl" \
EXIT_STUDY_SPLITS_PKL="<abs>/docs/research_programs/P-M/data_gaps/data/split_hist.pkl" \
EXIT_STUDY_G1_APPROVED=1 <venv>/bin/python g1_run.py
```

- `g1_run.py` re-verified the sidecar (all three OK) before doing anything, rebuilt the owner
  universe mask and indicator set exactly as `census_g0()` does, and called the frozen
  `evaluate()`. It introduces no settings of its own.
- Data access read-only throughout (PKLs + `mode=ro` DB for the fingerprint).
- **Runtime 156.9 s.** Result: `RESULT_20261006T142027Z.json` (2026-10-06 14:20:27 UTC).
- Cross-checks at run time: populations E-SN 3,682 / E-RND 3,682 / E-BRK 5,141 — **exactly the
  G0-ter census counts**; dataset fingerprint `f42275e3…` **identical to the census run's**
  (zero drift between census and G1).

## 2. Outcome (see VERDICT.md / PRACTICE_NOTE.md)

**P4 (swing lot) is the only arm RECOMMENDED** (both eras t +4.26/+3.25 on E-SN; also
+3.23/+3.46 on E-RND). All other non-baseline arms: NO_RELIABLE_DIFFERENCE; none harmful.
Averaging down (P2): not adopted. The owner's X1 plan: no reliable difference vs a 20-session
hold — keep the stop for ruin control, not return. Full tables: VERDICT.md (rendered
mechanically by `gen_verdict.py`); raw numbers: the RESULT.

## 3. Disclosures carried in VERDICT.md

1. **Known parity residue (~5%), no re-freeze** (planner, 2026-10-06): 58/61 real setups
   identical vs the live jurnal26 code; 3 differ — FIMP 2022-10-06, EMTK 2025-01-15,
   TBLA 2023-07-25 (group-mean/level rounding or the 5-bar window edge).
2. **Post-run mechanical repair of the RESULT file:** the runner's JSON sanitizer missed
   plain-Python ints → 1,529 digit-string values converted back to int (values only, keys
   untouched, zero recomputation). The run itself is untouched and unique.
3. X0/X2 equal-risk portfolios go bust (negative equity) — their CAGR/max-DD columns are
   meaningless and dd_ok comparisons involving them are void (VERDICT §Reading notes).
4. P-arms share X1's portfolio numbers exactly (single-exit approximation); per-trade paired
   tests are the discriminator for position arms.
5. Benign runtime warnings (All-NaN TR slice on pre-listing stubs; CAGR scalar-power on
   negative curves) — frozen code, documented.

## 4. Files in the G1 commit

`RESULT_20261006T142027Z.json` · `VERDICT.md` · `PRACTICE_NOTE.md` · this handoff ·
`g1_run.py` · `gen_verdict.py` (provenance: the exact orchestration and the table renderer).
The three frozen artifacts and the sidecar are **unchanged** by G1 (verified at commit).

## 5. Governance

- Practice study: no registry, family-slot, or DECISION_LOG edits (the owner files a short
  D-entry only if they adopt P4 or anything else from PRACTICE_NOTE.md).
- `~/jurnal26` untouched (read-only reference only); production untouched; no service
  restarts; `research/ml-rank-2026-10`, `research/broad-search-v2-zcode` untouched; no
  secrets printed.
- **G1 is terminal for this study.** Any further run on this design would be a new,
  separately-approved exercise.
