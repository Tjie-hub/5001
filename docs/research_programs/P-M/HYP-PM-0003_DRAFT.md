# HYP-PM-0003 — Adverse-Selection Permanence via Daily Broker-Summary Net Flow (DRAFT)

> **Status: DRAFT — held at G1. NOT REGISTERED. No family slot consumed.**
> Free-era candidate ([[HYPOTHESIS_LIFECYCLE]] §2–§3): refine freely; nothing risked until the
> irreversible `DRAFT → REGISTERED` (T4/G1). **This draft was prepared without inspecting any
> return, reversal, or continuation outcome** — every number below comes from schema/coverage
> inspection, the pre-existing frozen cost authority, or Dataset A's already-published governance
> receipts (D-032…D-047), never from computing flow-vs-return statistics. Registration requires
> explicit CRO/Owner sign-off and is **not performed by this document**.
>
> **Placeholder ID.** `HYP-PM-0003` is the next unused number — `HYP-PM-0001` is REGISTERED/
> terminal-FAILED, `HYP-PM-0002` exists as an unregistered draft (different dataset, see §0.1) and
> is **not** superseded, duplicated, or touched by this document. No `HYPOTHESIS_REGISTRY.md` entry
> is created by this draft.

**Program:** P-M · Microstructure Flow · **Family:** P-M {I5, I6, I7, I12} ([[DECISION_LOG]] D-028)
— this would be a **third member** if registered (first: `HYP-PM-0001`, FAILED F2, 2026-07-18;
second: `HYP-PM-0002`, drafted, unregistered)
**Mechanism (I7 = M2.1):** signed order-flow imbalance → adverse-selection premium → **permanence
(non-reversion)**
**Date drafted:** 2026-09-09 · **Supersedes nothing** (new data source, not a T12 revision of
either prior P-M item)

---

## 0. Why this hypothesis, and why not a duplicate of HYP-PM-0002

### 0.1 Not the same test as HYP-PM-0002

`HYP-PM-0002_DRAFT.md` also targets I7/M2.1, but its signal is `stockbit_flow_bars` (1-minute
intraday bars, daily-aggregated) — a different vendor product from `broker_flow`, and a dataset
this draft does not touch. `broker_flow` (Dataset A) is Stockbit's own **daily broker-summary**
product — a genuinely independent measurement of order flow, not a rollup of the same underlying
1-minute series. Testing I7 against both is not redundant: **`HYP-PM-0002`'s own §0 explicitly
avoided `broker_flow`'s `investor_type` breakdown** because, when drafted (2026-08-20), it spanned
only ~4.5 months — *"layering a second, shorter-history proxy on top would compound LIM4, not
reduce it."* Dataset A's now-established ~20-month span (D-046, Option C — eligible, not asserted
mature) removes that specific objection for `broker_flow` as a whole, though not for any
`investor_type` conditioning specifically (§0.2).

### 0.2 Not layering `investor_type` as the primary signal

A read-only schema check this session found `broker_flow.investor_type='Asing'` now also spans
`2025-01-02 → 2026-09-08` [DB-VERIFIED, coverage-inspection only — no flow-vs-return statistic
computed]. This is background only. The **primary specification below uses the aggregate signed
`lot` across all investor types**, not an `investor_type`-filtered subset — the more conservative,
already-fidelity-audited (R-3…R-5) measurement. An `investor_type='Asing'`-conditioned variant is
noted as a possible future robustness extension (§4, A-PM3.4) and is explicitly **not** part of the
primary claim this draft would register.

## 1. Mechanism

**Class: M2.1 · Adverse-selection spread component** ([[ECONOMIC_MECHANISM_TAXONOMY]] §3, verbatim
definition, identical citation to `HYP-PM-0002`): *"A supplier who cannot distinguish informed from
uninformed counterparties embeds an expected-loss premium in every quote, so that transaction prices
move permanently in the direction of executed flow."*

- **Participant class:** liquidity suppliers (uninformed by role) versus informed traders; no
  further sub-classification is attempted in the primary specification (§0.2).
- **Constraint:** the supplier cannot distinguish informed from uninformed flow (information
  asymmetry, D2) — identical constraint to `HYP-PM-0002`, same taxonomy entry, different
  measurement instrument.

## 2. Inefficiency / family entry

