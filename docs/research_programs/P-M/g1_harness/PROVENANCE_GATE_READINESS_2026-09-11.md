# PROVENANCE GATE READINESS — 2026-09-11

**Task:** implement the immutable execution provenance wrapper (D-048 / governance closeout §E3), make it a mandatory C7 execution gate, test it mechanically, and prepare the commit. **No empirical execution of any kind occurred.** No methodology, registration, family-assignment, G1-classification, or Dataset B change.

---

## Verdict: **READY** — provenance hard gate implemented, tested (8/8 + 16/16 + 7/7), wired into both execution paths, fail-closed on every specified condition. Commit list prepared (not committed — awaiting Owner authorization).

## A. Provenance design implemented

`g1_harness/provenance.py` — two functions, one exception:

- **`snapshot_run(...)` → (run_id, run_dir, manifest)** — called BEFORE any data access. Creates `runs/<run_id>/` exclusively (pre-existing directory aborts) and writes `preflight_manifest.json` containing:
  - **executed Python sources**: every imported module under the program directories, hashed with a **double pass** — a file that changes between passes raises `ProvenanceRefused` (ambiguous state);
  - **config**: path + sha256;
  - **registration/spec**: `G1_REGISTRATION_v1_2026-09-11.md` (G1) / `C7_REGISTRATION_v1_2026-09-11.md` (C7), hashed;
  - **Dataset B freeze manifest**: hashed, **and its pinned store sha256 cross-checked against the actual store binary** — mismatch aborts (input/store fingerprint change);
  - **run ID**: `RUN-<UTC timestamp>-<preflight_digest[:12]>`, digest = sha256 over the canonical hash material (source hashes keyed by basename — stable across directory moves);
  - **git commit/state**: HEAD commit, dirty flag, dirty-line count (absent/broken git is recorded, never hidden — the file hashes remain the binding identity);
  - **gates** and label.
- **`seal_run(...)`** — called AFTER execution. Re-hashes sources, config, registrations, and the store binary; any drift stamps the run `INVALID_PROVENANCE` (output retained, marked non-reportable) and records `drifted_files`; hashes all outputs into `seal.json`.
- **`ProvenanceRefused`** — the fail-closed exception: missing files, store-pin mismatch, ambiguous sources, pre-existing run directory.

## B. Hard-gate behavior (wired into BOTH execution paths)

| Path | Gates before data access | Provenance behavior |
|---|---|---|
| `python3 g1_harness.py` (G1, real) | all four governance gates (`check_gates`) → **then** `snapshot_run` → `load_real_bundle` (internal re-check) | snapshot → run → outputs written into `runs/<run_id>/g1_real_output.json` → `seal_run` |
| `python3 g1_harness.py c7` (C7, real) | `c7_registered` **(unchanged, not weakened)** → **then** `snapshot_run` (registration = C7_REGISTRATION_v1) → `load_real_bundle(required_gates={"dataset_b_frozen"})` (internal re-check) | snapshot → run → `runs/<run_id>/c7_real_output.json` → `seal_run` |

- `load_real_bundle` was generalized to take an explicit `required_gates` set (G1: all four; C7: only the data gate it depends on). Fail-closed re-check retained inside the function.
- Fail-closed conditions implemented and tested: source change after preflight (double-pass + post-run seal), config change, registration change, store/freeze-manifest fingerprint change, missing governance/registration file, ambiguous source state, pre-existing run directory.
- The `c7_registered` gate is **not weakened** — it remains the first refusal check, and the provenance gate is **additional**.

## C. Mechanical tests (all pass)

| Suite | Result |
|---|---|
| `test_provenance_gate.py` | **8/8** — snapshot success + contents; preflight-digest determinism across directories; source/config/registration drift → seal INVALID; store tamper → preflight refusal; missing registration → refusal; double-pass ambiguity → refusal; immutable run directory |
| `test_g1_harness.py` | **16/16** — unchanged G1 machinery incl. foundation parity, leakage traps, determinism |
| `test_c7_registration.py` | **7/7** — intensity/threshold/boundary, ADV20 shift(1), freq-poison identity, k-set/primary, exclusions, fail-closed |

No real Dataset B empirical computation occurs in any test (synthetic/temp fixtures only; the wrapper is exercised on dummy files in temp directories).

## D. Exact commit candidate (prepared — NOT committed)

Untracked today: `docs/research_programs/P-M/g1_harness/` (entire) and `docs/research_programs/P-M/dataset_b/` (entire).

**Commit — include (34 files g1_harness + 14 files dataset_b):**

