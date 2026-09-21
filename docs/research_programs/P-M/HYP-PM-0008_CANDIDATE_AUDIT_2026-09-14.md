# HYP-PM-0008 · CANDIDATE AUDIT — 2026-09-14

**Authority:** generated point-in-time record · **Mode:** forensic discovery + candidate generation + ranking
**Owner authorization:** Branch A, 2026-09-14 — permission to **develop and register** one new hypothesis;
**not** permission to execute.
**Companion document:** `HYP-PM-0008_SPEC.md` (DRAFT — NOT REGISTERED)

> **ZERO EMPIRICAL TESTS WERE RUN.** No backtest, no G1 harness run, no return, no event count, no outcome
> statistic, no parameter tuned against data. The only database access was read-only **coverage metadata**
> (table date-span, per-regime session counts, `corporate_actions` row count, table-existence checks) —
> required by this brief's own "data readiness" and "PIT availability" ranking criteria. No registry,
> dataset, config, or verdict was modified.

---

# PHASE 1 — FORENSIC DISCOVERY: THE CONSUMED MECHANISM SPACE

## 1.1 Corpus read

`RESEARCH_PROGRAM.md` · `HYPOTHESIS_REGISTRY.md` · `FAILURE_REGISTRY.md` · `DECISION_LOG.md` (D-028, D-048,
D-049) · `EXPERIMENT_LEDGER.jsonl` · `FOUR_TEST_IDENTITY_AND_REGISTRY_AUDIT_2026-09-11.md` (Parts A–H) ·
`NEXT_LAWFUL_HYPOTHESIS_AUDIT_2026-09-14.md` · `ZCODE_ALPHA_DISCOVERY_FAMILY_MAP_2026-09-10.md` (16
families A–P) · `ZCODE_TOWR_BREAKOUT_PULLBACK_DEEP_DIVE_2026-09-10.md` · `G1_REGISTRATION_v1_2026-09-11.md` ·
`C7_REGISTRATION_v1_2026-09-11.md` · `C8_MECHANISM_AUDIT_2026-09-11.md` · `G1_POSTMORTEM_FAMILY_TRIAGE_2026-09-11.md` ·
`DATASET_B_SEMANTIC_REGISTER_v1.json` (13 entries) · `MARKET_INEFFICIENCY_TAXONOMY.md` (I1–I12) ·
`LC-PM-0001…0010` · `DISCOVERY_2026-08-21_M2x_short_horizon.md` · `DISCOVERY_2026-08-21_M6_I1_price_limits.md` ·
`S1-PM-0005/0006/0007` · `HYP-PM-0001/0002/0003` records · ZCode `broker_flow_program/31_MECHANISM_MAP.md` ·
`bfi001_broker_flow/90_results.json` (14-cell family).

## 1.2 The used-up mechanism space — what is actually consumed, and by what

This is the load-bearing table of the audit. "Consumed" is used strictly: a mechanism is consumed if it has
been **executed to a determinate result**, **structurally voided by an instrument defect**, or **blocked by
an unresolved semantic**.

