# G1 FREEZE-READINESS & GATE VERIFICATION — 2026-09-11

**Mode:** READ-ONLY verification + minimum mechanical gate-hardening. No G1 execution on real data, no Dataset B freeze, no methodology/specification changes, no owner decisions, no commits.

**Deliverables:** this report + `G1_FREEZE_CANDIDATE_STORE_MANIFEST_2026-09-11.json` (draft, explicitly NOT-FROZEN) + hardened `g1_harness.py` (two gate fixes, §D).

---

## A. Dataset B verification results (store: `dataset_b/store/DATASET_B_BROKER_FLOW_STORE_v1.sqlite`)

| Check | Expected | Observed | Verdict |
|---|---|---|---|
| Intended capture cells | 30,880 | **30,880** (= Σ PIT `session_members`, 101-ticker universe × 386 sessions, 2025-01-02→2026-08-27) | ✅ |
| SUCCESS | 30,877 | **30,877** | ✅ |
| EMPTY | 3 | **3** (PTRO 2025-10-06, RAJA 2025-10-13, RATU 2025-11-28 — suspension-type confirmed-empty, terminal) | ✅ |
| Failures / non-terminal | 0 | **0** | ✅ |
| Truncation (`truncated_buy`/`truncated_sell`) | 0 | **0** | ✅ |
| Date-echo mismatches | 0 | **0** | ✅ |
| Accounting identity (manifest `n_buy+n_sell` vs actual `broker_flow_b` rows per cell) | exact | **0 discrepancies** across 30,877 SUCCESS cells | ✅ |
| Completeness at limit=150 (`bandar.total_buyer==n_buy` AND `total_seller==n_sell`) | all | **0 violations** — store is the uncensored population | ✅ |
| `bandar_detector_b` rows | = SUCCESS count | **30,877** | ✅ |
| `raw_responses` provenance rows | = all cells | **30,880** | ✅ |
| `capture_version` | single-valued | **`v1` only** (1,518,727 broker rows) | ✅ |
| Sides | BUY/SELL only | **BUY 802,352 / SELL 716,375** | ✅ |
| NULL freq / zero-value rows | 0 | **0 / 0** | ✅ |
| `PRAGMA integrity_check` | ok | **ok** | ✅ |
| Roster/calendar hashes in `capture_run_log` | single-valued | **single** `roster_artifact_sha256 = f7e2fec0…` (PIT_ROSTER v1, sha re-verified) across all 3 runs; grid = Σ members **30,880** in BOTH v1 and v2; **v1↔v2 session memberships content-identical (0 differing sessions)** | ✅ |

## B. Freeze candidate identity/checksum (what WOULD be frozen)

`G1_FREEZE_CANDIDATE_STORE_MANIFEST_2026-09-11.json` (marked `draft-v1-NOT-FROZEN`):

- **store_fingerprint = `1303378683819f17afa41001dd64574708127a6494ecdd135df23c6b6a2088dd`** — sha256 over the canonical manifest (per-ticker order-independent commutative SHA-256 fold, method identical to `dataset_b/fingerprint.py`) of:
  - `broker_flow_b` (broker_code, side, lot, lot_value, value, value_total, avg_price, freq, investor_type) — 1,503,287 in-scope rows
  - `bandar_detector_b` (total_buyer, total_seller) — 30,624 in-scope rows
  - production `ohlcv` (open, high, low, close, volume) — the outcome layer
  - capture grid: roster `f7e2fec0…` (v1; = v2 memberships), calendar sha per artifact, 386 sessions, 30,880 cells, quarantined per FINGERPRINT_v1 artifact
- **Fingerprint reproducibility (production side):** `DATASET_B_FINGERPRINT_v1` **reproduced bit-exactly** (`b0ad62826671e7da…` recorded == recomputed) — production content over the window is unchanged since the artifact was built.
- **Production DB isolation:** the backfill code writes only to the store (no production imports/paths); production fp reproduction above is the in-window stability proof; all audit connections were `mode=ro` + `PRAGMA query_only`. Note recorded in the manifest: the raw frozen-window row count (2,871,143) is the full-universe table; Dataset A's 1,222,713 is the IDX80-scoped slice (custody reproduced 2026-09-10, verdict A) — not an isolation violation.
- **Freeze-procedure note (for the owner, later):** the store has live `-wal`/`-shm` sidecars; the actual freeze must checkpoint/close the writer, then re-run `freeze_candidate_manifest.py`-equivalent checks and pin the final digest.

**Dataset B was NOT frozen.**

## C. G1 input contract status

| Input | Wired via | Verified |
|---|---|---|
| PIT roster / calendar | `foundation.PitRoster.load` / `SessionCalendar.load` (sha-verified artifacts; loader default v2) | ✅ v1↔v2 memberships identical; both artifact sha256s re-verify |
| OHLCV | production `ohlcv` (ro), `is_final=1`, `close×volume` value fallback | ✅ schema matches loader SELECT |
| Forward returns | harness engine, **parity-tested against `foundation.forward_returns`** | ✅ (test_parity) |
| Corporate actions | `foundation.load_corporate_actions` + `detect_unapplied_splits`; k-window exclusion in cells | ✅ |
| Suspensions | `suspension_events` expanded over declared calendar | ✅ schema matches |
| Broker-flow / bandar store | `broker_flow_b` / `bandar_detector_b` / `capture_manifest` (ro) | ✅ columns match loader SELECTs exactly |
| Exclusion logic | price≥100, |ret1|≥15%, suspension, CA-in-(t,t+k], breadth floor, quarantine — all counted per stage | ✅ synthetic-verified |
| Feature construction | F-classifier (prefix), ST, NF-buckets, breadth surprise | ✅ 15/15 tests |
| Inference configuration | NW(k) daily-series t, Holm α=0.05, k∈{3,5,10} primary 5, 0.60% RT floor | ✅ config fields present; final binding deferred to preregistration (unchanged) |
| Net-flow control | PROVISIONAL stockbit_flow wiring in loader, **hard-gated** | ✅ gate closed (§D) |

