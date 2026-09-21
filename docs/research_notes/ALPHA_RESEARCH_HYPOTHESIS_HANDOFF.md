# Broker-Flow / Stockbit-Flow — Hypothesis Handoff & Research-Design Gate

**Status: research-design gate output only. Not a hypothesis registration.** None of the hypotheses
below are entered into `research/knowledge`, the `hypotheses` table, or
`docs/research_programs/HYPOTHESIS_REGISTRY.md` by this document. No backtest, empirical outcome
analysis, vendor/API fetch, database write, research-code change, PIT-table change, or Stockbit/
broker-flow data change was performed to produce this document. Obsidian and git were not touched
by the research process that produced it (this file's own addition to the repo is a plain,
uncommitted reference doc — see repo CLAUDE.md for the difference between this and an actual
governance-corpus entry).

This document builds on, and does not replace, `ALPHA_RESEARCH_LITERATURE_REVIEW.md` (same
directory) — all §-references below point to that file.

---

## 1. Verification Results

A primary-source verification pass was run on the five highest-impact claims, using RePEc/IDEAS
abstract pages, NBER's own abstract pages, and BIS's/arXiv's own public pages (not the original
pass's SSRN/publisher-PDF URLs, which had failed with 403/binary errors).

| Claim | Result | Evidence tag change |
|---|---|---|
| Chordia & Subrahmanyam (2004) — lagged imbalance predicts next-day return, reverses sign once contemporaneous imbalance is controlled for | **Still unverified.** RePEc/IDEAS page confirms only bibliographic metadata ("No abstract is available for this item"); full text is ScienceDirect-subscription-only. | No change to the substantive finding — stays **SOURCE CLAIM/UNKNOWN**. Bibliographic detail (vol/issue/pages) is now **FACT** (RePEc-confirmed). |
| Kelley & Tetlock (2013) — ~20-trading-day predictive horizon, no reversal at 60 days | **Still unverified.** Same RePEc no-abstract result; JoF full text is subscription-only. | No change — stays **SOURCE CLAIM/UNKNOWN**. |
| Harvey, Liu & Zhu (2016) — ~316 factors catalogued; recommended t-stat threshold ~3.0 | **Partially verified** via NBER's own public abstract (WP 20592). The abstract explicitly states "a newly discovered factor needs to clear a much higher hurdle, with a t-ratio greater than 3.0." It does **not** state an exact factor count — only "hundreds of papers and hundreds of factors." | **t>3.0 threshold upgraded to FACT** (direct quote from NBER's public abstract). **"~316 factors" stays SOURCE CLAIM/UNKNOWN** — not in the abstract, not independently verified against the full text. A separately-sourced "FDR≤1% ⇒ t-hurdle 3.39" figure also stays **SOURCE CLAIM**, not primary-verified. |
| Lakonishok, Shleifer & Vishny (1992) — 769 pension funds, 1985–1989, no substantial herding except small stocks | **Verified** via NBER's own public abstract page (WP 3846). | Upgraded to fully-confirmed **FACT/EMPIRICAL EVIDENCE**. |
| Krohn, Sushko & Synsatayakul (2023), BIS WP 1154 — foreign/local-financial/local-non-financial three-way decomposition, momentum reinforcement | **Verified** via BIS's own public working-paper abstract page. Note: page content reached the fork as an LLM paraphrase of the page, not a copy-pasted verbatim quote — substance is now primary-sourced, exact wording should be treated as approximate. | Upgraded from SOURCE CLAIM to **EMPIRICAL EVIDENCE**. |
| (Bonus, time-permitting) "Revisiting Boehmer et al. (2021)" arXiv reassessment | **Verified** via direct arXiv/ar5iv fetch. Confirms: original sample 2010–2015 vs. later 2016–2021; large-cap predictability disappears in the later sample; full-sample long-short strategy becomes statistically insignificant; small-cap one-week alpha falls from 0.437% to 0.143%. | Upgraded from SOURCE CLAIM to **EMPIRICAL EVIDENCE**, with the specific decay numbers now stated (previously "exact numbers UNKNOWN"). |
| Ülkü & Weber (2014) | Not re-fetched this pass (already directly fetched and flagged highest-confidence in the original review). No new red flags found on re-reading the existing summary. | **Unchanged.** |

All six upgrades/attempts above were applied as small, precise edits directly to
`ALPHA_RESEARCH_LITERATURE_REVIEW.md` (§3.4, §3.5, §3.9, §10) — no other content in that file was
touched.

**Net effect on confidence**: the two claims most directly relevant to a "retail/individual flow
predicts returns" style hypothesis (Chordia-Subrahmanyam, Kelley-Tetlock) remain **unverified
SOURCE CLAIM**, which is a material reason (see §2) that no hypothesis below is built as a direct,
unqualified restatement of either paper's specific numeric claims. The two claims most relevant to
a **foreign-flow / investor-type-decomposition** hypothesis (BIS WP 1154, LSV 1992) are now
primary-verified, which is why the admissible hypothesis set below leans on that evidence more
heavily than on the retail-imbalance literature.

