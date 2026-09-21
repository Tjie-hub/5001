# HYP-PM-0003 · Power / Methodology Analysis (pre-registration)

> **Purpose:** fix candidate design parameters and identify what remains CRO-open for
> [[HYP-PM-0003_DRAFT]]. **Pre-registration preparation, not experiment execution** — uses only
> structural counts and price-series volatility computed from `ohlcv`/`broker_flow` schema, never
> the relationship between signed net flow and forward return. **That relationship was NOT
> computed and stays sealed until the test runs post-registration under custody.**

**Date:** 2026-09-09 · **Inputs:** Dataset A (`DS-broker_flow-idx80-nonpit-2025_2026v1`,
`provenance_hash 329b22e49f0ef882b6da031f437e9d87084d2863837ebf8c830de362b7942558`, FROZEN D-043) +
`ohlcv` (price-only, for the volatility nuisance parameter) · **Status:** structural inputs
computed; test selection, MDE, and alpha/power target **remain CRO-open**.

---

## 1. Primary estimand

The **net-of-cost, sign-specified continuation of price displacement conditional on the sign of
daily aggregate broker-flow (`SUM(lot)`) at formation, measured over the following k=7 trading
days**, pooled across Dataset A's 79-ticker roster and full window — i.e., the M2.1/I7 permanence
signature `HYP-PM-0003_DRAFT.md` §3–§4 specifies. This is a single scalar estimand at the primary
horizon; k∈{3,15} are reported as robustness, not separate primary estimands.

## 2. Statistical test

**Investigated ambiguity, reported rather than silently resolved:** `HYP-PM-0001_DRAFT.md`/
`HYP-PM-0002_DRAFT.md` both *recommend* double-clustered (ticker × time) inference, but
**`research/statistics.py` — the only statistics module in this repository — implements exactly
two tests: `bootstrap_ci` (used by `cell_verdict`, the gatekeeper, and the NR7 study) and
`t_test_greater` (a simple one-sided mean test).** No clustered-standard-error or panel-regression
implementation exists anywhere in the codebase. **The "double-clustered" design both prior P-M
drafts recommend is aspirational — not an existing, reusable authority — and adopting it here would
require writing new statistical code, not reusing existing corpus machinery.**