| # | Mechanism | Status | Consumed by | Recoverable? |
|---|---|---|---|---|
| 1 | Aggregate net-flow direction (inventory M1.1 / adverse selection M2.1) | **STRUCTURALLY VOID** | Exchange accounting identity: all-broker net ≡ 0 in **100.00%** of 30,877 Dataset B cells (integer-exact); 68.10% exactly zero in Dataset A lots. HYP-PM-0003 INVALID-DATA; BFI-001 primary INVALID-DATA | **No** — prohibited by the D-049 `all-broker-net-identity` hard gate |
| 2 | Vendor aggressor-side OFI (immune instrument) | **CONSUMED** | HYP-PM-0001 FAILED F2 (k=15 signed reversal −0.0008%); LIT-001 REJECTED; LIT-002 INCONCLUSIVE, blocked to ≈2028-04 | No |
| 3 | Ownership-conduit disagreement (foreign/local brokerage nets) | **CONSUMED — INVALID SPEC** | C2 / HYP-PM-0004: `for+loc+pem ≡ 0` in 100% of cells ⇒ "disagreement" is algebraically forced (77.79% opposite-sign); gate incidence inflated 26.6%→72.5%. Also BFI-001 F2 cells (asing/lokal/pemerintah) executed | No |
| 4 | **Breadth / participation surprise** | **CONSUMED TWICE** | C3 / HYP-PM-0005 NOT CONFIRMED (valid, bounded; k=5 θ=+5.8bp, Holm p=1.0, 329 daily obs) **and** BFI-001 F4_breadth (t=+2.41, Holm 0.164) | No |
| 5 | **Flow intensity state** (gross/ADV20 ≥ 2.0) | **CONSUMED** | C7 / HYP-PM-0006 — registered 2026-09-11, **executed 2026-09-14**, NOT CONFIRMED | No |
| 6 | **Absorption state** (intensity ≥2×ADV ∧ \|ret\| ≤1%) | **PARKED + NESTED** | C8 — unregistered, never forward-tested; and semantically **contained inside C7's state space** (it is C7's high-intensity state ∧ a small-return condition) | Only as a C7 sub-cell — i.e. as a re-cut |
| 7 | **Informed-broker persistent skill** (trailing-IC "smart money") | **CONSUMED — clean null** | BFI-001 `F4_binf_k5`: NW t = **+0.0857**, p = 0.932, Holm 1.0; rank-IC `binf` t = +0.36. The information-asymmetry-via-broker-identity channel was tested and is flat | No |
| 8 | **Concentration / dominance (CONC)** | **CONSUMED as a secondary** | BFI-001 `F4_conc_k5`: t = **−2.65**, Holm 0.097 — suggestive, Holm-unconfirmed. Map candidate "C6" was never registered | Only by selecting on a suggestive secondary ⇒ **textbook post-hoc rescue** |
| 9 | **Species composition** (desk vs aggregator), **desk programs** | **BLOCKED — semantic** | C1a/C1b `WITHDRAWN_FREQ_DEPENDENT`; `broker_flow.freq` meaning **UNKNOWN**, research use **FORBIDDEN** (~100× reconciliation shortfall) | Only if a vendor probe establishes `freq` units |
| 10 | Broker network / coalition coordination | **REJECTED descriptively** | Family map N: avg pairwise daily tilt correlation **−0.065**; dominant-broker identity churn 80%/day. "H9 broker-coalition fingerprint" = NOT FOUND | No |
| 11 | Cross-stock broker information diffusion | **DEGENERATE** | Family map F: aggregators active in 93/~850 names daily ⇒ p(other-name next day) = 0.9999 vs breadth base ~0.10 — indistinguishable from universal breadth | No |
| 12 | Broker×stock specialization | **WEAK / no structure** | Family map E: top-1 affinity share p50 = 0.001 | No |
| 13 | Flow/price disagreement on true net | **BLOCKED — data** | Family map G: broker_flow per-ticker net structurally ~0; vendor version pending `[DEP-B]` | No |
| 14 | Same-agent persistence through retracement | **TESTED NEGATIVE descriptively** | TOWR deep dive: "breakout buyers rotated… identity overlap/flip features show **zero discrimination**" (1,625 events) | No |
| 15 | Auction / reconstitution dislocation | **CONSUMED — terminal** | HYP-PA-0001 FAILED F2 (sole P-A slot); ADD side real (+1.89%) but **not capturable** | No |
| 16 | Range-contraction breakout (OHLCV) | **FALSIFIED** | NR7 / P0: pooled OOS −0.1787%/trade, n=6,183; D-029 → SHADOW, no capital | No |
| 17 | **Close-to-close reversal after a large move** | **REJECTED (discovery)** | `S1-PM-0006` (2026-08-25): after ≥10% fall, next day mean **−0.587%**, up only 36.1% (n=7,191). "Buying the crash loses money before costs." Reversal after large *up* days is unexecutable and sub-cost. `S1-PM-0007` sign-flip = zero-return-mass artifact | No |
| 18 | H4/H5/H7/H9 named families | **DO NOT EXIST** | `G1_POSTMORTEM_FAMILY_TRIAGE_2026-09-11.md`: searched both corpora, **NOT FOUND** — no registration, no spec, no map entry. H7 retail-response is freq-dependent (same wall as C1a); H9 ≈ map family N (REJECTED) | Not applicable — nothing to copy |

