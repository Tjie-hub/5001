# HANDOFF G1: retail ownership (KSEI) {OC} (2026-10-09)

- **Run:** `OC_G1_APPROVED=1 g1_run.py` was executed exactly once (2 min 20 s) and wrote
  `RESULT_20261009T075700Z.json`.
  - Before the run: sidecar `sha256sum -c` OK, snapshot and KSEI hashes re-verified in-run, census N
    611 matched.
- **Verdict:** both arms FAIL on every frozen condition. **FAILED (F2)**, a determinate NULL; see
  VERDICT.md.
- **To file (on owner "file it"):**
  - D-085: G1 NULL, FAILED F2.
  - FAILURE_REGISTRY: FAIL-PM-0020.
  - HYPOTHESIS_REGISTRY: HYP-PM-0020 → FAILED.
  - {OC} family row: 1 member, FAILED.
- **No fixes or re-runs.** Any variant (another denominator, horizon or universe) is a new registration
  under a new D-entry.
- **Data left in place for reuse:** `~/idx_external/ksei/` (211 months). This NULL is now a known prior
  for anything built on KSEI ownership.