**Narrowest defensible primary test from what actually exists:** `bootstrap_ci` on the pooled k=7
signed-continuation sample (matching `cell_verdict`'s exact method: `n_boot`, `ci_level`, `seed`
from `regime_config.yaml`'s already-versioned config, reused rather than reinvented), verdict rule
identical to `cell_verdict`'s PRESENT/ABSENT/REVERSED logic (§`research/regime/profile.py:25-43`).

> **CRO-ADOPTED (2026-09-09):** **Option A — `bootstrap_ci`.** No new clustered-inference code is
> implemented before G1. Clustered inference (ticker × time) is recorded as a **future robustness
> extension**, not a registration prerequisite — it may be added later without altering this
> hypothesis's primary test, per O5 Feature/O6 Experiment's own branch-on-upstream-change
> discipline should it ever be built. This does not resolve §5's dependence concern; it is
> addressed there as a diagnostic, not by this test choice.

## 3. Null and alternative

- **H0:** net-of-cost signed continuation at k=7 ≤ 0 (full/partial reversion, or no relationship).
- **H1 (directional, fixed here, no post-hoc switching permitted):** net-of-cost signed
  continuation at k=7 **> 0**.

Identical to `HYP-PM-0003_DRAFT.md` §4 — restated, not altered.

## 4. Unit of analysis

**Unit = (ticker, formation-date) pair** — a cross-sectional daily panel observation, **not** a
trade, not a broker-day, not an executed position. This is deliberately distinguished from three
other quantities that must not be conflated with it:

- **`min_n=100`** is a *trade-level* per-hypothesis/G1 floor (Q3, resolved) — **not borrowed here**
  as a Dataset-level or panel-level quantity. If this hypothesis is registered and a regime-cell
  bootstrap verdict is later computed (§2), `min_n` would apply to the count of (ticker, date)
  panel observations **within each regime cell** at that time — not to Dataset A's raw row count.
- **Dataset A's raw `broker_flow` rows** (1,222,713, at the `(ticker, trade_date, broker_code,
  side)` grain) are **not** the unit of analysis — they are aggregated via `SUM(lot)` (§6 of the
  draft) into one net-flow figure per (ticker, date) before any test is run.
- **The 30,652-cell expected grid** (79 tickers × 388 dates, F-2 receipt) is the *maximum possible*
  panel size, not the actual sample — see §8.

## 5. Dependence

**Two concerns, neither resolved here:**
1. **Cross-sectional clustering** — 79 tickers observed on the same calendar dates share
   common-day shocks (index-level moves, macro news). `bootstrap_ci`'s default resampling (i.i.d.
   over the pooled sample) does not account for this; a block/cluster bootstrap or explicit
   day-clustering would be more conservative.
2. **Serial dependence within a ticker** — overlapping k=7 forward windows for the same ticker are
   autocorrelated by construction (day *t*'s window overlaps day *t+1*'s window for 6 of 7 days).
   `HYP-PM-0001_POWER.md`'s own deflation ladder (÷100, ÷1000 "effective N") is the only precedent
   in this program for handling this, and it is explicitly a **sanity-check heuristic**, not a
   rigorous correction.

> **CRO-ADOPTED (2026-09-09):** the `HYP-PM-0001` deflation ladder (N, N/10, N/100) is adopted as a
> **sensitivity diagnostic** — reported alongside the primary `bootstrap_ci` result to show how the
> conclusion moves under progressively harsher assumed effective-sample-size deflation.
> **Explicitly labeled: this is a heuristic sensitivity analysis, NOT a formal dependence
> correction.** `bootstrap_ci` itself performs i.i.d. resampling over the pooled sample and **does
> not model either dependence source identified above** (cross-sectional same-day clustering, or
> serial overlap in the k=7 forward window). The deflation ladder does not fix this — it only shows
> how sensitive the naive result is to an assumed reduction in effective N. A genuine correction
> (block bootstrap, explicit clustering) remains unbuilt (§2) and is not adopted by this entry.

## 6. MDE

**Definition for this hypothesis:** the smallest net-of-cost k=7 signed continuation that the
chosen test (§2) can detect at the target alpha/power (§7), given the sample actually available.

**`HYP-PM-0001`'s MDE is explicitly NOT inherited.** That figure (0.023–0.712 bps, per-bar) was
derived from a 12.7-million-row **1-minute** panel with 1-minute return volatility — a structurally
different instrument (intraday, high-frequency) from this hypothesis's **daily, k=7-trading-day**
panel. Reusing that number would misstate this test's actual detectable effect size by orders of
magnitude.

**No arbitrary effect size is invented either.** Per §8, a *naive, order-of-magnitude-only*
sanity-check figure is computed from structural inputs (matching `HYP-PM-0001_POWER.md`'s own
"approximate power sanity check" framing) — it is not proposed as the registered MDE.

> **CRO-ADOPTED (2026-09-09): Option A — friction-anchored.** The ex-ante criterion is net-of-cost
> signed continuation at k=7 **> 0**, i.e. gross signed continuation must clear the canonical
> **0.60%** round-trip floor (`engine/exits/costs.py`, §10 — verified, not re-derived). This is
> **not** chosen to make any statistical power calculation "pass" — §8's naive statistically-derived
> MDE range (0.168%–1.684% across the deflation ladder) is retained in this document as a reported
> sensitivity figure, not as the registered criterion, and the tension between the two is preserved
> below rather than resolved by discarding one number in favor of the other.

## 7. Alpha / power

**No canonical corpus-wide alpha/power precedent exists beyond what `HYP-PM-0001_POWER.md` used
for its own sanity check: two-sided α=0.05, power=0.80** — this is the closest thing to a
repository convention (also implicit in `bootstrap_ci`'s default `ci_level=0.95` in
`regime_config.yaml`, i.e. α=0.05 one-sided-equivalent). **Reused as a candidate, not established as
binding:** no document states these values are mandatory for every P-M hypothesis; they are simply
what the one prior precedent used.

> **CRO-ADOPTED (2026-09-09):** two-sided **α=0.05**, target **power=0.80**, recorded as
> **`HYP-PM-0003`'s own ex-ante convention** — justified by, but not binding on, the rest of the
> corpus. This is not a claim that any other future P-M/P-A hypothesis must use these values; each
> makes its own ex-ante choice, citing precedent or not, per R5.

## 8. Sample-size / feasibility calculation (structural only — no outcome computed)

**Computed, read-only, from Dataset A's frozen structure and `ohlcv` price series alone — the
flow-return relationship itself was never touched:**

```
Maximum structural grid (F-2 receipt, unchanged):        30,652  (ticker,date) cells
(ticker,date) pairs with SUM(lot) != 0 (real, nonzero
  net-flow observations — a schema/coverage count):      20,604