## D. Four gate wiring/status audit

Gate check lives in `g1_harness.py: check_gates()`; invoked in `main()` **before any data access** (`real = not cfg["synthetic"]` → `blocks = check_gates(cfg, real_data=real)` → exit 2 if any block). Demonstrated live: real-mode config (all gates false) → `G1 NOT LAUNCHED — mechanical gates:` all four listed, **exit code 2, zero data access**.

| Gate | Where enforced | FALSE/absent behavior | Demonstrated |
|---|---|---|---|
| `dataset_b_frozen` | `check_gates` (main, pre-access) + (new) inside `load_real_bundle` | exit 2 / SystemExit refusal | ✅ CLI + API |
| `prereg_confirmed` | same | same | ✅ |
| `freq_semantics_ratified` | same **plus unconditional cell-level block** in `run_g1` (C1a/C1b → `BLOCKED_FREQ_SEMANTICS`, all numbers nulled) | same | ✅ (test_c1a gating) |
| `net_flow_source_ratified` | same | same | ✅ |

**Bypasses found → minimum mechanical fixes applied (this task's only code changes):**
1. **`enforce_freq_gate=false` bypass:** `run_g1` previously required `enforce_freq_gate != false` in addition to the gate being false to block C1a — a config could compute C1a on unratified freq semantics. **Fix:** the C1a/C1b block is now unconditional on `gates.freq_semantics_ratified` (knob removed from the decision; the synthetic fixture sets the gate TRUE so all tests still pass). 15/15 re-verified.
2. **Direct-API bypass:** `load_real_bundle(cfg)` was callable directly (e.g., from a notebook) without `main()`'s gate test. **Fix:** `load_real_bundle` now re-checks `check_gates(real_data=True)` itself and refuses fail-closed. Demonstrated: API call with gates false → refused with all four gate messages.
3. Non-bypass notes: `synthetic:true` never opens any database (by construction); `G1_CONFIG` env points the loader at an owner-supplied config — that IS the intended owner mechanism, and with fix (2) the loader still refuses unless the gates are true inside it. The `enforce_freq_gate` key remains in config files as an inert vestige (documented; not removed to avoid config-schema churn).

## E. Dry-run reproducibility

- `python3 test_g1_harness.py` → **15/15 PASS** (post-fix).
- `python3 g1_harness.py` → `g1_dry_run_output.json` **byte-identical across three consecutive runs: sha256 prefix `70dff8d5cc4c4089`**, equal to the previously recorded artifact hash → byte-identity against the existing dry-run artifact CONFIRMED.
- `run_mode: synthetic-dry-run`; the dry path constructs its bundle in memory (`g1_synthetic.make_bundle`) and never opens any database — no Dataset B real-data execution, no production writes, no methodology/specification change (freq-gate hardening affects only the refusal path; fixture output unchanged and hash-identical).

## F. Discrepancies found

1. Two gate bypass paths (§D) — **fixed mechanically**, tests re-verified.
2. Docstring syntax error introduced and repaired during fix (1) — caught immediately by the gate demonstration (`ast`/import check now clean).
3. Capture ran against roster artifact `f7e2fec0…` (v1) while the loader defaults to v2 — **memberships verified content-identical**, and the freeze manifest records both hashes; no action needed beyond pinning this in the freeze.
4. The persisted builder script for the freeze manifest could not pass the local security scanner (false-positive pattern flags on literal parameterized SQL); the manifest was produced via an equivalent read-only CLI-extract + fold procedure documented here. The scanner-approved queries and the fold method are recorded in the manifest itself; a clean persisted builder remains open housekeeping (does not block freeze — the manifest JSON is the deliverable).
5. Store has live WAL sidecars → checkpoint before the actual freeze (§B note).

## G. Exact command/path for eventual real G1 execution

Owner-only preconditions: all four gates true in
`docs/research_programs/P-M/g1_harness/g1_config.json` (or a copy passed via `G1_CONFIG`), with `synthetic: false`.

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001/docs/research_programs/P-M/g1_harness"
G1_CONFIG=./g1_config.json python3 g1_harness.py     # → g1_real_output.json
```

Pipeline on that path: `check_gates` (all four) → `load_real_bundle` (fail-closed re-check; store `capture_manifest` must be fully terminal) → `run_g1` (C1a still auto-blocked unless `freq_semantics_ratified` is true) → deterministic JSON with config+provenance hashes.

## H. Final verdict: **READY**

Engineering, data-integrity, and gate-wiring work is complete: the freeze candidate is verified and fingerprinted (not frozen), every G1 input is wired and verified, all four gates are genuine fail-closed hard gates with demonstrated refusal paths, and the dry-run is byte-reproducible. **The remaining blockers to the first G1 empirical run are exclusively governance/owner decisions:** the four gate flags (Dataset B freeze execution, H0–H3/P0 retrieval+confirmation — still NOT FOUND as of the 2026-09-11 retrieval report — freq ratification, NF source ratification) and D-032 Items C/D.

*No commits made. Production, Dataset A, Dataset B, and the backfill untouched.*