---

## 2. Final Admissible Hypothesis Set (3 hypotheses)

Conservative by design: 3, not 5 — every additional hypothesis considered and rejected is listed in
§4 (Explicit Exclusions) with the reason it was not admitted, rather than padded in here to reach a
target count.

### H1 — Lagged aggregate net flow predicts next-day return, but the effect is price-pressure (temporary), not information-based

- **Economic mechanism**: inventory/price-pressure (temporary), per Grossman-Miller (§3.1) and the
  specific pattern Chordia-Subrahmanyam report (§3.2) — a positive lagged-imbalance-to-return
  relationship that **reverses sign once contemporaneous imbalance is controlled for**.
- **Feature definition**: signed net aggregate broker flow (buy value − sell value) / total traded
  value, at t−1.
- **Expected direction**: positive coefficient on lagged flow predicting the t+1 return in a
  regression that does **not** control for contemporaneous (t) flow; that coefficient should
  **attenuate toward zero or reverse sign** once contemporaneous-day flow is added as a control.
- **Forward-return horizon**: **t+1 only** (single trading day), pre-registered — not a horizon
  scan.
- **Required controls**: contemporaneous (t) net flow; standard liquidity/turnover control;
  contemporaneous same-day return reported separately per §3.3's mechanical-relation warning.
- **Falsification criterion**: refuted if (a) the lagged-flow coefficient is not statistically
  distinguishable from zero once t>3.0-threshold multiplicity correction (§5, Phase C) is applied,
  even in the uncontrolled specification, OR (b) the coefficient does **not** attenuate/reverse when
  the contemporaneous-flow control is added (i.e., the pattern is flat rather than showing the
  price-pressure signature the mechanism predicts).
- **Literature support**: Chordia & Subrahmanyam (2004), §3.2 — **SOURCE CLAIM, unverified this
  pass** (see §1 table). Confidence in this hypothesis should be held at "moderate, pending
  independent replication of the source claim itself," not treated as resting on a confirmed
  primary finding.
- **Applicability**: **EXTRAPOLATED.** Chordia-Subrahmanyam is a NYSE study; §3.10 found no
  Indonesia-specific stock-level broker-flow study of any kind. This is a genuinely novel test for
  IDX, not a replication of an established local finding.

### H2 — Foreign net flow predicts short-horizon forward returns via a mixed information/momentum-feedback channel

- **Economic mechanism**: mixed information-based and herding/positive-feedback (per BIS WP 1154,
  §3.5, now EMPIRICAL EVIDENCE-tagged: "innovations in foreign order flow... predict future
  returns" [information] and "foreign investors engage in momentum trading" [feedback] are both
  reported for the same market).
- **Feature definition**: signed net foreign broker flow / total traded value, at t (contemporaneous
  observation used as the predictor for **forward**, not same-day, returns — i.e., cumulative return
  from t+1 through the pre-registered horizon).
- **Expected direction**: positive — net foreign buying at t predicts positive cumulative return
  over t+1..t+5.
- **Forward-return horizon**: **cumulative t+1 through t+5** (5 trading days), pre-registered as a
  single fixed window — not a horizon scan across 1/5/10/20 days.
- **Required controls**: contemporaneous same-day return (per Ülkü & Weber's simultaneity/
  endogeneity warning, §3.5 — flow and return can jointly respond to a common shock within the same
  day; failing to control for this risks mistaking a contemporaneous, bidirectional relationship for
  one-directional forward predictability); lagged domestic/local flow if available as a covariate.
- **Falsification criterion**: refuted if the cumulative t+1..t+5 return, conditional on t-flow, is
  not statistically distinguishable from zero after controlling for contemporaneous same-day return,
  under the same elevated (t>3.0-class) threshold used for H1 — i.e., if the apparent effect is
  fully explained by the contemporaneous/mechanical relationship rather than surviving as a genuine
  forward-looking one.
- **Literature support**: Krohn, Sushko & Synsatayakul (2023), BIS WP 1154, §3.5 — **EMPIRICAL
  EVIDENCE, verified this pass** (see §1). Supporting/consistent: Vo (2017), Vietnam, §3.5 —
  **SOURCE CLAIM**, positive foreign feedback trading, not independently re-verified.
- **Applicability**: **EXTRAPOLATED.** Both supporting studies are Thailand and Vietnam
  respectively — single-country, not a cross-market consensus, and neither is Indonesia. §3.10:
  genuinely no Indonesia-specific evidence either way.

### H3 — Domestic flow follows (lags) foreign flow direction, rather than leading it

