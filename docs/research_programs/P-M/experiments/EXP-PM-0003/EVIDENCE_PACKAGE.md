# EXP-PM-0003 — Evidence Package (terminal)

> The terminal evidence product for the confirmatory experiment of **HYP-PM-0003**. This package binds the frozen registration, the frozen manifest, the immutable results, and the lifecycle transition receipts into one auditable record. **No experimental result is restated with any modification** — every number below is quoted verbatim from `results.json` / `execution.log`. Authored at close-out; the underlying results are immutable.

**Owner:** Research Director / CRO · **Authored:** 2026-09-09 · **Governed by:** [[HYPOTHESIS_LIFECYCLE]] (T5/T7, HL-1) · [[EVIDENCE_MODEL]] (EV-9, C2) · [[FAILURE_LIBRARY_SCHEMA]] (O8)

---

## 1. Identity

| Field | Value | Source |
|---|---|---|
| Experiment ID | **EXP-PM-0003** | MANIFEST |
| Hypothesis ID | **HYP-PM-0003** | REGISTERED |
| Registration timestamp | 2026-09-09T09:22:00Z | REGISTERED §receipt |
| Registration hash (seal) | `a2db92047e5e23f8c0bb8949797e7750706b6bfe33fa744509ef6a782f6f53f5` | REGISTERED = MANIFEST = results.json |
| Dataset A fingerprint | `329b22e49f0ef882b6da031f437e9d87084d2863837ebf8c830de362b7942558` | REGISTERED · MANIFEST · results.json — identical |
| Code commit | **N/A — uncommitted** (working-tree HEAD `9b6e3800c3dbdd0e717b00da91f0eccfda0f7226`, but this script/close-out are not part of any commit) | MANIFEST |
| Pipeline / script | `run_exp_pm_0003.py` · sha256 `b32fde97ca1666d8166738f9250d78b446697f22f0a31a173fa73fd05283c55b` | MANIFEST; == on-disk, re-verified unchanged before execution |
| Execution timestamp (`run_utc`) | **2026-09-09T09:44:17Z** | results.json = execution.log line 1 |
| **Experiment status** | **COMPLETED** | this package |
| **Hypothesis terminal status** | **FAILED** (F2 · Prediction failure) | [[FAILURE_ENTRY]] · [[HYPOTHESIS_REGISTRY]] |
| Evidence tier reached | **C2** (EV-9, N=1, in-sample per history-maturity gate D-046/D-047) — competent refutation | REGISTERED §expected_evidence_product |

## 2. Lifecycle transition receipts (HL-1 — no receipt, no transition)

Two transitions occurred; each carries its mandatory receipt.

### T5 — REGISTERED → IN_TESTING (custody receipt)