k=7 forward-return sample, price-only, all 79 tickers,
  pooled (2025-01-02 -> 2026-08-27):                      30,020 observations
k=7 forward-return sigma (price-only, pooled), sigma:      8.623 %
```

**Distinguishing structural capacity from realized hypothesis-trade count:** 30,652 is the
*theoretical maximum* if every cell were used regardless of signal; 20,604 is the actual count of
panel observations with a nonzero signed-flow signal to condition on — this is the more realistic
upper bound on **N** for this hypothesis's test, still **before** any dependence deflation (§5) or
regime-cell splitting is applied.

**Naive sanity-check MDE (order-of-magnitude only — mirrors `HYP-PM-0001_POWER.md`'s own caveat;
NOT the registered criterion, NOT derived from any flow-return computation):**

```
MDE = 2.802 * sigma / sqrt(N_eff)      (two-sided alpha=0.05, power=0.80 — candidate, §7)

N_eff = 20,604 (raw, no dependence correction):        MDE ~ 0.168%
N_eff =  2,060 (/10  -- mild clustering deflation):    MDE ~ 0.533%
N_eff =    206 (/100 -- HYP-PM-0001's own deflation):  MDE ~ 1.684%
```

**Interpretation, stated carefully:** unlike `HYP-PM-0001` (where even aggressive deflation left
the statistical MDE far below the 0.60% friction floor — power was "abundant," friction was the
binding constraint), **this daily panel's naive MDE crosses the 0.60% friction floor somewhere
between the raw and ÷100-deflated N_eff** — meaning **statistical power, not only friction, may be
a real, binding constraint for this design**, unlike the prior P-M item. This is a structural
observation about sample size and volatility, not a claim about whether any effect exists.

## 9. Multiplicity

**Family: P-M {I5, I6, I7, I12}** (D-028), unchanged, not broadened by this document. If
registered, `HYP-PM-0003` joins as an independently-counted third member (§14 of the draft).

**Variants/subgroups:** the primary specification is the pooled, all-investor-type test (§0.2 of
the draft). If a future CRO-approved extension adds the `investor_type='Asing'`-conditioned variant
(A-PM3.4, explicitly out of primary scope), **that variant must be counted as an additional family
member/multiplicity draw when and if it is ever registered — not folded silently into this
hypothesis's single test.** `investor_type` remains out of primary scope here, exactly as the draft
specifies.

**Independence from `HYP-PM-0002`:** flagged, not resolved (A-PM3.3 of the draft) — whether this
test and `HYP-PM-0002`'s (same I7 entry, different data source) are independent draws or require
joint family-adjustment is an open methodological question, not decided by this document.

> **CRO-ADOPTED (2026-09-09) — Option B, independent counting.** Basis: **OS-10**
> (`RESEARCH_OBJECT_SCHEMA.md` §4.5) — *"every hypothesis registered under a Program joins its
> family; no hypothesis leaves."* A **CRO interpretation of this existing, general rule**, not a new
> corpus rule. **Pipeline separation is not treated as the governing multiplicity criterion** — the
> Playbook §1.2 CONFOUNDS/SUBSUMES-UPSTREAM/MODIFIES test is a taxonomy-entry/family-drawing
> mechanism (evaluated once, before any hypothesis exists; P-M's family is already fixed, D-028) and
> is not re-applied to compare hypothesis instances within an already-declared family. `HYP-PM-0002`
> and `HYP-PM-0003` therefore each count independently under OS-10, matching every precedent this
> investigation found.
>
> **Preserved caveat — scientific/evidential, not a multiplicity blocker:** A-PM3.3 established
> `stockbit_flow_bars` and `broker_flow` are genuinely separate Stockbit API products (no shared
> endpoint, fetch function, or repository-side computation) but **both describe the same underlying
> executed IDX trades** — vendor-internal independence cannot be established or ruled out from
> repository evidence. This bears on the **evidential weight/independence of the two hypotheses'
> eventual results**, not on how the family denominator is counted under OS-10.

## 10. Cost / friction

**Cost authority verified at source, `engine/exits/costs.py`:**
```
COMMISSION_BUY  = 0.0015   (0.15%)
COMMISSION_SELL = 0.0025   (0.25%)
SLIPPAGE        = 0.001    (0.10%, applied each leg)
Round-trip = (0.15%+0.10%) + (0.25%+0.10%) = 0.60%
```
**This is the single, repository-wide, already-established cost authority** — identically cited by
`HYP-PM-0001`, `HYP-PA-0001`, and `HYP-PM-0002`. Reused verbatim here (not re-derived, not a
hypothesis-specific invention) because it is a fixed constant every P-M/P-A item already shares.
**No net-of-cost claim is made anywhere in this document without this authority** — §8's MDE
comparison and §6's ex-ante criterion both reference it explicitly.

## 11. History maturity

Restated exactly as `HYP-PM-0003_DRAFT.md` §8 declares — not re-litigated here:

- **D-046 (Q1=C):** Dataset A's genuine backfilled span (`2025-01-02 → 2026-08-27`) is **eligible**
  for regime-stratified/walk-forward span-based purposes. It does **not** count toward maturity for
  decay estimation, which remains subject to genuinely-elapsed future observation.
- **D-047:** no numeric `N` exists or is invented by this document. Maturity is **not pre-cleared**
  by Dataset A's span, D-042's regime characterization, or anything computed in this power document
  — §8's structural counts and volatility figure are sample-size inputs, not a maturity ruling.
- **Q3 (resolved):** `min_n=100` remains a trade-level/per-hypothesis/G1 floor, not invoked here as
  a Dataset-level requirement (§4).

## 12. Refutation condition (ex ante, mechanically testable)

*If the chosen test (§2, CRO-selected) does not find the net-of-cost k=7 signed continuation
significantly positive at the CRO-ratified alpha (§7) — i.e., the confidence interval does not
exclude zero net-of-cost, or the point estimate does not clear the 0.60% round-trip friction floor
(§10) — M2.1's permanence prediction is refuted for this data source and horizon.* Identical in
structure to `HYP-PM-0003_DRAFT.md` §15 — restated for completeness, not altered.

## 13. G1 readiness matrix

| Field | READY / OPEN / BLOCKED | Exact reason |
|---|---|---|
| Primary estimand (§1) | **READY** | Fully specified, matches the draft |
| Statistical test (§2) | **READY (ADOPTED)** | CRO-adopted 2026-09-09: `bootstrap_ci` (Option A); clustered inference deferred as future robustness extension, not built |
| Null/alternative (§3) | **READY** | Directional, fixed, matches the draft |
| Unit of analysis (§4) | **READY** | Defined and distinguished from `min_n`, raw rows, and the expected grid |
| Dependence treatment (§5) | **READY (ADOPTED, as diagnostic only)** | CRO-adopted 2026-09-09: `HYP-PM-0001` deflation ladder as a labeled sensitivity heuristic, not a formal correction; `bootstrap_ci` does not model the dependence — stated explicitly, not concealed |
| MDE (§6) | **READY (ADOPTED)** | CRO-adopted 2026-09-09: friction-anchored (Option A), 0.60% round-trip floor; statistical MDE range retained as a reported, not adopted, sensitivity figure |
| Alpha / power (§7) | **READY (ADOPTED)** | CRO-adopted 2026-09-09: α=0.05 two-sided, power=0.80, as `HYP-PM-0003`'s own ex-ante convention |
| Sample-size / feasibility (§8) | **READY** (structural input) | 20,604 nonzero-flow observations, σ=8.623% (k=7, price-only) computed |
| Multiplicity (§9) | **READY (ADOPTED)** | CRO-adopted 2026-09-09: Option B, independent counting under OS-10; observation-dependence caveat vs. `HYP-PM-0002` preserved as an evidential limitation, not a blocker |
| Cost/friction (§10) | **READY** | Verified against source; single repo-wide authority, no invention |
| History maturity (§11) | **READY** | D-046/D-047 correctly reflected; no threshold invented, no pre-clearance claimed |
| Refutation condition (§12) | **READY** | Ex ante, mechanically checkable — all inputs it depends on (§2/§6/§7) are now adopted |
| CRO approval overall | **All methodological items ADOPTED** | No open methodological item remains; overall `DRAFT → REGISTERED` (T4/G1) authorization is a separate, explicit act not performed by this document |

---

## A. Exact file created

`docs/research_programs/P-M/HYP-PM-0003_POWER.md` (this document).

## B. Methodology summary — CRO-ADOPTED, 2026-09-09

**Primary test:** `bootstrap_ci` (Option A) — reuses the gatekeeper/regime/NR7 convention; no new
clustered-inference code implemented before G1; clustered inference recorded as a future robustness
extension. **Dependence:** the `HYP-PM-0001` deflation ladder adopted as a labeled sensitivity
diagnostic only — explicitly not a formal correction, and `bootstrap_ci` explicitly does not model
either dependence source identified. **MDE:** friction-anchored (Option A), the canonical 0.60%
round-trip floor (`engine/exits/costs.py`) — not chosen to make the statistical power range "pass";
the 0.168%–1.684% statistically-derived range remains reported as a sensitivity figure, not the
criterion. **Alpha/power:** α=0.05 two-sided, power=0.80, recorded as this hypothesis's own ex-ante
convention (precedent-supported, not corpus-mandated). **Multiplicity: CRO-adopted, Option B**
(independent counting under OS-10) — the observation-dependence caveat vs. `HYP-PM-0002` is
preserved as a stated evidential limitation, not a multiplicity blocker.

## C. Unresolved CRO decisions

**None remaining.** All five items from the original list are now CRO-adopted.

## D. G1 blockers after this document

**None methodological.** All G1 methodology fields are READY/ADOPTED (§13). The remaining step is
the separate, explicit `DRAFT → REGISTERED` (T4/G1) authorization act itself — not performed by this
document.

## E. Recommended next action

The methodology package is complete. The next act, if the CRO/Owner chooses to proceed, is an
explicit registration authorization — **not requested or performed here.**

---

**Nothing in this document registers a hypothesis, computes the flow-return relationship, modifies
Dataset A, edits `HYPOTHESIS_REGISTRY.md`/`DECISION_LOG.md`, or runs any backtest.**
