# HYP-PM-0002 — Adverse-Selection Permanence at Swing Horizon (DRAFT)

> **Status: DRAFT — held at G1. NOT registered. No family slot consumed.**
> Free-era candidate ([[HYPOTHESIS_LIFECYCLE]] §2–§3): refine freely; nothing risked until the
> irreversible `DRAFT → REGISTERED` (T4/G1). **This draft was prepared without inspecting any
> return, reversal, or continuation outcome** — every number below (dates, ticker counts, cost
> constants) comes from schema/coverage inspection or the pre-existing frozen cost authority, never
> from computing OFI-vs-return statistics. Registration requires explicit CRO/owner sign-off and is
> **not performed by this document**.

**Program:** P-M · Microstructure Flow · **Family:** P-M {I5, I6, I7, I12} ([[DECISION_LOG]] D-028)
— this would be the **second member** (first: [[HYP-PM-0001_REGISTERED]], FAILED F2, 2026-07-18)
**Mechanism (I7 = M2.1):** signed order-flow imbalance → adverse-selection premium → **permanence
(non-reversion)**
**Date drafted:** 2026-08-20 · **Supersedes nothing** (new mechanism, not a T12 revision of
HYP-PM-0001 — see §2 lineage)

---

## 0. Why this hypothesis, and why not generic momentum

`FAILURE_ENTRY.md` for HYP-PM-0001 (`FAIL-PM-0001`, dated 2026-07-18 — before this draft existed)
states explicitly under `lessons_learned`: *"Future P-M work should either (a) test M2.1
adverse-selection **permanence** (I7) as the competing read, or (b) await higher-fidelity (LOB)
flow."* This draft executes path (a). The mechanism was named by the institution's own prior
failure analysis, not authored after looking at any result for this hypothesis (§7.3/OS-6 blind
requirement — see §9).

**Explicitly not attempted:** generic cross-sectional price momentum. Its natural mechanisms in
this institution's taxonomy are **I10 (limited-attention mispricing)** and **I11
(disposition-driven adjustment drag)** — both RM0/Conjectured, both explicitly flagged in
`MARKET_INEFFICIENCY_TAXONOMY.md` as the taxonomy's weakest entries, and **neither is in an open
program family** (P4 blocked on LIM4, P5/P6 not initiated). I6 (illiquidity premium) is a
cross-sectional *level* effect (compensation for trading cost), not a continuation effect, and is
not stretched to cover momentum here. The taxonomy itself is unchanged — this hypothesis uses only
the already-declared I7/M2.1 entry, exactly as defined in `ECONOMIC_MECHANISM_TAXONOMY.md` §3.

## 1. Mechanism

**Class: M2.1 · Adverse-selection spread component** ([[ECONOMIC_MECHANISM_TAXONOMY]] §3, verbatim
definition): *"A supplier who cannot distinguish informed from uninformed counterparties embeds an
expected-loss premium in every quote, so that transaction prices move permanently in the direction
of executed flow."* Causal chain: informed participants exist and are unidentifiable → supplier
widens quotes to cover expected loss → informed trade selectively against stale quotes → price
incorporates the information → **permanent, non-reverting component of price change conditional on
signed flow**.

- **Participant class:** liquidity suppliers (uninformed by role) versus informed traders
  (fundamental/order-flow-informed; not further sub-classified — no participant-class proxy beyond
  the signed-flow aggregate itself is used, see §4 A-PM2.1).
- **Constraint:** the supplier cannot distinguish informed from uninformed flow (information
  asymmetry, D2).

## 2. Inefficiency family, identification problem, and lineage to HYP-PM-0001