| Field | Value |
|---|---|
| Guard | Experiment approved (G2 Code Review, CLEARED — see G2 review turn, 12 checklist items, 3 non-blocking findings recorded); custody enforced; consistency gate 11/11 PASS re-verified at `run_utc` |
| **When** | 2026-09-09T09:44:17Z (`run_utc`) |
| **By whom** | Owner/CRO execution authorization (this task's preceding turn: "Authorize execution of EXP-PM-0003 on WSL/Dell…") |
| **Once** | Single confirmatory run; no re-run, no parameter change (any re-run with a changed parameter is a *new* experiment — MANIFEST §Immutability) |
| Partition | **IN-SAMPLE** — no OOS partition released, none exists (`oos_partition: NONE`, REGISTERED). Per the registered history-maturity gate (D-046/D-047), the guard clause "OOS opened once, logged" is vacuously satisfied — there is no OOS partition to open |

### T7 — IN_TESTING → FAILED (failure receipt)

| Field | Value |
|---|---|
| Guard | One F-mode, attribution defended against auxiliaries (R1) |
| Receipt | **[[FAILURE_ENTRY]]** (O8) — mandatory, immutable, never deleted ([[FAILURE_LIBRARY_SCHEMA]]) |
| F-mode | **F2 · Prediction failure** — the pre-registered criterion was not met |

## 3. Result (verbatim from `results.json` / `execution.log` — not modified)

**Consistency gate (re-run automatically as part of execution):** 11/11 PASS.

**Bootstrap CI on pooled signed_continuation** (`research/statistics.py::bootstrap_ci`, n_boot=10000, ci=0.95, seed=20260711), `n_analysis_observations = 20,604` (nonzero net_flow ticker-date pairs) before per-k trimming for a valid k-ahead close:

| k (trading days) | tag | n | gross signed_continuation | CI95 | net-of-cost |
|---|---|---|---|---|---|
| 3 | robustness | 20,509 | `-0.0287%` | `[-0.1080%, +0.0508%]` | `-0.6287%` |
| **7** | **PRIMARY** | **20,509** | **`+0.0538%`** | **`[-0.0656%, +0.1768%]`** | **`-0.5462%`** |
| 15 | robustness | 20,277 | `-0.0044%` | `[-0.1823%, +0.1804%]` | `-0.6044%` |

**Robustness gradient** signs across k∈{3,7,15} = {−, +, −}. Unlike `HYP-PM-0001`, `HYP-PM-0003`'s registered spec did not declare an explicit "all-k-must-agree" consistency rule for k∈{3,7,15} (`HYP-PM-0003_REGISTERED.md` `formation_horizon_k`: *"reported as robustness — not a selection scan"*) — this sign pattern is reported as a fact, not applied as an independent additional refutation trigger beyond the primary k=7 result.

**Dependence-sensitivity diagnostic** (labeled sensitivity only, not a correction, per `HYP-PM-0003_POWER.md` §5): at k=7, point estimate moves from `+0.0538%` (N=20,509) to `-0.1005%` (N/10=2,050) to `-0.9149%` (N/100=205) — reported for completeness; not used in the refutation decision, which rests on the primary (full-N) bootstrap CI only.

## 4. Decision against the preregistered rule (verbatim)

> **Frozen falsification rule** (REGISTERED §falsification): *"Net-of-cost signed continuation of daily broker-flow-implied price displacement at k=7 trading days is not significantly positive (bootstrap_ci CI does not exclude zero net-of-cost, or the point estimate does not clear the 0.60% round-trip friction floor) ⇒ M2.1's permanence prediction is REFUTED for this data source and horizon."*
> **Frozen alternative** (REGISTERED): *"H1: net-of-cost signed continuation at k=7 > 0."*
> **Frozen MDE** (friction-anchored): gross continuation that must be cleared = **0.60%** round-trip.

**Applying the rule to the frozen primary estimator (k=7):**
- Gross signed continuation = **`+0.0538%`**, CI95 `[-0.0656%, +0.1768%]` — **includes zero** — the refutation condition ("CI does not exclude zero net-of-cost") is met on the gross figure alone, before cost.
- Net-of-cost signed continuation = **`-0.5462%`** — does not clear the `+0.60%` floor — refutation condition met a second, independent way.

**⇒ M2.1 (adverse-selection permanence, I7) is REFUTED for this data source (`broker_flow`/Dataset A) and horizon (k=7).** The hypothesis transitions to **FAILED**.

## 5. Failure-mode determination (exactly one, defended — R1)

**Filed: F2 · Prediction failure** — the pre-registered criterion was not met. Full attribution defense: [[FAILURE_ENTRY]].

## 6. Internal-consistency audit

| Anchor | Cross-checked across | Result |
|---|---|---|
| Registration hash `a2db9204…` | REGISTERED §receipt · MANIFEST §Identity · results.json `registration_sha256` | **MATCH (3/3)** |
| Registration seal | SHA-256 of frozen bytes recomputed this session, twice (post-fix and pre-execution) | **MATCH** — seal intact, frozen object untampered |
| Dataset A fingerprint `329b22e4…` | REGISTERED · MANIFEST · results.json · G2 review · this package | **MATCH** |
| Roster sha256 `7d4eb100…` (newline-joined convention) | REGISTERED · MANIFEST consistency check (11/11) · execution-time re-check (11/11) | **MATCH** |
| Execution timestamp `2026-09-09T09:44:17Z` | results.json `run_utc` · execution.log line 1 | **MATCH** |
| Script sha256 `b32fde97…` | MANIFEST · on-disk `sha256sum`, re-verified immediately before execution | **MATCH — unchanged since G2 review** |
| `k_primary = 7` · `friction = 0.60%` (0.006) | REGISTERED · MANIFEST · results.json · execution.log | **MATCH** |
| Primary result `+0.0538%` (net `-0.5462%`) | results.json `continuation.k7` · execution.log | **MATCH** |
| Statistical test = `bootstrap_ci`, no clustered inference | REGISTERED · G2 review checklist item 7/8 · script import list | **MATCH — no clustered-inference code exists or was added** |

**Audit verdict: PASS** — every document references the same execution timestamp (`2026-09-09T09:44:17Z`), the same script hash (`b32fde97…`), and the same result (k=7 gross `+0.0538%`, net `-0.5462%`).

## 7. Institutional value (R12 — negative evidence is evidence)

A competent refutation is a first-class product (PG-11, R12). EXP-PM-0003 maps a boundary on I7 (adverse-selection permanence) for `broker_flow`/Dataset A daily net signed flow at 3–15 trading-day horizons: no capturable, cost-surviving continuation signal is measurable. Per the preserved observation-dependence caveat (A-PM3.3), this result is **not**, by itself, independent evidence separable from `HYP-PM-0002`'s own (unregistered, not-yet-executed) test of the same I7 entry on `stockbit_flow_bars` — any future joint reading of both results must carry that caveat forward. The only legitimate continuation for this specific object is a **new** registration under T12 (supersession); there is no path back (HL-3, §5 below).

## 8. Lineage

[[HYP-PM-0003_REGISTERED]] · [[HYP-PM-0003_DRAFT]] · [[HYP-PM-0003_POWER]] · [[MANIFEST]] · [[FAILURE_ENTRY]] · [[HYPOTHESIS_REGISTRY]] · [[FAILURE_REGISTRY]] · [[HYPOTHESIS_LIFECYCLE]] · [[EVIDENCE_MODEL]] · Dataset A: `BROKER_FLOW_DATASET_A_EMPIRICAL_READY_HANDOFF_2026-09-09.md` (D-043, FROZEN, unchanged by this close-out).