- **Primary entry: I7 · Adverse-selection premium** (M2/D2, [[MARKET_INEFFICIENCY_TAXONOMY]] I7).
- **Family:** P-M {I5, I6, I7, I12} — already declared (D-028). **This draft does not broaden it.**
  I7 is already a family member; this is a new hypothesis instance testing an already-in-scope
  entry with new data, not a new entry.
- **I5↔I7 confound (same as HYP-PM-0002 §2):** `HYP-PM-0001` tested M1.1 (I5, reversion) at
  intraday horizon on `stockbit_flow_bars` and found no significant reversion. That null does not
  confirm I7 — it is a different mechanism-test, different horizon, different data. This draft is
  independent of both prior items and, per PG-3/OS-10, would join the family as its own,
  independently-counted member if registered.
- **I6, I12:** modifiers only (liquidity/capacity conditioning of premium magnitude), not competing
  mechanisms — same role as in `HYP-PM-0001`/`HYP-PM-0002`.

## 3. Directional / sign-specific prediction

Price displacement conditional on a signed **daily** net broker-flow imbalance on formation day *t*
**does not revert** — a nonzero fraction persists — over the following *k* trading days. Positive
net flow → positive contemporaneous/near-term return → subsequent return **continues in the same
direction** (does not reverse sign). Primary horizon **k = 7** trading days (matching
`HYP-PM-0002`'s primary horizon for direct comparability across the two I7 tests), with k ∈
{3, 7, 15} reported as robustness.

## 4. Explicit null

**H0:** the signed continuation (§6 measure) at k=7 is ≤ 0 (full or partial reversion, or no
relationship) — i.e., no permanence signature. **H1:** signed continuation at k=7 is **> 0** and
economically material net of cost (§13/§17).

**Assumptions:**

| # | Assumption | Risk if false |
|---|---|---|
| A-PM3.1 | Daily-aggregated signed `lot` (`SUM(lot)`, §6) correctly signs the day's net aggressor direction | mis-signed flow → mechanism untestable (measures noise), not merely weak |
| A-PM3.2 | A 3–15 trading-day horizon separates permanence from later, unrelated information | wrong horizon → permanence aliased by later events |
| A-PM3.3 | `broker_flow`'s daily broker-summary product and `stockbit_flow_bars`'s 1-min-aggregated-to-daily product are sufficiently independent measurements that a positive result on one is not mechanically guaranteed by a positive result on the other | if the two products share upstream computation, this draft and `HYP-PM-0002` are not independent evidence and must be family-adjusted jointly, not treated as two separate multiplicity draws |
| A-PM3.4 | (Deferred, not part of primary spec) an `investor_type='Asing'`-conditioned variant could sharpen the informed/uninformed split, at the cost of a narrower, separately-gated history-maturity question for that specific sub-slice | not tested here; noted only |

## 5. Dataset A binding and exact fingerprint

**Bound dataset:** `DS-broker_flow-idx80-nonpit-2025_2026v1` (Dataset A) — **FROZEN**
([[DECISION_LOG]] D-043, unchanged, unmodified by this draft).

```
provenance_hash: 329b22e49f0ef882b6da031f437e9d87084d2863837ebf8c830de362b7942558
```

Per [[RESEARCH_OBJECT_SCHEMA]] §3.4 Versioning ("Immutable on fingerprint"), this draft, if
registered, binds this **exact** fingerprint. Any future correction to the population is a new
Dataset Object and would require a new hypothesis or a T12 supersession, not a silent rebind.

**Population, exactly as Dataset A's own handoff defines it (not restated, cited):** 79-ticker
IDX80 roster (SHA-256 `7d4eb1004e7d1e83153eede9a5d4e458ab5298ac1a4a4d7fa301f095f665eee0`),
`2025-01-02 → 2026-08-27` inclusive, excluding `2026-08-25`. **NON-PIT** — this draft makes no
historical-index-composition claim; the roster is applied uniformly and retrospectively, per
Dataset A's own stated limitation (`BROKER_FLOW_DATASET_A_EMPIRICAL_READY_HANDOFF_2026-09-09.md`
§5).

## 6. Signed-lot convention