- **Primary entry: I7 · Adverse-selection premium** (M2/D2, [[MARKET_INEFFICIENCY_TAXONOMY]] I7).
- **Same I5↔I7 confound HYP-PM-0001 declared, opposite read.** HYP-PM-0001 registered M1.1 (I5,
  reversion) as primary, tested against M2.1 (I7, permanence) as the competing explanation, and
  found *no significant reversion* at 1-minute/k∈{5,15,30}-minute horizon (signed reversal
  ≈ −0.0008%/trade, t=−0.35, sign-inconsistent across k). **A null on reversion at microstructure
  horizon does not confirm permanence at swing horizon** — it is a different mechanism-test at a
  different horizon, on different (aggregated) data, and this draft treats it as fully independent,
  not as evidence for I7. HYP-PM-0002 is a **new G1 registration**, not a T12 supersession of
  HYP-PM-0001 (the mechanism class differs: M2.1 vs M1.1), and per PG-3/OS-10 it joins the P-M
  family as a second, independently-counted member.
- **I6 and I12** remain modifiers only (liquidity/capacity conditioning of the permanence
  magnitude), not competing mechanisms — same role they played in HYP-PM-0001.

## 3. Structural barrier & prediction

**Barrier (persistence):** information asymmetry itself. Per M2.1's falsification criteria, this
barrier cannot be arbitraged away — removing it would require the supplier to know what the
informed trader knows, at which point there is no asymmetry and no premium ([[MARKET_INEFFICIENCY_TAXONOMY]]
I7, "Persistence hypothesis").

**Prediction (sign-specified):** price displacement conditional on a signed daily order-flow
imbalance on formation day *t* **does not revert** — a nonzero fraction of the displacement
persists — over the following *k* **trading days** (k ∈ {3,7,15}, primary k=7). Positive OFI →
positive contemporaneous/near-term return → subsequent return **continues in the same direction**
(does not reverse sign). The **signed continuation** (defined in §6) is **> 0**.

### 3.1 Observable implications
1. Price change over the formation window correlates with signed OFI (displacement).
2. The displacement does **not** fully revert over the following k trading days (I7 signature) —
   discriminated against I5's opposite prediction (full/partial reversion).
3. Permanence should **not** vary mechanically with illiquidity alone (I6 is a magnitude modifier
   of *either* reading — I5 or I7 — and does not by itself discriminate them; only the sign/decay
   of the post-formation return does, per §2).
4. No participant-class flow-labeling is attempted this round (see A-PM2.1) — this is a narrower,
   more conservative test than HYP-PM-0001's foreign/smart-money split, because `broker_flow`'s
   investor-type breakdown (`Asing`/`Lokal`/`Pemerintah`) only spans 2026-04-01→2026-08-19 (~4.5mo),
   shorter than even the already-thin flow-coverage window this draft uses (§7) — layering a second,
   shorter-history proxy on top would compound LIM4, not reduce it.

## 4. Assumptions