**Blocked dimensions (family map §6, re-verified):** intraday broker timing · true-net disagreement ·
sector-relative structure (`sectors_*` is a 2-day snapshot) · fundamentals/news/event conditioning
(unadmitted) · options/short/borrow, order book, client identity (**unavailable in market — permanently**).

## 1.3 The structural conclusion of Phase 1

The family map's own verdict — "**DISCOVERY SUFFICIENTLY EXHAUSTED** at the descriptive level permitted by
current data; 16/16 families searched" — is **confirmed and strengthened** by this audit. Every remaining
ticker-day construction over `broker_flow` is one of: identity-void (1, 3, 13), executed (2, 4, 5, 7, 8),
semantically blocked (9), descriptively rejected (10, 11, 12, 14), or a nesting of an executed state (6).

> **Therefore any genuinely new mechanism must leave the `broker_flow` instrument entirely.** This is not a
> preference; it is forced by the identity defect, the `freq` semantic, and the exhaustion of the 16-family
> map. It is also the single most useful finding of Phase 1, because it explains why the last four
> registrations produced three nulls and two invalidations: they were all drawing from one contaminated well.

---

# PHASE 2 — CANDIDATE MECHANISMS (five, generated against the used-up map)

## Candidate A — **I1 · auto-rejection band pinning: rule-truncated demand deferral** ← SELECTED