**`SUM(lot)` treated as already-signed net flow, summed directly across both sides, per ticker per
day.** `lot` is empirically signed (BUY predominantly positive, SELL predominantly negative — R-5
receipt). **No additional BUY-minus-SELL subtraction is applied on top of `lot`** — doing so would
double-apply the sign convention (the same pitfall this session's F-4 consumer audit confirmed no
production code currently commits, and the admission draft's own recommended convention). Formally:

```sql
net_flow(ticker, date) = SUM(lot) FROM broker_flow WHERE ticker=? AND trade_date=?
```

`lot = 0 ∧ lot_value > 0` rows (an unresolved [UNRESOLVED] population — 3,700 BUY + 11,963 SELL
rows in Dataset A's exact scope) contribute exactly `0` to this sum regardless of their unexplained
semantics — their ambiguity carries no formula risk for this specification (same finding as F-4).

## 7. Analytical window and OOS/forward partition

**In-sample scope only, per the history-maturity declaration below (§9).** No OOS or forward
partition is defined by this draft. Per [[CUSTODY_MODEL]] §5.3/§5.4, an Out-of-Sample or Blind
partition would be a first-class, separately-registered asset with its own custody state — **none
is created here**, and none should be requested until (a) this draft is registered and (b) the
Owner/CRO separately authorizes an OOS design. The entire `2025-01-02 → 2026-08-27` window, minus
whatever formation/horizon trimming §13 requires at the edges, would be used **in-sample**, matching
`HYP-PM-0001`'s and `HYP-PM-0002`'s own precedent of running in-sample under an open history-
maturity gate rather than being blocked from testing at all.

## 8. History-maturity declaration (reflects D-046/D-047 exactly — declared here, per B-3 precedent)

Per `HYP-PM-0001_DRAFT.md` §11 B-3 (*"gates validation, not registration"*) and this draft's own
obligation to declare the gate at G1 rather than have it discovered at review:

- **Q1 (D-046, Option C):** Dataset A's genuine, vendor-backfilled `2025-01-02 → 2026-08-27` span
  is **eligible** to count toward span-based maturity for regime-stratified/walk-forward purposes.
  It does **not** count toward maturity for forward-observation phenomena (decay estimation) — not
  claimed or attempted here.
- **Q3 (resolved):** `regime_config.yaml::cell.min_n=100` is a trade-level, per-hypothesis/G1
  statistical floor — **this draft does not invoke it as a Dataset-level history requirement.** If
  this hypothesis is registered and executed, `min_n=100` (or a value the CRO ratifies for this
  hypothesis specifically) would apply to **this hypothesis's own realized trade population**, per
  regime cell, exactly as it already governs `HYP-PM-0001`/the NR7 study — not as a pre-condition
  on Dataset A itself.
- **N (D-047):** **no numeric threshold is invented here.** D-047 defers the Dataset/Program-level
  `N` question to a future Program-level PG-A assessment (for whichever Program that turns out to
  be relevant to) — not to this hypothesis draft, and this draft does not attempt to answer it.
- **Regime evidence available, not claimed as sufficiency:** D-042 found all three
  `PRIMARY_REGIMES` classes present in Dataset A's window (SIDEWAYS 61.6%, BEAR 26.5%, BULL 11.9%)
  — contrasting with `HYP-PM-0001`'s disqualifying single-regime state on a different dataset. This
  is **evidence available to cite**, not a completed maturity ruling (D-047 is explicit that
  multi-regime presence establishes only non-disqualification, not sufficiency).
- **Explicit declared scope (§9's operative rule):** **this draft, if registered, would be
  IN-SAMPLE, SINGLE-PASS ONLY, with regime-stratified and walk-forward VALIDATION explicitly
  deferred** — mirroring `HYP-PM-0001`'s and `HYP-PM-0002`'s own history-maturity gate treatment.
  It does **not** claim Dataset A is "mature" and does **not** request or assume regime-stratified
  validation is authorized.

## 9. Regime/walk-forward claims vs. decay claims — explicit distinction

- **This draft makes NO regime-stratified claim** (no claim that the effect differs by BULL/BEAR/
  SIDEWAYS cell) and **NO walk-forward claim** (no claim of out-of-time generalization). Both
  remain deferred by the history-maturity gate (§8).
- **This draft makes NO decay claim.** LIM7 (*"decay is detectable only in arrears"*) and D-046's
  explicit carve-out (backfilled span does not advance decay maturity) both apply; no half-life or
  decay-hypothesis field is populated (contrast with O9 Accepted Knowledge Object's
  `decay_hypothesis`, which does not apply — this is a G1 draft, not a promoted claim).
- **What this draft DOES claim, if registered:** a single, pre-registered, in-sample,
  non-regime-stratified test of I7 permanence at k=7 (primary), reported with the k∈{3,7,15}
  robustness set, exactly as narrow as `HYP-PM-0002`'s own scope.

## 10. Required data

`broker_flow` (Dataset A, §5) — the only data this draft binds. `ohlcv` (for formation-day and
post-formation returns; already 5-year, DECLARED-equivalent depth per `DATA_FEASIBILITY_STUDY` §3,
not itself a maturity concern). No other table is required by the primary specification.

## 11. Sample / population definition

One observation = one **(ticker, formation date)** pair where `net_flow(ticker, date) ≠ 0` (per §6),
drawn from Dataset A's exact population (79 tickers × 388 dates, minus whatever trailing-k-day
trim §13 requires at the window's right edge to have a complete forward return). This is a
**cross-sectional daily panel**, not a per-trade backtest population — a structurally different unit
of observation from `HYP-PM-0001`'s intraday-trade panel and closer in spirit to `HYP-PM-0002`'s
daily formation-day panel (which drew from `stockbit_flow_bars` daily aggregates, not
`broker_flow`).

## 12. Statistical test

**CRO-adopted (2026-09-09), per `HYP-PM-0003_POWER.md` §2:** `research/statistics.py::bootstrap_ci`
— the same mechanism `cell_verdict`/gatekeeper/NR7 already use, reused rather than invented. **No
new clustered-inference (ticker × time) code is implemented before G1** — `research/statistics.py`
contains no such implementation anywhere in this repository, and building one is deferred as a
future robustness extension, not a registration prerequisite. `HYP-PM-0003_POWER.md` §5 records
that `bootstrap_ci` does not itself model the identified cross-sectional/serial dependence; the
`HYP-PM-0001` deflation ladder is adopted alongside it as a labeled sensitivity diagnostic only.

## 13. Power / MDE

**`HYP-PM-0001`'s numerical MDE remains NOT inherited** — the panel size, return volatility, and
clustering structure of a **daily broker-flow** signal are materially different from `HYP-PM-0001`'s
1-minute intraday signal (N=12.7M bars). `HYP-PM-0003_POWER.md` computed this hypothesis's own
structural inputs instead: **20,604 nonzero-net-flow (ticker, date) observations**, k=7
forward-return **σ=8.623%** (price-only, no flow-return relationship touched).

**CRO-adopted (2026-09-09), per `HYP-PM-0003_POWER.md` §6:** the ex-ante criterion is
**friction-anchored** — net-of-cost signed continuation at k=7 must be **> 0**, i.e. gross must
clear the canonical **0.60%** round-trip floor (§16 below) — matching `HYP-PM-0002`'s own
friction-anchored convention. This was **not** chosen to make the statistically-derived MDE range
(0.168%–1.684% across the deflation ladder, `HYP-PM-0003_POWER.md` §8) "pass" — that range is
retained as a reported sensitivity figure, and the observed tension (this daily panel's power may be
a binding constraint, unlike `HYP-PM-0001`'s friction-only binding case) is preserved, not resolved
by discarding either number.

## 14. Multiplicity family

P-M {I5, I6, I7, I12} (D-028), append-only and monotonic (PG-3/OS-10). If registered, this draft
becomes the family's **third** member, independently counted — it does not narrow, reinterpret, or
consume any slot `HYP-PM-0001` or `HYP-PM-0002` occupies (`HYP-PM-0002` remains unregistered and
consumes no slot until its own separate G1 act).

> **CRO-ADOPTED (2026-09-09) — Option B, independent counting.** Basis: **OS-10**
> (`RESEARCH_OBJECT_SCHEMA.md` §4.5) — *"every hypothesis registered under a Program joins its
> family; no hypothesis leaves."* This is a **CRO interpretation of that existing, general counting
> rule**, not a new corpus rule. **Pipeline separation is not the governing criterion** —
> `RESEARCH_PROGRAM_PLAYBOOK.md` §1.2's CONFOUNDS/SUBSUMES-UPSTREAM/MODIFIES test is a
> taxonomy-entry/family-drawing mechanism, evaluated once before any hypothesis exists (P-M's family
> is already fixed, D-028); it is not re-applied to compare hypothesis instances within an
> already-declared family. `HYP-PM-0002` and `HYP-PM-0003` (both I7/M2.1) therefore each count as
> their own independent family member under OS-10, exactly as every other precedent in this corpus
> does (P0/NR7, `HYP-PM-0001`, `HYP-PM-0002` itself, HL-4's "new registration: new G1, new family
> count" route).
>
> **Preserved caveat — scientific/evidential, not a multiplicity blocker:** A-PM3.3's provenance
> investigation established that `stockbit_flow_bars` (`HYP-PM-0002`) and `broker_flow` /
> Dataset A (`HYP-PM-0003`) are genuinely separate Stockbit API products with no shared endpoint,
> fetch function, or repository-side computation — but **both describe the same underlying executed
> IDX trades**, and repository evidence cannot establish or rule out vendor-internal independence.
> **This is an unresolved limitation on the evidential independence of the two hypotheses' eventual
> results, not a lever the corpus's denominator-counting mechanism (OS-10) responds to.** Any future
> joint interpretation of both results as fully independent confirmations/refutations of I7 should
> be read against this caveat.

## 15. Refutation / failure condition (one sentence, R14)

*If the net-of-cost signed continuation of daily broker-flow-implied price displacement at k=7
trading days is not significantly positive (double-clustered CI does not exclude zero, or the
point estimate does not clear the 0.60% round-trip friction floor), M2.1's permanence prediction is
refuted for this data source and horizon, and I5's reversion reading (already null on
`stockbit_flow_bars` at intraday horizon per HYP-PM-0001) gains no support from this test either —
both remain open at horizons/data sources not yet examined.*

## 16. Friction / cost model (this hypothesis makes a net-of-cost claim)

**Cost authority:** `engine/exits/costs.py` — `COMMISSION_BUY 0.0015` (0.15%) + `SLIPPAGE 0.001`
(0.10%) on the buy leg, `COMMISSION_SELL 0.0025` (0.25%) + `SLIPPAGE 0.001` (0.10%) on the sell leg
= **0.60% round-trip**. **Reused, not re-derived** — this is the single, repository-wide cost
authority `HYP-PM-0001`, `HYP-PA-0001`, and `HYP-PM-0002` all cite identically; it is a fixed
repository constant, not a hypothesis-specific parameter, so reusing it does not fall under the
"do not inherit HYP-PM-0001's hypothesis-specific parameters" instruction (which concerns MDE/k/
mechanism-specific numbers, not the shared cost-model constant every P-M/P-A item cites).
**Ex-ante criterion:** net-of-cost signed continuation at k=7 must be **> 0**, i.e. gross signed
continuation must clear 0.60% — matching `HYP-PM-0002`'s own friction-anchored (not
statistically-derived) MDE convention.

## 17. Custody / provenance requirements

- **Dataset fingerprint** (§5): bound, immutable per O4 Versioning.
- **Experiment provenance (O6, if registered and executed):** `run_id`, `git_commit`, `seed`,
  `environment` — the X2 minimum set ([[RESEARCH_OBJECT_SCHEMA]] §7.2) — none exist yet; no
  experiment has been designed or executed by this draft.
- **Custody asset-state:** per D-036 (orthogonal axes) and this session's ROM v2.0 §3.2 finding
  ("Dataset | C-FROZEN-ON-USE | Frozen on fingerprint"), Dataset A's custody asset-state already
  entered its frozen condition at FINGERPRINTED (D-041) — no further custody action is required to
  *read* Dataset A for this draft's design work. Any future OOS/Blind partition (§7, not created
  here) would be a separately custodied asset under CUSTODY_MODEL §5.3 if one is ever authorized.
- **Provenance elements per O4 §3.4:** vendor (Stockbit broker summary), transformation lineage,
  and `point_in_time` construction argument are all already established in Dataset A's own handoff
  (§8, §10, §12 there) and are cited, not restated.

## 18. G1 / CRO approval fields required by existing governance

Per [[RESEARCH_OBJECT_SCHEMA]] §3.3 (O3 Hypothesis) and `HYP-PM-0001_DRAFT.md`'s own G1 checklist
pattern:

| Field | Status here |
|---|---|
| Mechanism (§1), sign-specified prediction (§3), null (§4), refutation condition (§15) | ✅ populated above |
| `scope` (universe, horizon, regime, period) | ✅ Dataset A population + k∈{3,7,15} + in-sample only, no regime split (§8–§9) |
| `effect_size_floor` (ex-ante criterion incl. cost) | ✅ friction floor **CRO-adopted 2026-09-09** (§13, §16) |
| `multiplicity_family` | ✅ P-M {I5,I6,I7,I12}, third independently-counted member if registered (§14) — **CRO-adopted, Option B, OS-10** |
| `custody_state` | Discovery — no OOS/Confirmation partition exists (§7, §17) |
| `oos_period` / `oos_opened_at` | **N/A — not defined** (§7); a prerequisite if this draft is later extended to claim OOS/forward evidence |
| `power_analysis` / `mde` | ✅ **CRO-adopted 2026-09-09** — `bootstrap_ci` test (§12), friction-anchored MDE (§13), α=0.05/power=0.80 (`HYP-PM-0003_POWER.md` §7) |
| `retirement_rule` | Not applicable pre-registration (O9-level field; this is a G1 draft, not an Accepted Knowledge Object) |
| CRO approval | **All methodological items now adopted.** Overall `DRAFT → REGISTERED` (T4/G1) authorization is a separate, explicit act not performed by this document |

---

## A. Which existing hypothesis mechanism should be developed?

**Neither HYP-PM-0002 as-is, nor a broadened family — a new candidate (this draft, HYP-PM-0003),
reusing I7/M2.1 but bound to Dataset A specifically.** Evidence: `HYP-PM-0002_DRAFT.md` is built on
`stockbit_flow_bars`, not `broker_flow` — it does not bind Dataset A at all, and its own §0
explicitly declined to use `broker_flow`'s `investor_type` data for a reason (short history at the
time) that Dataset A's governance work has since addressed for the aggregate population (D-046).
Developing HYP-PM-0002 further would not use Dataset A; drafting a new I7 instance against Dataset A
directly is the task's actual request, and does not broaden the family (I7 is already in it) or
create a new Program.

## B. Complete proposed hypothesis draft

`docs/research_programs/P-M/HYP-PM-0003_DRAFT.md` — reproduced in full above (§0–§18).

## C. Every field that remains unresolved, and why (updated 2026-09-09 — see `HYP-PM-0003_POWER.md`)

| Field | Status |
|---|---|
| Exact statistical test (§12) | ✅ **CRO-adopted** — `bootstrap_ci` |
| Power / MDE (§13) | ✅ **CRO-adopted** — friction-anchored, 0.60% floor |
| Alpha / power target | ✅ **CRO-adopted** — α=0.05, power=0.80 |
| Dependence treatment | ✅ **CRO-adopted, as a labeled sensitivity diagnostic only** — the deflation ladder, not a formal correction; `bootstrap_ci` does not model the dependence |
| `investor_type`-conditioned variant (A-PM3.4) | Still deliberately deferred — narrower data slice, its own separate maturity question, not part of the primary claim |
| **Independence of this draft from `HYP-PM-0002` (A-PM3.3 / §14)** | ✅ **CRO-adopted 2026-09-09** — Option B, independent counting (OS-10); observation-dependence caveat preserved as an evidential limitation, not a multiplicity blocker |
| OOS/forward partition (§7) | Not designed — no custody asset created; a future, separately-authorized step if this draft proceeds toward any out-of-sample claim |

## D. Exact G1 blockers (updated 2026-09-09)

**None methodological.** The multiplicity ruling (§14) is now CRO-adopted, joining §12/§13/alpha-power/
dependence treatment as complete. **No blocker from Dataset A's governance state** —
DECLARED/FINGERPRINTED/FROZEN are all satisfied (D-040/D-041/D-043); the history-maturity gate
remains correctly declared open and deferred (§8), not treated as resolved or as a registration
blocker (per B-3 precedent). The remaining step is the separate, explicit `DRAFT → REGISTERED`
(T4/G1) authorization act — not performed by this document.

## E. Recommended next action

The G1 methodology package is complete. The next act, if the CRO/Owner chooses to proceed, is an
explicit registration authorization. **No such request is made here; no registration is
performed.**

---

**Nothing in this document registers a hypothesis, consumes a family slot, runs an empirical test,
modifies Dataset A, or edits `DECISION_LOG.md`/`HYPOTHESIS_REGISTRY.md`.**