| # | Assumption | Risk if false |
|---|---|---|
| A-PM2.1 | Daily-aggregated signed flow (`stockbit_flow_bars`, summed to the day, see §6) correctly signs the day's net aggressor direction | mis-signed flow → mechanism untestable (measures noise) |
| A-PM2.2 | A 3–15 trading-day horizon is long enough to observe the *absence* of reversion but short enough that new, unrelated information doesn't dominate the return | wrong horizon → permanence aliased by later, unrelated events |
| A-PM2.3 | The ≥500-ticker/day coverage floor (§7) selects a representative cross-section of the flow feed's true daily coverage, not a biased subset | biased universe on exactly the days used |
| A-PM2.4 | The observed continuation exceeds round-trip friction (0.60%) | F4 — a real but non-harvestable premium |
| A-PM2.5 | `stockbit_flow_bars` PROXY flow is representative of total imbalance, not only retail | biased imbalance measure (carried forward from HYP-PM-0001's A-PM5) |

> **LIM2 caveat (binding, stated at G1, carried from HYP-PM-0001):** at PROXY fidelity (no limit-order
> book), the I5/I7 separation is **causal argument, not causal identification**
> ([[MARKET_INEFFICIENCY_TAXONOMY]] §5.3, LIM2). Absence of reversion at swing horizon is consistent
> with I7 but does not identify it against every alternative (e.g. a slow-moving fundamental catalyst
> co-occurring with flow would also produce non-reverting continuation without any adverse-selection
> mechanism). This caps confidence at the same tier HYP-PM-0001 was capped at (§9).

## 5. Required dataset & capability

| Dataset | Role | Capability |
|---|---|---|
| `stockbit_flow_bars` (1-min signed lot/delta, aggregated to daily — §6) | daily OFI construction | **Available Today — PROXY tier**, but **short and uneven** at broad cross-sectional breadth — see §7 |
| `ohlcv` | prices, forward returns, universe liquidity filter (Amihud/ADV) | Available Today, ~5.1yr, but growing universe (753 tickers in 2021 → 959 in 2025-26) |
| `corporate_actions` | split/dividend adjustment for return computation | Available Today, 2,171 rows (2,070 dividend, 101 split) |
| `suspension_events` | exclude suspended/gapped tickers from forward-return computation | Available Today, 2022-04-28→2026-07-10, 3,189 rows (359 suspension, 2,830 data_gap) |
| `broker_flow` (investor-type) | **not used this round** — see §3.1 item 4 | Available Today but shorter (2026-04-01→2026-08-19, ~4.5mo) than the already-binding flow window |

## 6. Variables — exact construction (declared before any outcome inspection)

- **`OFI_day(ticker, t)`** = `Σ delta` / `Σ (buy_lot + sell_lot)`, summed over all 1-minute bars in
  `stockbit_flow_bars` for that `(ticker, trade_date)`. This is the **same primitive ratio**
  HYP-PM-0001 used per-minute (`delta/(buy_lot+sell_lot)`), aggregated to a volume-weighted daily
  figure rather than averaged per-minute — chosen specifically to inherit an already-vetted variable
  definition rather than introduce a new one. **Not** `stockbit_flow`'s pre-computed
  `composite_score`/`foreign_score`/`smart_money` fields — those are vendor-derived, un-audited
  constructions whose methodology this draft has not verified, and using them would break the
  reproducibility lineage to HYP-PM-0001's variable.
- **`cont_k(ticker, t)`** ("signed continuation") = `sign(OFI_day(t)) * (logp(t+k) − logp(t))`, where
  `t+k` is measured in **trading days** (not calendar days) using the settled, split-adjusted `ohlcv`
  series, entry priced at `t`'s close (formation-day close — the last fully known price at the
  moment `OFI_day(t)` is fully observed) and exit priced at `(t+k)`'s close. This is the swing-horizon
  analogue of HYP-PM-0001's `signed_reversal_k`, with the sign flipped: HYP-PM-0001 measured
  contrarian capture (`-sign(OFI)*rev_k`, expecting >0 for reversion); this measures **momentum
  capture in the flow's own direction** (`+sign(OFI)*rev_k`, expecting >0 for permanence). Same
  underlying forward-return object, opposite-signed hypothesis, exactly mirroring the I5-vs-I7
  discriminator declared in §2.
- **`illiq(ticker, t)`** = Amihud-style 30-trading-day trailing average dollar volume (ADV), IDR,
  ending at `t` (inclusive) — used only for the universe rule (§7), not as an interaction term this
  round (no I6 magnitude-modifier test is pre-registered here; that is left for a future,
  separately-registered extension per R7.4/R15 discipline, not folded in now).

## 7. Universe rule and formation-date set (coverage-derived, not outcome-derived)

**Formation-date set:** trading days in `stockbit_flow_bars` with **≥500 distinct reporting
tickers** (a data-hygiene floor set from the coverage histogram itself — e.g. 2026-06-04 has only 13
tickers reporting and must be excluded, or every ticker's `OFI_day` on that date is computed from an
almost-empty cross-section). Querying this directly against the live table: **62 trading days**,
spanning **2026-04-28 → 2026-08-19**. This is the entire usable formation-date set — there is no
broader window to select from without breaching the coverage floor.

