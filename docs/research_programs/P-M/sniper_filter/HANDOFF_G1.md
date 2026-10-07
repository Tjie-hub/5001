# HANDOFF_G1 — sniper setup filter (HYP-PM-0016 draft): G1 executed (the single run)

**Date:** 2026-10-07 · **Branch:** `research/sniper-filter-2026-10` @ Revision 2 (`d261260`) ·
**Gate:** owner approval of Revision 2 (`SNIPER_FILTER_G1_APPROVED=1`). **The run executed
exactly once. Any fix after this run is a new, disclosed, re-frozen run.**

## 1. What ran

```bash
cd <worktree>/docs/research_programs/P-M/sniper_filter
DB_PATH="<abs>/data/walkforward.db" \
EXIT_STUDY_HIST_PKL="<abs>/docs/research_programs/P-M/forward_volex/remeasure/work/hist_pre2021.pkl" \
EXIT_STUDY_SPLITS_PKL="<abs>/docs/research_programs/P-M/data_gaps/data/split_hist.pkl" \
SNIPER_FILTER_G1_APPROVED=1 <venv>/bin/python g1_run.py
```

- Freeze sidecar verified first (all five files OK), then the **R6 snapshot gate**:
  `/home/tjiesar/scratch/sniper_filter_g1/walkforward_snapshot_2026-10-07.db` sha256
  `c42c151e…` OK and dataset fingerprint **`f42275e3…` = G1FIX exactly** — both verified
  BEFORE any outcome was computed.
- Data access read-only throughout (PKLs + the frozen snapshot). Runtime **200.2 s**.
- Result: `RESULT_20261007T090305Z.json` — populations 3,682 fills (val 934 / test 1,429),
  M1 validation choice = **M1b** (C=10; val means M1a −0.0161 / M1b +0.0019), PBO **0.461**
  (48 months used, 8 dropped, 16 splits), selection tiers per config 2,358 window / 4 all-known
  / 1,320 unselected / 1,319 unscored, and the computed pass flags copied into `VERDICT.md`.

## 2. Outcome

**NULL — no configuration passes** (all fail conditions 1–3; M1b and M2 satisfy condition 4 and
everything satisfies condition 5, which changes nothing). The best monthly-difference NW t is
+0.23 vs the frozen primary bar **3.2931**; no configuration's selected setups have positive
mean R on test. The pre-registered honest prior ("a NULL, or skip-the-volatile-names") resolves
to the NULL branch; notably the M0 baseline (low-vol + momentum) was the WORST test performer,
so the HYP-PM-0015 lesson did not transfer to this entry. **No forward test is built** (§8
builds one only for a passing model). Full tables and flags: `VERDICT.md` (copied from the
RESULT, not re-judged); raw numbers: the RESULT.

## 3. Governance

- Practice-style registration in {L1} (D-067); per the predeclared null handling the owner files
  HYP-PM-0016 → FAILED and the census arithmetic (ratification draft @ 2937488). This study
  edited no registry and no DECISION_LOG.
- `~/jurnal26` untouched (the forward-test path stayed dormant — nothing passed); production,
  crontab, service, `logs/TELEGRAM_OFF` untouched; read-only data; no secrets printed.
- The exit study's frozen files were called, never modified; sidecars verified before and after.
- **STOP. Further work on this design = a new, separately-approved, re-frozen exercise.**

*— ZCode, 2026-10-07*
