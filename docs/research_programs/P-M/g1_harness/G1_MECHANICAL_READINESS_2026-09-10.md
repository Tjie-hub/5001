# G1 MECHANICAL READINESS / DRY-RUN REPORT — 2026-09-10

**Task:** prepare and mechanically validate the G1 empirical harness. HARNESS ONLY — the live G1 empirical test was NOT run. No real G1 alpha/IC/returns computed anywhere. No hypothesis/specification/dataset/production code modified. Nothing committed.

**Location of the harness (built this task):** `docs/research_programs/P-M/g1_harness/`
`g1_harness.py` · `g1_config.json` · `g1_synthetic.py` · `test_g1_harness.py` · `g1_dry_run_output.json`

---

## FINAL STATUS: **READY** — with four mechanical gates closed (§11)

The harness is mechanically ready: a complete G1 pipeline now exists, is synthetic-validated (15/15), deterministic (byte-identical re-runs), wired to the exact Dataset B interface, and mechanically incapable of touching real data until all four gates are true. G1 can execute immediately once (1) Dataset B is frozen, (2) H0-H3/P0 is confirmed, (3) freq semantics are ratified, (4) the net-flow control source is ratified. Honoring the stop condition, nothing was launched.

## 1. G1 entry point

Before this task **no G1 harness existed anywhere** (searched: project tree, ZCodeProject, worktrees, scratchpad; the only "G1" artifacts were the retired S2-cycle open-integrity census for the shelved I3 candidate). The harness was therefore built as the preparation work, implementing:

- **Research definition (frozen input, unmodified):** `pm_data_audit/PM_SPECIES_MECHANISM_BFI002_DESIGN_2026-09-10.md` — family {C1a primary, C2, C3}, Holm α=0.05, k∈{3,5,10}, primary k=5, 0.60% RT cost floor.
- **Execution conventions (inherited verbatim):** `ZCodeProject/bfi001_broker_flow/10_execute_bfi001.py` — daily spread series → Newey-West(k) t (this program's date clustering), two-sided p via erfc, Holm step-down, ADV20 = rolling-20-session **median** of traded value `shift(1)`, price floor 100, breadth floor 40, |ret1|≥0.15 exclusion, CA-in-(t,t+k] invalidation.
- **Measurement (Dataset B-owned):** `dataset_b/foundation.py` — PIT roster, session calendar with session-indexed `k_ahead` and strict contiguity, corporate-action basis detection, close→close forward returns.

Entry: `python3 g1_harness.py` (synthetic dry-run) / `load_real_bundle()` + `run_g1()` (gated real path).

## 2. Files inspected (read-only)

- `docs/research_programs/P-M/`: S2-PM-0004_G1_RESULT (retired G-1), HYP-PM-0001_REGISTERED (conventions), family map, D1_D2 audit, dataset_b/ (foundation.py, validate.py, backfill_broker_flow.py, DATASET_B_FOUNDATION_CLOSURE_REPORT, SEMANTIC_REGISTER_v1, VALIDATION_REPORT_v1, PIT_ROSTER/SESSION_CALENDAR v1+v2 artifacts)
- `ZCodeProject/`: BFI-002 design memo, custody handoff, bfi001 harness (10_execute_bfi001.py)
- production `walkforward.db` (ro): trading_calendar, broker_flow, suspension_events, ohlcv, stockbit_flow schemas; Dataset B store (ro): capture_manifest (14,649 SUCCESS / 2 EMPTY at 20:09, 2025-01-02→2025-10-15, ~37% of 101×386)

## 3. Files changed/created

Created (new directory, nothing overwritten): the four harness files above + dry-run output. **Zero production files modified; zero commits.**

## 4. Mechanical bugs found/fixed (all caught by the synthetic dry-run)

1. **Gross-value collapse (critical, in new harness code):** `gross = buy_v + sell_v` summed signed sell values → gross was actually NET flow; every sell-dominated ticker-day got `gross ≤ 0` and was silently dropped. Fixed to `buy_v + abs(sell_v)`; fixture now asserts exact gross per cell (e.g. AAA = 60,000,000 exactly).
2. **C3 history wiped by the formation filter:** trailing breadth medians were computed after the breadth-floor filter removed early sessions → surprise undefined at the first formation dates. Fixed: surprise computed over the FULL valid panel (strictly past), then the floor filter applies.
3. **NaN literals in JSON output:** cells with no computable days emitted `NaN` (invalid JSON). Fixed: non-finite → `null`; Holm treats non-finite p as 1.0; output verified strict-JSON parseable and NaN-free.
4. **CA-exclusion placement:** initially a trailing (≤t) exclusion — contradicts the inherited BFI-001 convention. Corrected to k-window-specific: CA strictly inside (t, t+k] invalidates the observation (k=3/5/10 separately, counted in output).
5. Scanner-driven hardening: guarded output-path writes (abspath+commonpath), no `NOT IN` SQL.

## 5. Synthetic tests added (15, all PASS)

`test_g1_harness.py` — tiny 8-ticker / 39-session / 6-broker fixture with hand-derived expected values (documented in `g1_synthetic.py` docstring):

| # | Trap covered | Test |
|---|---|---|
| 1 | Mechanical gates block real runs | test_gate_blocks_real_run |
| 2 | Excluded-session strict contiguity (no window may cross the holiday) | test_calendar_indexing… |
| 3 | Forward-return horizon exactness (session-indexed, engineered +2%/0%/+1% returns verified to 1e-9) | test_horizon_exact… |
| 4 | Corporate-action window filter (applied 5:1 split ex-date inside (t,t+k] drops 2 cells at k=3, 3 at k=5; no false −80% anywhere) | test_corporate_action… |
| 5 | Suspension / missing-bar handling (suspended session + no-prior-close formation both excluded, counted) | test_suspension… |
| 6 | PIT membership, delist/list mid-sample, quarantine, never-member bait ticker | test_pit_membership… |
| 7 | Duplicate-join de-dup + unclassified-broker exclusion proven by exact gross | test_dedup… |
| 8 | T+1 leakage (flow dated t+1 / excluded session appears nowhere; formation t uses trade_date==t only) | test_t_plus_one… |
| 9 | Breadth floor + full stage-by-stage row accounting (150 formed, every exclusion counted) | test_breadth_floor… |
| 10 | C1a θ exactness (+2% on 02-03, −(200/204−1) on 02-06, nothing else) + freq gate blocks C1a with no numbers | test_c1a… |
| 11 | C2 disagreement spread exactness | test_c2… |
| 12 | C3 breadth-surprise spread exactness (+1% single day) | test_c3… |
| 13 | Inference NaN-safety (constant series → nan t, no fake significance), Holm monotonicity | test_inference… |
| 14 | Output determinism (byte-identical, strict JSON, all decision-gate fields present) | test_output… |
| 15 | **Parity with foundation.forward_returns** (harness engine ≡ Dataset B-owned engine on fixture data, in-memory DB) | test_parity… |

## 6. Test results

**15/15 PASS** (`python3 test_g1_harness.py`), plus standalone `python3 g1_harness.py` dry-run end-to-end with **byte-identical output on re-run** (sha256 70dff8d5cc4c4089…). No real data touched by any test.

## 7. Leakage checks

- **PIT universe:** formation rows only for roster members at t (fixture proves mid-sample delist/list honored; never-member ticker with full bait data never enters). Roster consumed from sha-verified artifacts, never re-queried live.
- **T+1 availability:** signal uses flow rows with trade_date == t exclusively; fixture proves a next-day-dated dump cannot leak. Standing DEP-B note: the after-close availability *convention* remains prose-only (handoff item #8) — inherits whatever the authoritative preregistration declares; no code assumption beyond trade_date==t.
- **No future information:** ADV20 shift(1), trailing breadth medians strictly past, species prefix ≤ 2025-09-30, ST tercile cuts config-frozen (declared from the memo's measured distribution, marked CONFIRM-AT-PREREG).

## 8. Alignment checks

Horizons count sessions on the declared calendar (never calendar days, never row-shifts); strict contiguity drops any window containing an excluded session; corporate actions invalidate windows they fall inside; suspension and missing-bar observations are dropped with counts; every join is on natural keys with duplicate detection and per-stage row accounting (flow_rows_in → dedup → quarantine → unclassified → panel formed → floor filter → fwd availability → CA filter).

## 9. Dataset B interface requirements (what G1 consumes when the backfill completes)

| Input | Source | Status |
|---|---|---|
| PIT roster (101 tickers, 8 periods) | `DATASET_B_PIT_ROSTER_v2.json` (sha-verified) | READY |
| Session calendar (386 sessions 2025-01-02→2026-08-27, 3 excluded) | `DATASET_B_SESSION_CALENDAR_v2.json` | READY |
| Broker flow (limit=150: value/lot/freq/investor_type per broker-side) | store `broker_flow_b` | IN PROGRESS (~37%) |
| Bandar totals (uncensored buyer/seller counts) | store `bandar_detector_b` | IN PROGRESS |
| Capture completeness check | store `capture_manifest` (all cells SUCCESS/EMPTY, date_echo_match) | enforced by loader |
| OHLCV (is_final=1) | production walkforward.db (ro) | READY |
| Suspensions | production `suspension_events` expanded over calendar | READY |
| Corporate actions + adjustment basis + quarantine | `foundation.load_corporate_actions` + `detect_unapplied_splits` + `vwap_ratio_report` | READY |
| Forward returns | `foundation.forward_returns` rules (parity-tested) | READY |
| **Net-flow control (NF)** | **NOT IN DATASET B.** broker_flow net ≡ 0 exactly at limit=150 (2026-09-10 trial). Loader wires a PROVISIONAL stockbit_flow share-based NF, hard-gated (`net_flow_source_ratified=false`). **Must be ratified at preregistration or added to Dataset B — not fabricated.** | **GAP — gated** |

## 10. G1 GO/NO-GO checklist

| Item | Verdict | Evidence |
|---|---|---|
| A. CODE READY | **PASS** | Harness complete incl. gated real loader; implements frozen BFI-002 design + BFI-001 conventions; loader never executed (gates closed) |
| B. SYNTHETIC TESTS PASS | **PASS** | 15/15, hand-verifiable fixture, byte-identical dry-run |
| C. DATA INTERFACE READY | **PASS** (as built) | Loader consumes exactly the §9 sources, fails loudly on any gap; net-flow ratification carried as gate, not silently substituted |
| D. PIT LEAKAGE CHECK | **PASS** | Test 6 + sha-verified artifact roster; no live roster reads |
| E. T+1 LATENCY CHECK | **PASS** | Test 8; DEP-B timestamp-convention note carried to prereg |
| F. HORIZON ALIGNMENT | **PASS** | Tests 2/3/15: session-indexed, strict contiguity, foundation parity |
| G. JOIN INTEGRITY | **PASS** | Test 7: natural-key dedup, exact-gross asserts, per-stage accounting |
| H. CORPORATE-ACTION CHECK | **PASS** | Test 4 + quarantine path (RAJA-analog fixture ticker) |
| I. INFERENCE CHECK | **PASS** (as configured) | NW(k) daily-series clustering (program convention), Holm family, NaN-safe; final method binding awaits preregistration (no substitution made) |
| J. OUTPUT/REPRODUCIBILITY | **PASS** | Deterministic JSON (allow-nan-free), config+provenance hashes, decision-gate fields (θ, NW t, p, Holm, n_days, cost-floor sensitivity) |

## 11. Remaining blockers (all external to the harness; encoded as mechanical gates)

1. **`dataset_b_frozen`** — Dataset B backfill running (~37%: 14,649/39,000-ish cells through 2025-10-15); store + validation 35/35 exist; freeze gates not yet taken.
2. **`prereg_confirmed`** — authoritative H0-H3/P0 not yet retrieved/locked; CONFIRM-AT-PREREG parameters flagged in config: ST tercile cuts, ADV20 statistic (implemented as rolling-20-session **median, shift(1)** — the inherited BFI-001 convention), inference binding, NF-bucket definition.
3. **`freq_semantics_ratified`** — SEMANTIC_REGISTER_v1: `broker_flow.freq` UNKNOWN/FORBIDDEN as ticket denominator → C1a/C1b emit BLOCKED_FREQ_SEMANTICS with no numbers; C2/C3 (freq-free) remain computable. Per the design memo: if freq resolves against the design, C1a is withdrawn, not re-cut.
4. **`net_flow_source_ratified`** — the registered NF control must come from outside broker_flow (≡0 at limit=150); provisional stockbit_flow wiring is gated off.

## 12. Stop condition honored

No live G1 run; no real Dataset B read beyond schema/progress counts (read-only); no real empirical number produced. The first real G1 number waits for: Dataset B complete + validated + frozen AND H0-H3/P0 locked AND gates 3-4 ratified — at which point `set gates → true; python3 g1_harness.py` executes immediately.