- **Economic mechanism**: herding/feedback — domestic investors partially mimic foreign flow
  direction with a lag, per BIS WP 1154's three-way decomposition (§3.5, now EMPIRICAL EVIDENCE):
  "local financial investors tend to mimic foreign investor trading... with observable lag," while
  local non-financial investors instead act as liquidity-providing counterparties.
- **Feature definition**: lagged foreign net flow (t−1) as the predictor; domestic (non-foreign)
  net flow direction at t as the outcome. **This is a flow→flow mechanism-validation test, not a
  flow→return test** — its purpose is to establish whether the mediating mechanism behind H2 (foreign
  flow leads, domestic flow follows) actually holds in IDX data, which materially affects how H2's
  result, if any, should be interpreted.
- **Expected direction**: positive — lagged foreign net flow direction correlates with same-direction
  domestic net flow at t.
- **Forward-return horizon**: not applicable (flow→flow test); the lag itself is fixed at **1 trading
  day**, pre-registered (the BIS abstract confirms a lag exists but this review did not extract an
  exact number of days from the primary source — 1 day is a deliberately conservative, literal
  reading of "with observable lag," not a value taken from a verified specific number).
- **Required controls**: contemporaneous local market return at t (to distinguish "domestic investors
  following foreign flow" from "domestic investors simply following the same price move foreign
  investors are also reacting to").
- **Falsification criterion**: refuted if domestic flow direction at t is not correlated with lagged
  foreign flow direction once contemporaneous return is controlled for.
- **Literature support**: Krohn, Sushko & Synsatayakul (2023), BIS WP 1154, §3.5 — **EMPIRICAL
  EVIDENCE, verified this pass**.
- **Applicability**: **EXTRAPOLATED**, and additionally **conditional on data availability** — this
  hypothesis presumes IDX broker-flow data can support a foreign vs. domestic (and ideally
  domestic-financial vs. domestic-non-financial) split analogous to Thailand's. Whether IDX broker
  codes actually support this granularity is a data-availability question this literature-review
  track does not resolve and did not check (no data was touched, per scope).

---

## 3. Finalized Research-to-Empirical-Test Map (IDX80 broker-flow / Stockbit-flow)

| Phase | Test | Hypothesis | Horizon | Mechanism tested | Multiplicity control |
|---|---|---|---|---|---|
| **A0** | Contemporaneous baseline: same-day net flow vs. same-day return | *(control, not a hypothesis — §3.3)* | t (same day) | Mechanical/definitional | N/A — required diagnostic run before A1, not itself subject to the Phase C correction |
| **A1** | Lagged aggregate flow → t+1 return, with vs. without contemporaneous-flow control | **H1** | t+1 | Inventory/price-pressure (expected temporary/reversing) | Counted as 1 of 3 pre-registered tests in the Phase C correction |
| **B1** | Foreign net flow (t) → cumulative t+1..t+5 return, controlling for contemporaneous return | **H2** | t+1..t+5 (cumulative, fixed) | Mixed information + herding/feedback | Counted as 1 of 3 |
| **B2** | Lagged foreign flow (t−1) → domestic flow direction (t), controlling for contemporaneous return | **H3** | N/A (flow→flow, 1-day lag) | Herding/feedback (mediation check for H2) | Counted as 1 of 3 |
| **C1** | Multiplicity-corrected synthesis across A1, B1, B2 | — | — | — | Apply an explicit correction across exactly these **3** pre-registered tests (Harvey-Liu-Zhu-style elevated bar, t>3.0 minimum per §1's verified threshold, or an equivalent documented FDR/Bonferroni procedure) **before** any result is described as evidence of an edge. Do not add a 4th test to this synthesis without re-running this gate. |
| **C2** *(optional, only if pre-registered before any data is seen)* | Regime split (bull/bear, or high/low volatility) of A1/B1/B2 | — | Same as parent test | Regime-dependent (per §3.8) | Each regime cell adds to the multiplicity grid — must be specified in the same pre-registration as A1/B1/B2, not appended after seeing results (§4) |

---

## 4. Explicit Exclusions — not admissible without a new, documented research justification

1. **Any horizon other than the ones pre-registered above** (t+1 for H1; cumulative t+1..t+5 for
   H2; 1-day lag for H3). No scanning across 1/5/10/20-day horizons looking for "the one that
   works."
2. **Cumulative-volume-delta z-score or any other vendor/practitioner-engineered flow feature**
   (§3.7) — zero academic validation found for this specific construction; TradingView/vendor-blog
   sourced only.
3. **Any regime, volatility, or bull/bear split not specified in the same pre-registration as
   A1/B1/B2** (Phase C2 above) — no post-hoc regime slicing to locate a subsample where an
   otherwise-null result becomes significant.
4. **Using Indonesia macro/aggregate foreign-flow-vs-JCI-index findings (§3.10) as license for a
   stock-level claim.** Macro-level Granger-causality or index-level foreign-flow studies do not
   transfer to a stock-level broker-flow claim without independent testing — and no such
   stock-level Indonesia study was found in this review.
5. **Any hypothesis asserting "institutional herding" at quarterly (or any non-daily) frequency.**
   LSV (1992) found a null result at U.S. quarterly-institutional frequency (now fully verified,
   §1); the only supporting evidence for herding/feedback effects in this review is at **daily**
   frequency in emerging markets (Thailand, Vietnam). A quarterly-frequency institutional-herding
   hypothesis is explicitly excluded from the admissible set on this basis.
6. **A standalone hypothesis modeled directly on Kelley-Tetlock's ~20-trading-day retail-imbalance
   predictability window.** Excluded for two compounding reasons: (a) the specific coefficients and
   horizon claim remain unverified SOURCE CLAIM even after a second verification attempt (§1); (b)
   the closest verified analogue — the Boehmer et al. successor study — is now **confirmed
   (EMPIRICAL EVIDENCE)** to have decayed to statistical insignificance for large-cap stocks by
   2016–2021, meaning the underlying US effect itself may no longer exist in its origin market
   today. Extrapolating a possibly-already-decayed, never-independently-verified effect fresh into
   IDX is a materially weaker basis than H1–H3. A retail-imbalance hypothesis could be reconsidered
   later, but only with its own dedicated verification pass, not folded into this handoff.
7. **Any further granular investor-type split** (e.g., domestic-institutional vs. domestic-retail,
   or broker-tier splits) beyond the foreign/domestic split used in H2/H3, unless IDX broker data is
   confirmed to support it **and** a new hypothesis is pre-registered through this same
   literature-to-design gate.
8. **Reporting any A1/B1/B2 result without also reporting the A0 contemporaneous baseline
   separately** — per §3.3, a positive contemporaneous finding must never be presented as if it were
   evidence of forward predictability.
9. **Applying any significance threshold below t≈3.0** (or an equivalently documented FDR
   procedure) to any of H1–H3 without explicitly justifying the deviation — the t>3.0 recommendation
   is now primary-verified (§1), so falling back to the conventional t≈2.0 threshold requires an
   explicit, documented reason, not silent default.

---

## 5. Handoff Requirements for ZCode (empirical-execution track)

Before running **any** test from H1/H2/H3 above, ZCode must confirm/ensure:

1. **PIT-only data.** The existing "P2" data-quality exclusion stays excluded from strict/
   reconstructed research eligibility exactly as currently defined in the repo. This handoff does
   **not** resolve, evaluate, or authorize touching P2 — that is out of scope for this literature
   track and remains a separate, still-open data-quality question.
2. **Contemporaneous vs. forward results reported separately, always.** The A0 baseline must be run
   and reported alongside any of A1/B1/B2 — never substitute a contemporaneous correlation for a
   forward-predictability claim (§3.3, §4.8).
3. **The exact multiple-testing correction from §3, Phase C1** applied across exactly the 3
   pre-registered tests (A1, B1, B2) — t>3.0-class threshold or an equivalent documented FDR/
   Bonferroni procedure — computed and reported **before** any of the three results is characterized
   as "a finding."
4. **Regime splits, if run at all, must be exactly the ones pre-registered in Phase C2** — not
   discovered or added after seeing A1/B1/B2 results.
5. **No expansion of the hypothesis, feature, or horizon set beyond H1–H3** as specified in §2,
   without a new, documented research justification — meaning a fresh pass back through this
   literature-review-to-hypothesis gate (this document plus the underlying literature review), not
   an ad hoc addition made mid-analysis.
6. **This document is a research-design-gate output only, not a hypothesis registration.** Before
   any of H1/H2/H3 counts as REGISTERED in the institutional sense, it must be separately entered
   into `research/knowledge` / `docs/research_programs/HYPOTHESIS_REGISTRY.md` via the repo's own
   `set_status()` gateway, per `docs/research_os/RESEARCH_PROTOCOL.md` and the repo's Research
   Master Plan invariants (append-only registry, no capital-facing status transition without a
   verifiable evidence receipt). This handoff document performs none of that registration itself.
7. **Do not use Indonesia macro/aggregate-flow evidence to justify skipping or loosening the
   pre-registration discipline above** — the absence of any Indonesia-specific stock-level prior
   study (§3.10) means H1–H3 are genuine first tests in this literature for this market, which
   argues for *more*, not less, discipline (§3.9, §5 of the literature review).
8. **Zero vendor/broker/market-data API calls, database writes, or PIT-table modifications are
   authorized by this handoff.** ZCode's own execution phase governs those actions separately, under
   the repo's existing research-governance rules — this document only defines what is admissible to
   test, not how to run it.
