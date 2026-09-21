# FOUR-TEST ACCOUNTING-IDENTITY FORENSIC AUDIT + MASTER REGISTRY RECONCILIATION — 2026-09-11

**Mode:** forensic verification and triage. No new hypothesis, no C7/C6/C8 execution, no parameter tuning, no registry mutation, no historical reclassification, no deletion, no methodology rescue.

**Claim under test (per task brief):** a systemic accounting-identity defect — all-broker buy/sell sides are the two sides of the same trades, forcing aggregate net/gross to zero — invalidated **BFI-001, HYP-PM-0003, G1 C2, and NR7/P0**.

**Headline findings (independently verified):**
1. The identity defect is **real, measured, and systemic for every all-broker aggregate net/gross construction** (BFI-001 primary, HYP-PM-0003, G1 C2's underlying class nets).
2. It does **NOT** touch NR7/P0 (no broker-flow component — independently verified from the registration, gatekeeper record, and falsification report). The task brief's inclusion of NR7 in the affected set is **not supported**.
3. It does **NOT** invalidate BFI-001's structure secondaries (CONC/BREADTH/LOKAL — not net/gross quantities) nor HYP-PM-0001 (vendor aggressor-side instrument — structurally immune).
4. HYP-PM-0003's predictor is **semantically degenerate** (identically zero on 68.10% of ticker-days — independently reproduced): the economic hypothesis was never tested on a valid directional observable.
5. G1 C2's "disagreement" state is **algebraically coupled, not independent** — but the claimed 100% tautology / 98.5% gate incidence are **not reproduced** by my measurement (77.79% opposite-sign; 72.5% gate incidence). C2 = INVALID — SPECIFICATION, with corrected figures.

---

## PART A — FOUR-TEST FORENSIC VERIFICATION

### A.1 BFI-001 / BROKER-001

**Registered predictor** (`bfi001_broker_flow/00_PREREGISTRATION_FROZEN.md` §E, sha `91c0eb9a…`): per stock-day over broker rows — `NV(i,t) = Σ_b value` (signed; SELL negative), `GV(i,t) = Σ_b |value|`; **PRIMARY `BFI_broad(i,t) = NV/GV`** (all brokers, all investor types), cross-sectionally ranked into deciles D1…D10, primary spread D10−D1 at k=5; secondary F1 horizons on the same predictor; F2 investor-class splits (Asing/Lokal/Pemerintah nets); F3 normalizations N1 = NV/ADV20, N2 = abnormal-flow z of NV, **N3 = signed lot share = Σ signed lot / Σ|lot|**; F4 broker-identity cells (CONC, BREADTH, BFI_informed).

**Implementation** (`10_execute_bfi001.py`, executed 2026-09-03): value column of production `broker_flow` (top-25 disclosed), per (ticker, t), all disclosed brokers.

**Input fields:** `value` (signed IDR), `lot` (for N3), investor_type, counts.

**Aggregation level / subset:** all **disclosed** brokers = top-25 per side (Dataset A truncation).

**Are buy/sell two sides of the same trades?** YES at top-25: when both counterparties of a trade are inside the disclosure, their flows appear on opposite sides and cancel; when one side is outside the top-25, the residual appears as net. Therefore `BFI_broad` is **directional in form** (a signed ratio in [−1,+1]) but its content is the **top-25 truncation residue**, not market-wide directional imbalance.

**Forced to zero?** At top-25: **no — an approximation artifact** (independently measured below: |NV/GV| p50 = 0.0, p90 = 0.00201, p99 = 0.0146, max = 0.0602 over 97,762 ticker-days). At full population (limit=150): **yes — identically zero** (measured: 30,877/30,877 cells exact).

**Recorded result** (`bfi001_broker_flow/90_results.json`, verified): PRIMARY_bfi_k5 mean +1.36 bp/step, **NW t = +0.047**, p = 0.962, Holm 1.0. Original conclusion: no signal; structure cells carried the footprints (CONC t = −2.65 Holm 0.097; BREADTH t = +2.41 Holm 0.164; LOKAL t = +2.43 Holm 0.164).

**Directional or dispersion?** `BFI_broad = NV/GV` **is a directional quantity by formula** — the net share of gross. It is **not** the concentration quantity (that is CONC = HHI_buy − HHI_sell, a separate cell). However, its measured content is the truncation residue: |BFI_broad| ≤ 6% of gross for 100% of ticker-days, ≤ 0.15% for 90%. A decile sort of this variable ranks names by ~basis-point disclosure asymmetries. **The primary test therefore ranked a near-degenerate, mechanically bounded quantity** — this is precisely what the identity+truncation structure predicts, and it is why the primary null is uninformative as a directional test.

**Classification impact:** the PRIMARY cell is **INVALID — DATA/SEMANTICS** (identity-attenuated predictor). The F3 normalizations N1/N2 (NV-based) inherit the attenuation; **F3_lots (N3 = signed lot share) produced NO result at all (NaN in 90_results.json)** — the lot identity made the cell uncomputable, which is the identity defect visible inside BFI-001's own recorded family table. The F2 class-split cells and F4 structure cells used class-level/structure quantities and are **VALID** (their nets do not self-cancel because the omitted brokers absorb the difference).

### A.2 HYP-PM-0003 / EXP-PM-0003

**Preregistered predictor** (`HYP-PM-0003_REGISTERED.md` `signed_lot_convention`, verified in `run_exp_pm_0003.py:8,163-165`): `net_flow(ticker,date) = SUM(lot)` over `broker_flow` rows — "already-signed, no BUY-minus-SELL subtraction"; unit = (ticker, formation-date) with `net_flow != 0`; endpoint `sign(net_flow_t) × fwd_ret_7`; bootstrap_ci, seed 20260711.

**Both signed sides of the same trades?** YES — `lot` is the broker's signed net lot for the session (dominant side); SUM over all disclosed brokers = total buy lots − total sell lots = the exchange identity in lots.

**Dataset/population:** Dataset A frozen (`329b22e4…`), 2025-01-02→2026-08-27, 79 tickers, 1,222,713 rows → 97,762 ticker-days; 20,604 observations retained after the `net_flow != 0` filter.

**Exact degree of zero identity (independently recomputed, matching the audit):**

| Measure | Value (independent) | Claude audit |
|---|---|---|
| SUM(lot) exactly zero | **68.10%** of 97,762 ticker-days (66,575) | 68.10% ✓ |
| total net lots vs Σ\|lot\| | −54,819,988 / 201,728,436 | — |
| \|NV/GV\| on values, same window | p50 0.0 · p90 0.00201 · p99 0.0146 · max 0.060 | p95 \|nf\| = 0.001 (family map) |

**Was it genuinely failed or never tested?** The registered predictor is the **sign of an accounting residue**: on 68.10% of ticker-days it is identically zero (filtered out — a disclosure-driven, non-random selection), and on the retained 31.9% it is the sign of the top-25 truncation residue worth ~0.2% of the day's lot turnover. The economic hypothesis — *adverse-selection permanence of directional net flow* (M2.1/I7) — presupposes a meaningful directional net-flow observable. At full population that observable is **identically zero by the exchange identity**; at top-25 it is a censored truncation artifact. **The hypothesis was never tested on a semantically valid predictor.** The registered F2 is procedurally correct (the registered test was run as registered) but scientifically vacuous.

**Classification: INVALID — DATA/SEMANTICS** (primary: predictor degeneracy via accounting identity + truncation; secondary: RAJA split contamination — Dataset A had no quarantine; non-random `!= 0` conditioning; 22-minute registration-to-execution gap). Historical registry row (FAILED F2) stands unmodified; the reclassification is proposed, pending owner.

### A.3 G1 C2

**Registered state** (`G1_REGISTRATION_v1_2026-09-11.md`): for/loc conduit disagreement — `for_gross ≥ 0.15 AND loc_gross ≥ 0.15 AND opposite net signs`; contrast = mean fwd(high/long side) − mean fwd(short side).

**Descriptive-generator state** (`12_discovery_structures.py` lineage, measured on Dataset A): class **net-share** gates — \|for_net\| ≥ 15% of gross, \|loc_net\| ≥ 15%, opposite signs — measured incidence ≈ 26.6–30.2% of name-days.

**Execution state (measured this audit, frozen store, integer-exact class nets, 30,877 cells):**

| Quantity | Measured |
|---|---|
| `for_net + loc_net + pem_net = 0` (integer-exact) | **30,877 / 30,877 = 100.00%** |
| opposite-sign cells (both class nets nonzero) | 24,019 = **77.79%** |
| same-sign cells | 6,858 = 22.21% — **exactly the Pemerintah-dominant cells** (6,858) |
| execution-gate incidence (gross-participation ≥ 15% both legs AND opposite sign) | **22,381 cells = 72.5%** |
| descriptive net-share gate incidence | **8,210 cells = 26.6%** |

**Gate difference:** the registered execution gate uses **gross-participation** shares (Σ|value| per class / gross), which sum to ≈ 100% across two classes whenever Pemerintah is negligible — so "both ≥ 15%" is near-vacuous (72.5% incidence measured; the audit reported 98.5% on its panel — same direction, different denominator; my figure is derived and shown). The descriptive generator's gate used **net shares** (26.6% — reproduced exactly). The swap inflates incidence ≈ 2.7×.

**Tautology:** `for_net + loc_net = −pem_net` holds identically. Where |pem_net| is small relative to the classes, `sign(loc_net) = −sign(for_net)` is **algebraically forced**, so the "disagreement" state reduces to `sign(for_net) ≠ 0` — a one-bit function of a single quantity (foreign-directional net), not an independent two-party observable. Measured: opposite-sign in 77.79% of cells (the algebraic regime); same-sign only where Pemerintah dominates (22.21%). **The mechanism label "two independent classes in disagreement" is misleading — the state is a thresholded function of one directional quantity.** However it is *not* the identity-zero defect (foreign class-level net has genuine variance and is not forced to zero — only the three-class SUM is).

**Exact recorded output** (`G1_REAL_OUTPUT_RUN1_2026-09-11.json`): C2 k=5 n_days = 359, θ = +4.9 bp, NW t = +0.548, Holm p = 1.0; k=3 +5.7 bp (t=0.75); k=10 −2.1 bp (t=−0.16).

**Correct classification: INVALID — SPECIFICATION** (primary: the registered disagreement state is algebraically coupled — near-tautological — under the three-class sum-zero identity; secondary: the execution gate ≠ the descriptive gate that motivated the candidate, inflating incidence 26.6%→72.5%). The C2 number is reportable only as "an unconditional thresholded foreign-net direction contrast produced a null" — **not** as a test of conduit disagreement.

### A.4 NR7 Breakout / Program P0

**Trace:**
- Registration: `docs/archive/superpowers_plans/specs/2026-07-12-prereg-nr7-bull-lowliq-v1.md` (registered 2026-07-12, commit `002dca46`, prereg hash `6b46d7ee…`, seed 20260711). Post-hoc discovery (BULL∧LOW_LIQ cell, +2.29%/trade, n=201) frozen as a forward test with promotion bar τ = +0.50%/trade.
- Predictor: **NR7 = narrowest 7-day range contraction** (OHLCV), breakout entry; overlay regime=BULL ∧ liquidity tier=LOW_LIQ. **No broker-flow component of any kind** — no `broker_flow`, no `value`, no `lot`, no sign/net construction.
- Data: OHLCV/universe tables; falsification walk-forward over 959 tickers, 6,183 OOS trades.
- Gate: 6 gatekeeper runs in `data/research.db::gate_decisions`, all `REJECT` (walk_forward FAIL).
- Falsification: `data/reports/nr7_falsification_2026-09-03.md` — pooled OOS expectancy **−0.1787%/trade** (n=6,183), bootstrap CI [−0.3727, +0.0163] includes 0; the +1.64pp/54-cell positive is a selection artifact of the n≥20 floor; D-029 demoted to SHADOW ("No capital").
- Failure registry: `data/research.db::failure_registry` id `9681dbdc…` "NR7 Breakout: falsified as a strategy-level edge…"

**Does the accounting-identity defect invalidate NR7? NO.** NR7's predictor contains no broker-flow net/gross construction — the identity is undefined for it. The audit document (`FULL_HISTORICAL_EMPIRICAL_AUDIT_2026-09-11.md` §7) does **not** actually claim the identity affects NR7 either: its §7 heading is "INVALID AS AN EDGE CLAIM; FALSIFIED", documenting NR7's **own independent walk-forward falsification** and its role as the program's reference implementation. The task brief's premise — that the audit extends the identity defect to NR7/P0 — is **not supported by the audit text**, and my verification confirms NR7 is identity-N/A. **Claude's (alleged) NR7 conclusion is REJECTED as an identity claim; NR7's FALSIFIED/SHADOW status is retained on its own evidence.**

## PART B — INDEPENDENT IDENTITY MEASUREMENTS (this audit, from the actual tables)

| Dataset | Cells | Σbuy == Σsell exact | \|net\|/gross p50 | p90 | p99 | max |
|---|---|---|---|---|---|---|
| **Frozen Dataset B store (limit=150, full population)** | 30,877 | **100.00%** | 0.0 | 0.0 | 0.0 | **0.0** |
| **Production `broker_flow` (top-25, Dataset A window)** | 97,762 | 69.90% | 0.0 | 0.00201 | 0.014588 | 0.060225 |
| Frozen store, per-day SUM(lot) == 0 | 30,877 | 94.17% | — | — | — | — |
| Production, per-day SUM(lot) == 0 (registered HYP-PM-0003 predictor) | 97,762 | **68.10%** | — | — | — | — |

Whole-table check: BUY total = |SELL total| = **1,585,427,502,195,600 IDR** exactly (net ≡ 0). Truncation effect: at top-25 the residual is bounded (max 6.0% of gross, p99 1.5%) but non-zero — an artifact quantity, not an identity. Investor-type decomposition on the frozen store: `for + loc + pem ≡ 0` in **100.00%** of cells (integer-exact); opposite-sign for/loc in 77.79%; same-sign exactly where Pemerintah dominates (22.21%).

## PART D — CHALLENGE BOTH DIRECTIONS (findings)

**Evidence AGAINST a universal/systemic-everywhere reading:**
1. **NR7/P0 uses no broker flow** (OHLCV range-contraction + regime/liquidity overlay) — verified from registration, gatekeeper fingerprint lineage, and falsification report. The identity cannot reach it.
2. **HYP-PM-0001's instrument is structurally immune**: `stockbit_flow_bars` is aggressor-side vendor data whose buy/sell do not balance (BBCA 44.4M vs 63.9M shares; my NF validation: |NF| p50 = 0.175 — genuine variance).
3. **BFI-001's structure cells are identity-free**: CONC (HHI of side values), BREADTH (broker counts), LOKAL (class net — a class-level net has real variance because omitted brokers absorb the difference) all produced real footprints. Only the ALL-BROKER net/gross cells are identity-bound.
4. **Truncation creates a real (if weak) quantity at top-25**: BFI_broad ≠ 0 at top-25 — a cross-sectional rank over it is a valid ranked feature of disclosure asymmetry. The BFI-001 primary null is therefore *attenuated-and-uninformative*, not *impossible* — the distinction matters and is preserved in the classification.

**Additional same-construction uses found (completeness):**
- **BFI-001 F3_lots (N3 = signed lot share)** — identity-constructed; **produced NaN/no result** in 90_results.json (the identity visible inside BFI-001's own family table).
- **BFI-001 F3_n1/n2 (NV/ADV20, abnormal-flow z)** — NV-based normalizations: attenuated at top-25 for the same reason (N2's cell additionally crashed, n=2).
- No other program instrument consumes all-broker net/gross.

## PART E — MASTER EXPERIMENT INVENTORY (20 objects)

| # | ID / name | Registration | Execution | Dataset | Predictor class | Result | Registry | Failure registry | Identity-affected |
|---|---|---|---|---|---|---|---|---|---|
| 1 | HYP-PM-0001 / EXP-PM-0001 | REGISTERED 2026-07-17 (`540c2d52…`) | EXP-PM-0001 2026-07-18 | stockbit_flow_bars (vendor, aggressor-side) | OFI signed reversal k=15 | FAILED F2 | HYPOTHESIS_REGISTRY (1st P-M slot) | FAILURE_REGISTRY FAIL-PM-0001 | **No — immune** |
| 2 | HYP-PM-0002 | DRAFT (never executed) | — | stockbit_flow_bars | — | — | noted, no slot | — | n/a |
| 3 | HYP-PM-0003 / EXP-PM-0003 | REGISTERED 2026-09-09 (`a2db9204…`) | EXP-PM-0003 2026-09-09 | Dataset A (broker_flow top-25) | `SUM(lot)` net continuation k=7 | FAILED F2 → **proposed INVALID — DATA/SEMANTICS** | HYPOTHESIS_REGISTRY (2nd P-M slot) | FAILURE_REGISTRY FAIL-PM-0003 | **Yes — primary defect** |
| 4 | BROKER-001 / BFI-001 | research.db `hypotheses` PREREGISTERED (`91c0eb9a…`) + frozen prereg | executed 2026-09-03 (`90_results.json`) | production broker_flow top-25 | BFI_broad = NV/GV (all-broker) + structure cells | primary not confirmed (t=0.047); CONC t=−2.65 Holm 0.097 | research.db only — **no HYPOTHESIS_REGISTRY row, no FAILURE_REGISTRY row (ledger gap)** | — | **Primary yes; structure cells no** |
| 5 | G1 Run 1 — C2 / HYP-PM-0004 | G1_REGISTRATION_v1 (D-048) | G1 Run 1 2026-09-11 | Dataset B frozen | class-net disagreement state (algebraically coupled) | NOT CONFIRMED → **INVALID — SPECIFICATION** | HYPOTHESIS_REGISTRY (C-family 1st) | FAILURE_REGISTRY FAIL-PM-0004-G1 | Yes — specification + coupling |
| 6 | G1 Run 1 — C3 / HYP-PM-0005 | same | G1 Run 1 | Dataset B frozen | breadth-surprise states | NOT CONFIRMED (VALID, bounded) | HYPOTHESIS_REGISTRY (C-family 2nd) | — | No |
| 7 | C7 / HYP-PM-0006 | C7_REGISTRATION_v1 (owner-approved) | **not executed** | Dataset B frozen | intensity states | pending | HYPOTHESIS_REGISTRY (C-family 3rd) | — | No |
| 8 | C1a | G1_REGISTRATION_v1 | **never (withdrawn; θ computed in-memory then nulled — executed-in-breach per the forensic audit, non-reportable)** | Dataset B frozen | species tilt | none | G1_REGISTRATION_v1 | — | Withdrawn |
| 9 | C1b | G1_REGISTRATION_v1 | **never implemented** | — | rank-species variant | none | G1_REGISTRATION_v1 | — | Withdrawn |
| 10 | LIT-001 | frozen | executed | vendor OFI | OFI reversal k=1 | REJECTED | lit001 dir | — | No (vendor instrument) |
| 11 | LIT-002 | `10_PREREGISTRATION_FROZEN.md` (`c2b03399…`) | OOS accrual **pending** | vendor OFI | OFI accrual | pending | lit002 dir | — | No |
| 12 | H1 foreign-flow continuous | preregistered (older program) | executed | investor-class aggregates | continuous foreign net | null | h1 dir | — | Class-level, not all-broker identity |
| 13 | H6 foreign-flow extremes | preregistered | executed | investor-class aggregates | extreme events | pressure, not tradable | h6 dir | — | No |
| 14 | HLIQ / EXP-HLIQ | `08_HLIQ_PREREGISTRATION.md` (`a87b5721…`) | executed (`12_HLIQ_RESULTS.json`) | event window | liquidity-shock CAR | per its rule | hliq dir | — | No |
| 15 | NR7 Breakout / P0 | `2026-07-12-prereg-nr7-bull-lowliq-v1.md` (`6b46d7ee…`) | walk-forward ×6 + falsification 2026-09-03 | OHLCV | range contraction + BULL×LOW_LIQ | **FALSIFIED / SHADOW (D-029)** | research.db gate_decisions ×6 + failure_registry | nr7_falsification report | **No — no broker flow** |
| 16 | EXP-PA-0001 | REGISTERED (`3692e69a…`) | executed 2026-08-19 | auction data | dislocation reversal | FAILED F2 | HYP-PA-0001 row | FAILURE_REGISTRY FAIL-PA-0001 | No |
| 17 | S2-PM-0004 | census (withdrawn candidate) | executed (read-only census) | — | open-integrity census | withdrawn | S2-PM-0004_G1_RESULT | — | n/a |
| 18 | Liquidity Sweep | — | wf_edge 08ff0ca6 | OHLCV | pooled OOS | falsified | research.db failure_registry `4c2f5932` | — | No |
| 19 | distribution (shadow) | — | ft_shadow_trade | OHLCV forward | forward-negative | falsified | research.db failure_registry `4e833d8b` | — | No |
| 20 | BFI-001 sub-cells F3_lots / F3_n2 | inside BFI-001 family | executed → **NaN (no result)** | Dataset A top-25 | identity-constructed lot share; abnormal-flow z | **no result — identity/crash** | 90_results.json family | — | **Yes — identity-visible** |

Duplicate/overlapping entries: BROKER-001 exists in research.db only; the P-M family rows exist in HYPOTHESIS_REGISTRY.md only; NR7 exists in research.db (gate_decisions + failure_registry) and as docs reports; G1 arms exist only in g1_harness registration + D-048. `hypothesis_links = 0` — no cross-registry linkage anywhere.

## PART F — REGISTRY RECONCILIATION DESIGN (plan only — no destructive migration)

**Verified independently:** two disjoint failure registries (docs `FAILURE_REGISTRY.md`: 5 rows incl. the two G1 rows; `research.db::failure_registry`: 3 strategy-level rows) and two disjoint hypothesis registries (`HYPOTHESIS_REGISTRY.md`: HYP-PM-0001/0003/0004/0005/0006 + HYP-PA-0001; `research.db::hypotheses`: BROKER-001 only, PREREGISTERED, never status-updated post-execution). `hypothesis_links` = **0 rows**. BFI-001's executed outcome has **no failure-registry entry in either registry** (ledger gap).

**Minimum unified ledger — `EXPERIMENT_LEDGER` design:**

| Field | Definition |
|---|---|
| `canonical_hypothesis_id` | HYP-PM-NNN (registry convention); research.db `BROKER-001` becomes alias `HYP-PM-0007` **only if the owner ratifies** the mapping (BFI-001 = the broker-flow baseline hypothesis — the mapping is documented, and receipted by D-048's citation of the frozen prereg sha `91c0eb9a…`; the ratification itself is an owner act) |
| `canonical_test_id` | EXP-PM-NNN for experiment bundles; `G1-RUN1-<arm>` for G1 arms |
| `source_registry` | which registry the row came from (docs registry / research.db / g1_harness registration) |
| `aliases` | every other ID/ref for the same object (prereg path, BFI label, experiment dir) |
| `execution_id` | run artifact reference + output sha256 |
| `family` | P-M {I5,I6,I7,I12} or P-M C-family {C2,C3,C7} or P-A or none |
| `registration_status` | DRAFT/REGISTERED/EXECUTED/INVALID/WITHDRAWN |
| `result_classification` | Part C vocabulary |
| `failure_classification` | F-mode or INVALID·governance or NOT-CONFIRMED |
| `provenance_status` | receipts present/missing (per closeout §C) |
| `links` | hypothesis_links pairs to the duplicated/related entries (populated from the aliases; replaces the zero-link state) |

**Migration plan (non-destructive):**
1. Freeze both existing registries as-is (append-only respected; no edits, no deletes).
2. Generate `EXPERIMENT_LEDGER.jsonl` by a read-only script that joins: HYPOTHESIS_REGISTRY rows, research.db `hypotheses`/`failure_registry`/`gate_decisions`, DECISION_LOG D-references, and the g1_harness/dataset_b manifest hashes — one line per canonical experiment, with `aliases[]` and `source_registry[]`.
3. Populate `research.db::hypothesis_links` with the alias pairs (insert-only).
4. Owner reviews the generated ledger + discrepancy report (unmatched objects, status conflicts); on approval the ledger becomes the canonical index and future entries append to it.
5. No row in either existing registry is edited or deleted at any step.

**Safety valve:** if any join is ambiguous (e.g., BROKER-001 ↔ HYP-PM family-slot mapping), the ledger emits the object with `status: UNRESOLVED_MAPPING` instead of guessing — same stop-rule as this audit.

## PART G — SEMANTIC REGISTER HARD RULE (DRAFT — for owner adoption; not deployed)

**Proposed rule (register into DATASET_B_SEMANTIC_REGISTER as a hard gate; name: `all-broker-net-identity`):**

> All-broker aggregate net flow constructed as the difference of the two sides of the same transaction population MUST NOT be treated as a directional predictor, in any form: raw net (Σbuy − Σsell), net/gross ratios (NV/GV, SUM(lot)/Σ|lot|), sign() of such a net, abnormal-z of such a net, or decile/rank constructs of such a net. Any net/gross quantity must first establish, from data and registration, that its numerator contains information not algebraically cancelled by the denominator/population construction.

**Required pre-execution validation (all must PASS before the gate opens):**
1. **Accounting identity check:** on the execution dataset, compute per-aggregation-cell Σbuy − Σsell. Report exact-zero %, near-zero %, max/median |net|/gross. If exact-zero ≈ 100% (full population) or the quantity's measured dynamic range cannot support the registered contrast, the gate FAILS.
2. **Semantic source verification:** document which table/fields the signed quantities come from and whether the two sides are (a) the two sides of the same trades (identity ⇒ void) or (b) independent-side observables (e.g., aggressor-side vendor data) — with a measured buy/sell asymmetry to prove independence.
3. **Aggregation-level verification:** state whether the construction is all-broker (identity-bound) or a strict sub-aggregate (class/broker subset — residual-bearing but attenuated), and demonstrate the sub-aggregate's variance is sufficient for the registered contrast.
4. **Truncation behavior:** quantify the predictor at the actual disclosure level AND at full population; if the full-population value is identically zero, the registered quantity is a truncation artifact and must be labeled as such.
5. **PIT availability:** formation-time availability of every input, per the registered convention.

**Retroactive note:** this rule is NOT applied retroactively to BFI-001 (2026-09-03), HYP-PM-0003 (2026-09-09), or G1 C2 (2026-09-11) — their records stand; the rule governs future executions only.

## PART H — PROGRAM-LEVEL CONCLUSION

1. **Is the systemic accounting-identity defect real? YES** — independently measured: at full population (limit=150) the all-broker net is **identically zero in 100.00% of 30,877 ticker-day cells** (value, integer-exact) and 94.17% of ticker-days in lots; at top-25 it is a truncation residue (exact-zero 69.9% in value, 68.10% in lots; |net|/gross p99 = 1.5%, max 6.0%).
2. **Which tests does it invalidate?** HYP-PM-0003 (predictor = the residue itself; 68.10% of ticker-days identically zero, remaining 31.9% a disclosure artifact — the economic hypothesis was never tested); **BFI-001's PRIMARY cell and the NV-normalized cells (N1/N2) + F3_lots (NaN — uncomputable)**; G1 C2's mechanism label (the "disagreement" is algebraically coupled — though C2's null was a real measurement of a thresholded foreign-net direction, hence INVALID rather than empirically FAILED).
3. **HYP-PM-0003: genuinely FAILED or INVALID?** **INVALID — DATA/SEMANTICS.** The registered predictor is the exchange identity itself on 68% of the sample and a truncation artifact on the rest. The registry's FAILED (F2) remains the historical record; the proposed reclassification is semantic.
4. **BFI-001: FAILED/NOT CONFIRMED or INVALID?** **SPLIT.** PRIMARY (BFI_broad) = INVALID — DATA (identity-attenuated: |NV/GV| ≤ 6% max, p90 = 0.2% — near-degenerate); the structure secondaries (CONC t=−2.65, BREADTH t=+2.41, LOKAL t=+2.43) are VALID cells whose not-confirmed status (Holm 0.097/0.164) is a real (suggestive-tier) result. F3_lots/N2-family cells: identity-degenerate/uncomputable.
5. **G1 C2: INVALID?** **YES — SPECIFICATION** (algebraically coupled state + execution-vs-descriptive gate swap 26.6%→72.5%). Not the identity-zero defect itself — C2's state is a foreign-directional threshold with real variation — but its "disagreement" framing is algebraically near-vacuous, and its registered control structure was unimplementable.
6. **NR7/P0:** **NOT AFFECTED by the identity.** Independently verified: OHLCV range-contraction predictor, no broker-flow component (registration + gatekeeper record + falsification report). Its FALSIFIED/SHADOW status stands on independent walk-forward evidence. The task brief's attribution of NR7 to the identity defect is **not supported** — the audit document itself claims only "invalid as an edge claim; falsified", which is NR7's own record.
7. **What remains trustworthy:** HYP-PM-0001's null (vendor aggressor-side instrument — immune by construction); EXP-PA-0001's null; NR7's falsification; H1/H6/LIT-001 lineage results (non-broker-flow instruments); BFI-001's structure-cell footprints (CONC/BREADTH/LOKAL — suggestive tier, Holm-unconfirmed); C3's bounded null (as executed, with the registration-divergence caveat); the entire Dataset B/infrastructure layer (freeze, fingerprints, identities — all verified).
8. **Minimum governance repair:** (a) this audit's proposed reclassification record, owner-ratified (HYP-PM-0003 → INVALID — DATA/SEMANTICS; BFI-001 primary → INVALID — DATA; C2 → INVALID — SPECIFICATION; C3/C1a/C1b as ledgered); (b) the Part G hard rule adopted into the semantic register as a pre-execution gate; (c) the Part F unified EXPERIMENT_LEDGER (non-destructive, with hypothesis_links populated); (d) the two registry "Last updated" + G1 rows already entered by D-048 stand.
9. **Before C7 can execute:** the Part G gate must be adopted and C7 must pass it (it will — intensity = gross/ADV20 is Σ|value|-based, not a net construction; verified freq-free; outcome/contrast/horizons/multiplicity/MDE all owner-decided); `c7_registered=true` (owner); the `runs/<run_id>/` wrapper is implemented and wired; the governance receipts (D-048) are entered; and the commit of the governance baseline is completed (currently blocked by out-of-scope legacy scanner findings — owner decision).

---

*Every classification above cites the artifacts named in its row. The two Claude-side documents were treated as claims under test, not as authority: where they were verified they are marked as independently confirmed (HYP-PM-0003 degeneracy numbers reproduced exactly), where they were not reproduced the discrepancy is stated (C2 98.5% incidence; 100% tautology), and where the task premise attributed an NR7 identity-claim to them, the audit text itself does not contain one.*