| Field | Content |
|---|---|
| **1 Proposed ID** | HYP-PM-0008 (0007 held — see SPEC §0) |
| **2 Mechanism name** | Price-limit (auto-rejection band) pinning — deferred demand under a truncated price path |
| **3 Economic rationale** | **M6 market-design artifact / D1.** The ARB mechanically forbids execution below a bound set off the prior close. Demand that would have cleared at a forbidden price is **deferred, not extinguished**, and carries into *t+1* as unexecuted supply. Truncation severity is set by band width — an exogenous decreed quantity |
| **4 Exact observable** | `ARB_contact(i,t) := close(i,t)/close(i,t−1) − 1 ≤ −(band_lower(i,t) − 0.005)`, `band_lower` = 35/25/20% tiered under R3, 15% flat under R4. **`close` only** |
| **5 Prediction horizon** | **k = 1** (one session — the mechanism's own timescale) |
| **6 Primary estimand** | `theta_primary` = coefficient on `1{d ∈ R4}` in an OLS of the **daily** mean post-contact return series on a constant + R4 indicator, Newey-West lag 5. **Prediction: negative** |
| **7 Independence from C3/C7/C8** | **Total — disjoint instrument.** Consumes no broker-flow field whatsoever (no `value`, `lot`, `value_total`, `investor_type`, `freq`, `bandar_detector`) and no Dataset B table. C3 = broker counts; C7 = gross/ADV20; C8 = C7 ∧ small-return. None is computable from this candidate's inputs, and vice versa |
| **8 Not a post-hoc rescue** | Never executed, never registered, no numbers exist. Surfaced **blind** on 2026-08-21 from a *literature* sweep (priority-1 market-design), months before C3/C7 results. Its thresholds come from **decrees**, not from any outcome |
| **9 Required data** | `ohlcv.{ticker,date,close,volume,is_final}` + `corporate_actions` + the LC-PM-0009 regime calendar |
| **10 PIT availability** | **Clean.** Formation uses `close(t)`, `close(t−1)`, both known at close *t*. No T+1 artifact. Universe filter uses trailing-60 median value with `shift(1)` |
| **11 Likely sample size** | **UNKNOWN BY DESIGN** — the §11 feasibility gate. Coverage: **377 R3 sessions / 343 R4 sessions**, 959 tickers, 2021-07-05→2026-09-14 (~10× Dataset B's span) |
| **12 MDE feasibility** | Declared ex ante: Δ = 0.60% (friction floor), σ_daily = 2.0% (declared, not measured), α .05 / power .80 ⇒ **≥175 event-days and ≥1,090 events per arm**. Shortfall ⇒ **RETIRED — UNPOWERED** (not FAILED) |
| **13 Transaction-cost relevance** | 0.60% round-trip reported as a sensitivity only. **Capturability is structurally absent** (§19 of the SPEC) — declared before execution |
| **14 Multiplicity / family** | **NO OPEN FAMILY** — the blocker. I1 is confounded with I2/I3 (inside P-A's family) and modified by I12 (inside P-M's). **Owner decision D-1** |
| **15 Kill rule** | "If `theta_primary` is not negative with two-sided p < 0.05, the band-deferral hypothesis is refuted" — F2 |
| **16 Leakage risks** | Corporate-action reference resets (E3) · mixed adjustment basis, RAJA (E4) · IPO 2× bands with no listing table (E5 proxy) · Papan Pemantauan Khusus unidentifiable (B4) · 2025-04-08 compound halt-threshold treatment (E6) · tick-grid rounding absorbed by a frozen `tol` |

## Candidate B — Multi-day per-broker inventory accumulation → unwind

| Field | Content |
|---|---|
| **Mechanism** | Inventory transfer. Individual brokers accumulate one-sided positions over a window *W*; the accumulated imbalance must eventually be liquidated, producing predictable pressure |
| **Key insight** | The accounting identity forces only the **sum** of broker nets to zero; **per-broker nets are non-degenerate**, and Dataset B (limit=150, full population) measures them *exactly* for the first time |
| **Independence** | Weak-to-moderate. Concentration of an accumulated position is close to **CONC** (consumed, t = −2.65) and to BFI-001's mechanism-map **H2** "institutional persistence/accumulation"; family map D already measured broker directional persistence (0.526) descriptively |
| **Rescue risk** | **High.** Any construction is one step from CONC, whose only interesting number is a Holm-unconfirmed suggestive secondary — selecting on it is the definition of a post-hoc rescue |
| **Family cost** | Falls squarely in **I5 (inventory)** — inside P-M's `{I5,I6,I7,I12}`, which already holds **two failures**. Would be the 3rd slot in a contaminated denominator |
| **Gate burden** | Must clear the D-049 identity gate affirmatively (per-broker net *is* a net); passable, but adds a validation burden Candidate A does not carry |
| **Verdict** | **Rejected** — fails "not a post-hoc rescue" and "independent from consumed families" |

## Candidate C — Uncensored-vs-disclosed participation divergence

| Field | Content |
|---|---|
| **Mechanism** | Information asymmetry via disclosure truncation. `bandar_detector.total_buyer/total_seller` is the **uncensored** broker count (VERIFIED: `disclosed_rows == min(total,25)` in 30,626/30,626 ticker-days); `broker_flow` is top-25 censored. The divergence measures participation *hidden* by the disclosure rule |
| **Novelty** | Genuine — it is the one VERIFIED uncensored measure in the estate and no candidate has used it |
| **Independence** | **Fails.** The construct is a **broker count** — i.e. breadth. C3 (breadth surprise) and BFI-001 F4_breadth have both consumed that family. A censored-vs-uncensored count ratio is a breadth normalization, not a new mechanism |
| **Verdict** | **Rejected** — "C3 breadth surprise in disguise" |

## Candidate D — ARB-boundary × flow-composition interaction

| Field | Content |
|---|---|
| **Mechanism** | Event-conditioned flow–price interaction: *who* supplies liquidity into the band wall |
| **Independence** | Moderate — the interaction is new, but each leg is used |
| **Verdict** | **Rejected.** Inherits **both** parent liability sets: Candidate A's decree/feasibility blockers **and** the broker-flow instrument's identity/`freq` defects. Dataset B's 386-session window would also truncate the study to ~58 R3 sessions, destroying the control arm that gives Candidate A its identification. Strictly dominated by A |

## Candidate E — IPO first-trading-day widened-band constrained liquidity

| Field | Content |
|---|---|
| **Mechanism** | M6 — IPO first-day limits are **2× normal**, referenced to the offer price (LC-PM-0009); a distinct constrained-liquidity setting |
| **Independence** | Good — distinct from A (wider, not tighter, bands; different reference price) |
| **Verdict** | **Rejected.** (i) **No listing-date table is held**, so the event set is not identifiable; (ii) a *widened* band binds less, inverting the mechanism's own severity logic; (iii) IDX IPO first-days are few and concentrated in small caps — the "HYP-PA-0001 again with different labels" failure mode the discovery record explicitly warned about |

---

# PHASE 3 — RANKING

Ranked on the brief's eight criteria (A economic distinctness · B preregistration cleanliness · C data
readiness · D PIT integrity · E power/MDE plausibility · F independence from consumed families · G execution
simplicity · H resistance to post-hoc interpretation). **Ranking is on design properties only — no candidate
was ranked by whether historical data look profitable, and no outcome was inspected.**

| | A · ARB band pinning | B · inventory unwind | C · uncensored breadth | D · ARB × flow | E · IPO bands |
|---|---|---|---|---|---|
| **A** distinctness | **High** (M6/D1; leaves the instrument) | Low | Low | Medium | Medium |
| **B** prereg cleanliness | **High** (blind, 2026-08-21, literature-sourced) | Low (selects on a suggestive secondary) | Medium | Low | Medium |
| **C** data readiness | **High** (377/343 sessions, 959 tickers) | High | High | **Low** (58 R3 sessions) | **Absent** (no listing table) |
| **D** PIT integrity | **High** (close-only, shift(1)) | Medium | Medium | Medium | Medium |
| **E** power/MDE | **Unresolved — gated** | Medium | Medium | Low | Very low |
| **F** independence | **Total (disjoint instrument)** | Low | Very low | Low | Medium |
| **G** execution simplicity | **High** (2 tables, close-only, one OLS) | Medium | Medium | Low | Low |
| **H** post-hoc resistance | **High** (placebo + frozen no-rescue) | Low | Medium | Low | Medium |
| **Rank** | **1** | 3 | 4 | 5 | 2 (on distinctness alone; fails data) |

**Candidates requiring unresolved semantics — stated as the brief requires:**

- **A:** IDX **tick-size table not extractable** ⇒ exact band bound not computable ⇒ absorbed by a frozen
  `tol = 50 bp`. **Papan Pemantauan Khusus** membership and **listing/suspension** tables **not held**.
  Regime decrees **not primary-verified** (B2).
- **B:** requires an affirmative D-049 identity-gate demonstration for per-broker nets.
- **C, D:** `broker_flow.freq` **UNKNOWN / FORBIDDEN**; `bandar_detector.value/volume` is **net crossed**
  volume and may **never** be a denominator.
- **E:** listing dates absent.

---

# PHASE 4 — SELECTION

**Selected: Candidate A — I1 auto-rejection band pinning (HYP-PM-0008).**

It is the only candidate that clears the distinctness test decisively rather than arguably, and it is the
only one that escapes the contaminated instrument identified in §1.3.

## 4.1 Why it is genuinely new — the exclusion list, item by item

| Brief's exclusion | Disposition |
|---|---|
| C3 breadth surprise in disguise | **No.** C3 counts brokers. HYP-PM-0008 reads no broker table at all; a broker count is not computable from its inputs |
| C7 intensity/state in disguise | **No.** C7 is `gross(Σ\|value\|)/ADV20`. HYP-PM-0008 has no gross, no broker values, no ADV20 |
| C8 absorption in disguise | **No.** C8 is C7's high-intensity state ∧ small-return. HYP-PM-0008's state is a *rule bound relative to the prior close* — and its events are **large**-return by construction, the opposite of C8's small-return condition |
| A re-run of C3/C7 | **No.** Different instrument, population construction, estimand (a cross-regime difference, not a state contrast), and identification |
| A parameter variant of C3/C7 | **No.** No parameter is shared. Its thresholds (35/25/20/15%) are **exchange decrees**, not tunable quantities |
| A post-hoc rescue of any failed/invalid result | **No.** Nothing in the I1 line has ever been executed. Surfaced blind from a literature sweep on 2026-08-21, before C3/C7 ran. **It is not a rescue of `S1-PM-0006` either** — see §4.2 |
| A mechanically renamed existing hypothesis | **No.** I1 is its own taxonomy entry (M6/D1); every registered P-M/P-A hypothesis to date is M1/M2 flow-based or I8→I2 auction-based |
| An H4/H5/H6/H7/H9 concept copied without checking registration | **No.** Checked: those names **do not exist** in either corpus (`G1_POSTMORTEM_FAMILY_TRIAGE`). Nothing was copied from them |
| HYP-PM-0002 promoted merely because it is DRAFT | **No.** HYP-PM-0002 is untouched, still DRAFT, still consuming no slot. Its mechanism (OFI continuation on `stockbit_flow_bars`) is unrelated |

## 4.2 The one adjacency that must be confronted — and why it does not sink the candidate

`S1-PM-0006` (2026-08-25, DISCOVERY ONLY, **REJECTED**) measured that after a ≥10% single-day fall, the next
close-to-close move is **down** (mean −0.587%, up 36.1%, n = 7,191). A skeptic should ask whether
HYP-PM-0008 is that rejected cohort re-cut.

**It is not, for three independent reasons — and the third is the decisive one:**

1. **Different object.** `S1-PM-0006`'s cohort is `|r| ≥ 10%` — a **move-size** cutoff. HYP-PM-0008's state
   is **band contact**, a *rule* bound (15% under R4; 20–35% under R3). Under R3 a −10% day is nowhere near
   the band. The discovery record itself rejected the move-size framing precisely because "the running
   variable (the size of the move) is **endogenous** to the demand process. A decree is not."
2. **Different estimand.** `S1-PM-0006` estimated a within-cohort mean. HYP-PM-0008 estimates a
   **difference across an exogenous rule change**, with a same-study placebo on the side whose rule did not
   move. A mean and a difference-in-means across a decree are not the same quantity.
3. **`S1-PM-0006`'s primary window is itself void for this question.** Its designated window **S2 =
   2023-04-03 → 2025-12-12 straddles the 2025-04-08 band switch.** Under [[LC-PM-0009]] transportability
   condition 1 — "never pool across regime boundaries without modelling the switch" — a pooled estimate over
   that window **cannot speak to the band mechanism at all**. It measured something real about large moves;
   it did not, and structurally could not, measure the band.

**However — recorded honestly and prominently, because it lowers the prior:** the *direction* of that local
descriptive evidence (falls continue) is consistent with I1's deferred-selling prediction, which means the
primary is **not** a bet against local evidence. What it does mean is that a confirmation will be harder to
attribute to the band rather than to momentum — which is exactly why the identification is a cross-regime
difference with an unchanged-rule placebo, not a post-contact mean. Per [[MARKET_INEFFICIENCY_TAXONOMY]] I1,
"a test that does not separate I1 from I10 tests neither," and a within-cohort mean does not.

## 4.3 The mechanism's own inversion — recorded because it corrects the source document

`DISCOVERY_2026-08-21_M6_I1_price_limits` §5 argues the ARB side is "where an executable version could
exist," reasoning that a buyer filled into a limit-down wall earns an upward, long-only **reversal**.

**That is a different mechanism from I1, and this audit does not adopt it.** At a limit-down the truncated
side is *selling*; deferred demand therefore predicts **continuation downward**, which is what the taxonomy's
I1 entry states ("the demand that would have cleared at a forbidden price does not vanish — it is
*deferred*"). The "buy the wall" reversal story is **liquidity provision / Grossman–Miller inventory — I5**,
which sits inside P-M's `{I5,I6,I7,I12}` family and has already failed twice there (HYP-PM-0001 F2;
HYP-PM-0003 INVALID).

Registering the reversal framing would therefore have been a third draw on a twice-failed family under a
mislabelled mechanism. **The SPEC registers the I1 continuation prediction**, and the consequence — that the
capturable leg does not exist — is declared **before** execution rather than discovered after (SPEC §19).

## 4.4 Does it pass a strict lawful-registration test? — the honest answer

Applying [[RESEARCH_PROGRAM]] §6.1 (admissibility, binary, non-negotiable):

| Gate | Result |
|---|---|
| Persistence **barrier** named | **PASS** — M6 structural, the program's own highest durability class |
| Mechanism authored **before** the result | **PASS** — 2026-08-21, blind, literature-sourced |
| The test **could fail** (power / MDE) | **NOT ESTABLISHED** — MDE declared; sample sufficiency unknown and forbidden to compute under Branch A |
| Predicted effect ≥ friction | **NOT ESTABLISHED** on the ARB side — no literature card establishes a lower-limit effect (LC-PM-0008 notes lower-limit hits are data-poor) |
| All six §5.2 elements present | **FIVE OF SIX** — the **multiplicity family** element is unresolvable without an Owner act |

> **Conclusion: the candidate is fully *specified* but not yet lawfully *registrable*.** The two open gates
> are not research defects and are not mine to close: one is a preflight count the authorization forbids,
> the other is a permanent-denominator decision reserved to the Owner. Per the brief — "If a new family slot
> or multiplicity amendment is required, STOP before changing the registry and report the exact Owner
> decision required" — the registry was **not** touched.

**This is not a NO REGISTERABLE NEW HYPOTHESIS finding.** A registrable mechanism was found, and it is
specified to freeze. What is missing is authorization, not science.

---

# PHASE 5 — REGISTRY / FAMILY / MULTIPLICITY IMPLICATIONS

## 5.1 Current denominators (unchanged by this audit)

| Family | Members | State |
|---|---|---|
| P-M · `{I5,I6,I7,I12}` | **2** — HYP-PM-0001 (FAILED F2), HYP-PM-0003 (FAILED F2 → INVALID-DATA) | both terminal |
| P-M · C-family `{C2,C3,C7}` | **3** — C2 INVALID(gov), C3 NOT CONFIRMED, C7 NOT CONFIRMED (executed 2026-09-14) | all terminal |
| P-A · `{I2,I3,I8}` | **1** — HYP-PA-0001 (FAILED F2) | terminal |

## 5.2 The family problem, stated exactly

I1 belongs to **no open family**. But it is **not orphaned** either — the taxonomy records:

- **I1 confounded with I2** ("band effects concentrate at session boundaries") — I2 ∈ **P-A**
- **I1 confounded with I3** ("a band that bound at the close mechanically shapes the next open… I1 and I3
  evidence overlap on precisely the observations most likely to be studied") — I3 ∈ **P-A**
- **I12 modifies I1** — I12 ∈ **P-M**
- **I1 confounded with I10** (salience) — I10 is in **no** declared family

PG-7 makes confound-driven merges **mandatory and immediate** ("Confounding discovered → PG-7 merge
evaluated immediately — it cannot be done later"), but **D-028 closed the merge window**: "The merge was
available once; it has now been exercised… the only future remedy for a mis-drawn boundary is termination
and a new family from zero, forfeiting every survivor."

This is a genuine governance tension that **cannot be resolved by a research document**. It is why this
audit stops at the registry.

> **Mitigating design note:** the SPEC's close-only construction (no `open` anywhere — G-1 is closed, and
> `S1-PM-0006` verified `close` integrity) materially *reduces* the I1↔I3 overlap, since I3's confound
> operates through the next **open**. It reduces it; it does not dissolve it.

## 5.3 Required owner decisions

- **D-1 · Family determination** — (a) open a new separately-denominated family on the D-048 Option-B
  precedent, recording the I1↔I2/I3/I12 confounds as preserved caveats; (b) register into P-A's
  `{I2,I3,I8}` on the confound, taking a 2nd P-A slot; (c) refuse registration because the mandatory PG-7
  merge is unavailable post-D-028. **No option may be taken silently.**
- **D-2 · Decree verification** — authorize primary retrieval of SK Kep-00003/BEI/04-2025 and the 2023
  "Auto Rejection Simetris Tahap II" decree; **or** accept Q3 secondary corroboration on the record and
  accept B8 exposure; **or** hold. **Note the discrepancy to be resolved either way:**
  `DATASET_B_SEMANTIC_REGISTER_v1` marks the bands **`VERIFIED`**, while [[LC-PM-0009]] — the card it cites —
  grades itself "corroborated but **NOT primary-verified**" and calls primary verification "a **hard S2
  prerequisite, not a nicety**."
- **D-3 · Knowingly non-capturable test** — confirm that a permanent family slot may be spent on a
  gross-only test whose capturable leg is structurally absent (HYP-PA-0001 precedent).

## 5.4 What was NOT done

`HYPOTHESIS_REGISTRY.md`, `FAILURE_REGISTRY.md`, `DECISION_LOG.md`, `EXPERIMENT_LEDGER.jsonl`, Dataset B,
`DATASET_B_SEMANTIC_REGISTER_v1.json`, `g1_config.json/py`, the C3/C7/C8 records, and every production
database are **unmodified**. No family was opened, narrowed, widened, or pooled. No status was advanced. No
terminal verdict was created. Nothing was marked EXECUTED.

---

# REMAINING BLOCKERS (consolidated)

| # | Blocker | Resolver |
|---|---|---|
| B1 | Family/multiplicity determination — I1 has no open family and confounds two already-declared ones | **Owner (D-1)** |
| B2 | Regime decrees not primary-verified; semantic-register `VERIFIED` vs LC-PM-0009 `not primary-verified` discrepancy | **Owner (D-2)** |
| B3 | Feasibility/power unknown — the §11 gate; R3 arm most at risk (wide bands ⇒ rare contact) | preflight, post-authorization |
| B4 | Papan Pemantauan Khusus, listing-date, and suspension tables **not held**; tick table not extractable | **Owner (D-3 / data admission)** |
| B5 | Capturable leg structurally absent — gross-only knowledge product, max tier C2 | **Owner (D-3)** |

# FILES CHANGED

1. `docs/research_programs/P-M/HYP-PM-0008_SPEC.md` — **created** (DRAFT, not a registration)
2. `docs/research_programs/P-M/HYP-PM-0008_CANDIDATE_AUDIT_2026-09-14.md` — **created** (this document)

No other file was created, edited, or deleted.

# CONFIRMATION

**ZERO empirical tests were run.** No G1 harness execution, no backtest, no return, no band-contact event,
no power figure, no outcome statistic computed from data. No parameter was chosen by inspecting an outcome.
No registry mutation, no Dataset B change, no semantic-register change, no `research.db` write, no production
DB write, no C3/C7/C8 change, no config change.

# STATUS

## **OWNER DECISION REQUIRED**

A genuinely new, economically distinct, mechanically specifiable hypothesis was found and frozen in
`HYP-PM-0008_SPEC.md`. It cannot be registered today because registration requires a **new family slot or a
multiplicity determination** (B1) — reserved to the Owner — plus decree verification (B2) and a capturability
acceptance (B5). On D-1/D-2/D-3 the specification is registrable as written; the preflight feasibility gate
(B3) then decides whether it executes or terminates as **RETIRED — UNPOWERED**.