```
docs/research_programs/P-M/g1_harness/
  g1_harness.py  g1_synthetic.py  provenance.py  freq_probe.py  nf_validate.py
  g1_config.json  test_g1_harness.py  test_c7_registration.py  test_provenance_gate.py
  g1_dry_run_output.json  g1_real_output.json
  G1_REAL_OUTPUT_RUN1_2026-09-11.json  G1_RUN_MANIFEST_RUN1_2026-09-11.json
  G1_REGISTRATION_v1_2026-09-11.md  C7_REGISTRATION_v1_2026-09-11.md
  G1_MECHANICAL_READINESS_2026-09-10.md  G1_PREEXECUTION_SEMANTICS_AUDIT_2026-09-10.md
  G1_AUTHORITATIVE_PREREG_RETRIEVAL_2026-09-11.md  G1_FREEZE_READINESS_2026-09-11.md
  G1_GOVERNANCE_UNBLOCK_RECORD_2026-09-11.md  G1_POSTMORTEM_FAMILY_TRIAGE_2026-09-11.md
  G1_FINAL_GOVERNANCE_STATUS_2026-09-11.md  G1_EXECUTION_REPORT_2026-09-11.md
  G1_FINAL_EXECUTION_REPORT_2026-09-11.md  G1_GOVERNANCE_CLOSEOUT_2026-09-11.md
  G1_FREEZE_CANDIDATE_STORE_MANIFEST_2026-09-11.json
  G1_OWNER_DECISION_PACKET_2026-09-11.md
  OWNER_DECISION_PACKET_FAMILY_ASSIGNMENT_2026-09-11.md
  FAMILY_DECISION_IMPLEMENTATION_2026-09-11.md
  CLAUDE_G1_FORENSIC_AUDIT_2026-09-11.md        (external reviewer record — include, authorship noted)
  CLAUDE_INDEPENDENT_REVIEW_G1_C7_2026-09-11.md (external reviewer record — include, authorship noted)
docs/research_programs/P-M/dataset_b/
  foundation.py  validate.py  fingerprint.py  fingerprint_v2.py
  build_calendar_and_roster.py  backfill_broker_flow.py  gap_classifier.py
  investigate_outside_band.py
  DATASET_B_FOUNDATION_CLOSURE_REPORT_2026-09-10.md
  DATASET_B_FINAL_RECONCILIATION_2026-09-11.md
  DATASET_B_BROKERFLOW_BACKFILL_REPORT_2026-09-11.md
  artifacts/  (21 files: roster/calendar v1+v2 + sidecars, FINGERPRINT v1+v2 + sidecar,
               SEMANTIC_REGISTER, VALIDATION_REPORT, GAP_CLASSIFICATION,
               OUTSIDE_BAND_INVESTIGATION, CAPTURE_COMPLETENESS + sidecar,
               FREEZE_MANIFEST_v1 + sidecar)
  store/run_backfill_supervised.sh  store/logs/
docs/roadmap/DECISION_LOG.md                       (modified — §2i/D-048)
docs/research_programs/HYPOTHESIS_REGISTRY.md      (modified — C-family rows)
docs/research_programs/FAILURE_REGISTRY.md         (modified — G1 outcome rows)
```

**Exclude (with reason):**

| Path | Reason |
|---|---|
| `dataset_b/store/DATASET_B_BROKER_FLOW_STORE_v1.sqlite` (264 MB) | hash-pinned by the freeze manifest (`21661f03…`); binary-in-git is an Owner policy decision; the file persists on the Syncthing-synced working tree |
| `store/*.sqlite-shm`, `*.sqlite-wal` | transient SQLite sidecars (WAL = 0 bytes) |
| `store/logs/` (empty backfill log) | zero-content |
| `**/__pycache__/` | generated |
| `g1_harness/runs/` (future) | created at execution time; each run directory is self-contained and committed per-run afterwards |

**Ambiguous / owner-attention:** none unsafe. Notes: (i) `CLAUDE_*.md` reviews are external-authorship records — included for the evidentiary trail; (ii) `g1_real_output.json` duplicates `G1_REAL_OUTPUT_RUN1_2026-09-11.json` byte-for-byte — both committed for path-stability with older reports.

**Proposed commit message:**

```
feat(P-M): Dataset B freeze + G1 Run 1 closeout; register C-family {C2,C3,C7} and C7; provenance hard gate

- Dataset B FROZEN: store 21661f03…, FINGERPRINT_v2 1a68ab1c…, freeze manifest v1 (30,880 cells)
- G1 Run 1 (C-family, per D-048): C2 governance-INVALID, C3 NOT CONFIRMED (valid bounded null),
  C1a/C1b WITHDRAWN — overall SPLIT / governance-invalidated
- C7 intensity-state REGISTERED (owner six decisions): 2.0 threshold, k∈{3,5,10} primary 5, freq-free
- provenance hard gate: preflight snapshot + post-run seal, fail-closed on drift (D-048)
- DECISION_LOG §2i/D-048; HYPOTHESIS_REGISTRY C-family rows; FAILURE_REGISTRY G1 outcome rows
- tests: provenance 8/8, C7 7/7, G1 16/16
```

## E. Remaining owner actions

1. **Authorize the commit** (list + message above) — until then nothing is committed.
2. **C7 execution authorization**: set `c7_registered=true`, then run `python3 g1_harness.py c7` — the provenance wrapper will snapshot, execute, and seal automatically.

## F. Explicit statement

**NO EMPIRICAL RUN PERFORMED.** C7 was not executed on real data; no forward returns were computed; the dry-run artifact and all G1 Run 1 artifacts are untouched; the G1 classifications, C7 registration parameters, family assignment, and Dataset B are unmodified. The wrapper is provenance infrastructure only.