**Per-formation-date universe:** for each formation date `t` in that set, a ticker is included if
(a) it reports in `stockbit_flow_bars` on `t`, (b) it has a valid, non-suspended `ohlcv` close on
both `t` and `t+k` for the horizon(s) being evaluated (checked against `suspension_events`), and (c)
its 30-trading-day trailing ADV as of `t` is ≥ **Rp 5,000,000,000/day** (`VALUE_LIQ_MIN_IDR`,
`engine/liquidity.py:23` — the same constant the existing P0/NR7 liquidity filter uses, reused for
consistency rather than picking a new threshold). Unlike the existing `liquid_universe()` precedent
in `research/studies/nr7_generalization_study.py` (which applies a **single as-of-today** ADV
filter across an entire multi-year backtest), this rule recomputes the ADV filter **per formation
date**, which is more point-in-time-correct and does not require the caveat flagged in the T4 data
coverage report about that precedent's survivorship exposure.

**Horizon-tail trim:** for k=15, formation dates within the last 15 trading days of the flow
window's end are excluded (no realized forward return yet); k=7 and k=3 trim correspondingly less.
Exact post-trim N per k is left to the (not-yet-run) experiment script to report — computing it
requires counting trading days, which is a calendar operation, not an outcome inspection, but is
deferred here to keep this draft strictly to declared *rules* rather than partially-executed
results.

## 8. Data-coverage limitation (pre-registered explicitly, per instruction)

- **OHLCV price history:** ~5.1 years (2021-07-05 → 2026-08-20), growing universe (753→959
  tickers) — sufficient for the *price* leg alone, but **not** claimed as the effective sample size
  for this hypothesis, because the binding constraint is flow, not price.
- **Broad daily flow coverage (the actual constraint on this hypothesis):** **62 trading days**,
  2026-04-28 → 2026-08-19 (≈3.9 calendar months, with internal gaps — not every calendar trading day
  in that span has ≥500-ticker coverage). This is shorter than the ~7-8 months estimated in the T4
  data coverage report before this per-day query — that estimate is superseded by this exact count.
- **Therefore: this hypothesis does NOT have 5-year flow-conditioned evidence, and no claim in this
  draft or its eventual registration should be read as 5-year evidence.** Every flow-conditioned
  statistic this experiment can produce is bounded to the 62-day window above. This mirrors, and is
  tighter than, HYP-PM-0001's own declared "history-maturity gate" (~1yr, in-sample only) — this
  hypothesis inherits that same posture at roughly a fifth of the window.
- **Consequence for evidence tier:** per [[EVIDENCE_MODEL]], a short, single-window, in-sample-only
  test cannot support regime-stratified or walk-forward claims (no regime variation is observable in
  a 3.9-month window that includes no full market cycle). The ceiling this implies for §10/§11 is at
  least as tight as HYP-PM-0001's C2, likely tighter given the shorter window — final tier is fixed
  at registration, not asserted here.

## 9. Planned statistical methodology (preparation only — no experiment run)

- **Primary test:** cluster-by-day mean of `cont_k` at k=7 (same `daily_stats()` cluster-by-day
  approach as EXP-PM-0001: aggregate to a per-day cross-sectional mean, t-test the resulting daily
  series, N≈62 clustered days minus the horizon-tail trim) — mirrors EXP-PM-0001's inference method
  exactly, applied to the daily/swing construction instead of the minute construction.
- **Robustness gradient:** k ∈ {3, 15} (the declared range's endpoints) as **consistency checks**,
  not a selection scan — all three (k=3,7,15) must agree in sign for the result to be treated as a
  clean continuation signature, exactly the discipline HYP-PM-0001 applied to its own k∈{5,15,30}.
  k=7 was chosen as the primary because it is the arithmetic anchor of the declared 3–15 range,
  fixed by range logic alone, not by any observed effect at any k.
- **Decile sort on `OFI_day`** (descriptive), primary k, analogous to EXP-PM-0001 §"Decile sort."
- **No participant-class (informed-flow) split this round** — see §3.1 item 4 and A-PM2.1; the
  I5/I7 discriminator here rests entirely on the reversion-vs-permanence sign/decay pattern across
  k, not on an informed-flow proxy (LIM2 caveat, §4, applies with full force).
- **Multiplicity:** family-adjusted DSR against the P-M scan distribution (now two registered
  members: HYP-PM-0001 + HYP-PM-0002); PBO via CSCV where the 62-day window permits it (if the
  window is too short for a meaningful CSCV partition, that is itself reported, not concealed).

## 10. Falsification criteria & one-sentence refutation

- **Economic feasibility criterion (Stage-1 gate, F4):** the gross signed continuation at the
  primary horizon (k=7) must exceed the round-trip friction floor to be economically relevant at
  all. **Cost authority:** `engine/exits/costs.py` — `COMMISSION_BUY 0.15% + SLIPPAGE 0.10%` (buy
  leg) + `COMMISSION_SELL 0.25% + SLIPPAGE 0.10%` (sell leg) = **0.60% round-trip** (identical
  constant HYP-PM-0001 and HYP-PA-0001 both used — the single cost authority for this repository).
- **Ex-ante MDE:** **friction-anchored**, matching HYP-PM-0001's own owner-ratified convention, not
  a statistically-derived MDE. Net-of-cost signed continuation must be **> 0**, i.e. gross signed
  continuation at k=7 must clear **0.60%**.
- **Approximate power sanity check (order-of-magnitude only, no outcome data used):** with N≈62
  clustered days (fewer after horizon-tail trim) and a literature-typical daily-return cross-sectional
  standard deviation on the order of 2–3% for IDX single names, the standard error of a cluster-day
  mean at N≈50-60 is roughly `σ/√N ≈ 2.5%/7.5 ≈ 0.33%` — meaning an effect near the 0.60% friction
  floor sits at roughly **1.5–2 daily-clustered standard errors**, not obviously either abundant
  (unlike HYP-PM-0001's sub-bp MDE over 12.7M bars) or hopeless. **This is a rough bound, not a
  formal power study** — a dedicated `HYP-PM-0002_POWER.md` (mirroring HYP-PM-0001's own separate
  power document) should be run before registration closes, using the exact post-trim N per k, not
  this estimate.
- **Falsification:** displacement conditional on daily OFI **fully reverts, or the surviving
  continuation is ≤ 0 or < the 0.60% friction floor, or the sign is inconsistent across k∈{3,7,15}**
  ⇒ M2.1 refuted for this horizon and window (→ I5/reversion after all, or F4 friction kill, or F5
  regime-artifact of the single 62-day window, or F1 fair-price).
- **One-sentence severe refutation:** *"If price displacement conditional on signed daily order-flow
  imbalance does not persist (net of the 0.60% round-trip friction) over a 3-to-15-trading-day
  horizon, consistently in sign across k=3, k=7, and k=15, the adverse-selection permanence
  mechanism (M2.1) is refuted for IDX proxy flow at swing horizon."*

## 11. Expected evidence product

At N=1 for this hypothesis, the terminal tier ceiling is capped by §8's short-window limitation —
likely **no higher than C2** ([[EVIDENCE_MODEL]] EV-9), and plausibly lower given the single 62-day
window contains no regime variation. Outcome is either a **C2-or-lower provisional continuation
signature** (permanence confirmed, consistent sign across k, net of friction) or a **competent
refutation** (reversion after all ⇒ I5 rehabilitated at swing horizon; F4 friction kill; F5
single-window artifact — explicitly not concealable given §8's declared limitation). Either maps a
boundary on the same D2 identification problem HYP-PM-0001 mapped, at a different horizon. **No
capital at C2 or below — shadow only**, same as HYP-PM-0001.

---

## 12. G1 admissibility assessment

| Requirement | Status |
|---|---|
| Mechanism: M-class + constraint + participant | ✅ M2.1 · information asymmetry · supplier vs informed trader |
| Directional prediction (sign-specified) | ✅ signed continuation > 0 |
| Null | ✅ full reversion, or continuation ≤ 0 / < MDE |
| Scope | ✅ liquid IDX universe (ADV ≥ Rp5bn/day, per-date), 3–15 trading days, 62-day flow window |
| Multiplicity family declared | ✅ P-M {I5,I6,I7,I12} — 2nd member |
| D2 separation strategy stated | ✅ reversion-vs-permanence sign/decay across k∈{3,7,15} (no informed-flow split this round — declared, not hidden) |
| Mechanism `blind_to` OOS | ✅ M2.1 is theory-first (Glosten-Milgrom); the *choice to test it here* was fixed by HYP-PM-0001's failure entry (2026-07-18), before this draft or any swing-horizon computation existed |
| Refutation condition in one sentence | ✅ §10 |
| required_data Available/Obtainable | ✅ Available Today (PROXY) — **short-window gate is explicit and binding**, not a deferred validation caveat like HYP-PM-0001's (§8) |
| Power / test can fail (R2) | ⚠️ order-of-magnitude bound only (§10) — a dedicated power doc is recommended before registration closes |
| Ex-ante criterion incl. effect size (R5) | ✅ friction-anchored, 0.60%, fixed here (not deferred, unlike HYP-PM-0001's original draft) |
| CRO approval | **pending — this draft is presented for review, not registered** |

## 13. Outstanding blockers & registration readiness

| Blocker | Nature | Blocks registration? |
|---|---|---|
| **B-1 · Formal power doc** | the §10 power check is a rough bound; a `HYP-PM-0002_POWER.md` with exact post-trim N per k is recommended | Recommended, not strictly required — HYP-PM-0001 itself deferred an equivalent item |
| **B-2 · CRO ex-ante sign-off** | confirm k-set, MDE, universe rule, and the decision not to attempt an informed-flow split this round | Yes |
| **B-3 · Short-window ceiling** | §8 — no regime variation observable; caps the achievable evidence tier | No — declared limitation, not a registration blocker |
| **B-4 · LIM2 identification ceiling** | PROXY fidelity ⇒ I5/I7 is argument, not identification (carried from HYP-PM-0001) | No — caps confidence, declared |

> **Registration readiness:** data exists today (unlike HYP-PA-0001's original block); the coverage
> floor and universe rule are fixed from schema inspection alone. The only things between this draft
> and a valid G1 registration are **B-2 (your sign-off on the parameters above)** and, optionally,
> **B-1 (a short formal power doc before committing to k=7 as primary)**. No experiment, inference,
> or registration is performed by this document.

## 14. Traceability

Family [[DECISION_LOG]] D-028 · Mechanism [[ECONOMIC_MECHANISM_TAXONOMY]] §3 (M2.1) · Identification
[[MARKET_INEFFICIENCY_TAXONOMY]] §5.3 (I5↔I7, LIM2) · Gate [[HYPOTHESIS_LIFECYCLE]] §4.1 · Tier
[[EVIDENCE_MODEL]] EV-9 · Cost authority `engine/exits/costs.py` · Liquidity constant
`engine/liquidity.py:23` (`VALUE_LIQ_MIN_IDR`). **Parent:** [[RESEARCH_PROGRAM]] · **Lineage:**
[[HYP-PM-0001_REGISTERED]] / [[FAILURE_ENTRY]] (`FAIL-PM-0001`, the origin of this hypothesis's
mechanism choice, §0/§2). **Registers into** P-M family at a later step — not before.
