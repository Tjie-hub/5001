# Rule-First Edge Research — Literature Gate & Candidate Rules

**Date:** 2026-09-24 · **Status:** method **adopted by D-055** (Owner, 2026-09-24) and implemented in
`research/rulecard/`. **Not a registration.** No backtest, no DB read, no outcome data touched. Nothing
here consumes a family slot. Builds on `ALPHA_RESEARCH_LITERATURE_REVIEW.md` (flow-only scope) and widens it to the
method itself and to non-flow anomalies.

**Evidence tags.** **[V]** verified this pass from the source's own abstract/page (or NBER / RePEc /
publisher listing). **[V2]** verified via a secondary summary page (CFA Digest, Alpha Architect).
**[M]** from prior knowledge, *not* fetched this pass — treat as a pointer, re-verify before citing
in a registration.

---

## 0. Why this document exists — the diagnosis

State of the program on 2026-09-24:

| Source of hypothesis | Tests | Outcome |
|---|---|---|
| Microstructure / broker flow (no IDX literature prior, ~1 yr data) | HYP-PM-0001, 0003, 0004, 0005, 0006, 0009, BROKER-001 | all FAILED / NOT CONFIRMED / INVALID |
| Auction / reconstitution (strong literature prior, symmetric spec) | HYP-PA-0001 | FAILED pooled; **ADD-side +1.89%, WCB p 0.013** (post-hoc, unregistered) |
| Chart patterns (practitioner folklore, ~12 arms) | pattern scan 2026-09-17 | every mean-reversion pattern is a **significant anti-edge**; only continuation positive, 2025-inflated |
| Classic factors (literature prior) | T1 trend (fwd), VOLEX-001 (fwd), VOLEX-SN | T1 +0.93%/trade ex-2025 t 2.83; VOLEX-001 ≈ +0.30%/mo t 2.59 after look-ahead fix; VOLEX-SN refused |

Two readings follow, and both are quantitative, not opinion:

1. **The survivors all came from published, replicated anomaly families** (trend, low-volatility).
   Every candidate sourced from either (a) mechanisms with no prior in any market-like-IDX literature
   or (b) chart folklore died. This is what the literature predicts: the probability a tested
   hypothesis is true is dominated by its **prior**, not by the rigor of the test (Harvey 2017 [V];
   Jensen-Kelly-Pedersen 2023 [V]). Rigor was never the bottleneck — the repo's controls are strong.
   **Hypothesis sourcing was.**
2. **Every in-house positive is on the "avoid" side** (avoid high-vol, avoid failed-breakdown,
   avoid sweeps, avoid wedge-pops). That is exactly the signature the short-sale-constraint
   literature predicts for a market with no practical shorting (Miller 1977 [M]; Stambaugh-Yu-Yuan
   2012 [V]: anomalies are driven by the short leg after high sentiment; the long leg shows no
   consistent relation). §4 turns this into the program's organising thesis.

**Throughput note (critical).** Arnott-Harvey-Markowitz make "management understands that most tests
will fail" a protocol item (7b) [V]. With 9 registrations in ~10 weeks (7 executed), each wrapped in
several 15–37 KB draft/power/audit documents, the cost per test is the constraint. The statistically load-bearing controls
are few (§2, R1–R10) and all fit on one Rule Card (§3). Family-slot semantics, custody tiers and
multi-document audit chains protect nothing that the Rule Card plus the trial ledger does not already
protect. Recommend: keep the ledger, freeze-then-run, and PIT discipline; **replace the
DRAFT→POWER→REGISTERED→AUDIT document chain with one Rule Card per candidate** for Tier-R rules.

---

## 1. Pattern vs Rule — the operational definition

A **pattern** is a shape recognised on a chart. Its unit of analysis is *one chart*; it is validated
by example; it fires *endogenously* on the price path; the detector has discretion. The in-house scan
proved the failure mode: every refuted pattern "worked" on BRPT, which sat at the 91st percentile of a
per-ticker distribution where only 35% of tickers were positive.

A **rule** passes all five tests:

| # | Test | Why it matters |
|---|---|---|
| P1 | Writable as a deterministic function of point-in-time columns with **every parameter fixed from the literature**, no discretion | removes researcher degrees of freedom (AHM 3c, 6b [V]) |
| P2 | **Every eligible stock gets a score at every formation date** (a characteristic), or the trigger is an **exogenous dated public event** (index change, rights issue) — not a price-path shape | kills cherry-picked occurrences; makes the cross-section, not the chart, the unit |
| P3 | Prediction is **cross-sectional and relative**: bucket vs the rest of the same universe on the same dates | strips market beta and era effects (2025) out of the estimand |
| P4 | **Dose-response**: returns are monotone across quintiles of the score (Patton-Timmermann MR test [V]) | a real characteristic effect is graded; an artifact lives only in the extreme cell |
| P5 | The mechanism predicts **at least one heterogeneity** (where it should be stronger/weaker) that is tested with a pre-declared sign | a causal claim must imply more than its headline (López de Prado causal protocol [V]) |

Lo-Mamaysky-Wang (2000) show patterns *can* be quantified via kernel regression and carry some
conditional-distribution information [V]; but rule universes tested with data-snooping controls lose
their significance and are fully offset by low transaction costs (Sullivan-Timmermann-White 1999,
26 rules × 100 years DJIA [V]; Bajgrowicz-Scaillet 2012, DJIA 1897–2011: best rules not selectable ex
ante, performance "completely offset by the introduction of low transaction costs" [V]). Hsu-Kuan
find significant technical-rule profits after snooping controls and costs only in the younger indices
(NASDAQ Composite, Russell 2000), none in DJIA/S&P 500 [V]. That is the closest analogue to IDX, and it
is why a trend *rule* (T1) is plausible here while pattern *detectors* are not.

---

## 2. The method rules (quantitative gates)

Each rule states its threshold, its source, and how it maps onto existing repo machinery.

**R1 — Mechanism first, and name the loser.** Before any data: who is on the other side, why they
keep losing, and why capital does not remove it (the barrier). AHM 1a/1b: "Did the economic
foundation or hypothesis exist before the research was conducted?" [V]. Maps to the repo's barrier
classes (M4 inventory, M5 behavioural, M6 market design).

**R2 — Parameters come from the paper, not from IDX data.** MAX uses the 5 highest daily returns over
21 sessions because Bali-Cakici-Whitelaw did; 52-week-high uses 252 sessions because George-Hwang did.
A parameter chosen on IDX data is a trial (R8). Robustness variants are declared up front and **never
used for selection**.

**R3 — Hurdle depends on prior (tiered).** Harvey (2017) proposes the minimum Bayes factor,
MBF = exp(−t²/2), to turn a t-stat into a posterior [V]. Computed:

| t | MBF | P(null \| data), prior P(true)=50% | prior 25% | prior 10% |
|---|---|---|---|---|
| 2.0 | 0.135 | 11.9% | 28.9% | 54.9% |
| 2.5 | 0.044 | 4.2% | 11.6% | 28.3% |
| 3.0 | 0.011 | 1.1% | 3.2% | 9.1% |

So one false-discovery budget (~10%) gives two hurdles:

- **Tier R (replication)** — the rule, with literature-default parameters, has ≥2 independent
  published replications including ≥1 emerging market. Prior ≈ 50% (JKP: 82% of factors replicate,
  "work out-of-sample in … 93 countries", posterior FDR 0.1% [V]; McLean-Pontiff: 26% OOS decay [V2]).
  **Hurdle: one-sided t ≥ 2.0 on the single primary estimand AND same sign in both pre-declared halves.**
- **Tier N (novel)** — anything else (IDX-specific mechanism, practitioner idea, in-house discovery).
  Prior ≤ 10%. **Hurdle: t ≥ 3.0** (HLZ [V]; ≥ 3.4 cross-sectional / 3.8 time-series if the idea came
  from a search, Chordia-Goyal-Saretto [V]) **plus DSR ≥ 0.95** with every trial counted.

HYP-PM-0012 (failed-breakdown anti-edge) is correctly Tier N — it came from a scan.

The minimum Bayes factor only *calibrates* the two thresholds to one false-discovery budget; each test is
still a pre-registered frequentist severity test, so ADR-L1-002 (critical rationalism, not Bayesian
epistemology) stands (D-055 §4).

**R4 — Exactly one primary estimand, cross-sectional, vs an equal-weight liquid benchmark.**
For Tier R the primary estimand is **the published one** (e.g. top-minus-bottom decile) — that is what
makes it a replication, and it is the only estimand whose σ and effect size can be sourced for R5. The
IDX-usable form — signal bucket **minus the rest of the same liquid universe** — is the single
pre-declared **deployment test**, run on the same frozen script: it decides whether a long-only book
can use the effect, not whether the effect exists. Entry at next open, Newey-West HAC t. Not IHSG — the
in-house audit measured the IHSG benchmark bias at +0.35%/20d (t 3.49). Book-level uplift is *derived*,
never tested separately (R4b).

**R4b — Test the spread, not the overlay.** Excluding a bucket of weight *w* that underperforms the
rest by *d* lifts an EW book by only *d·w/(1−w)*: a 1.6%/mo decile spread becomes **0.18%/mo** of book
uplift, below the MDE of most samples. Overlays are sized from the spread; they are not evidence.

**R5 — Power before data; inadmissible if underpowered.** MDE = t\* · σ / √N. Available monthly
history ≈ 88 months pre-2021 + 67 months 2021–26 = 155 (from the VOLEX re-measurement). Power 80%
needs an *expected* t of t\* + 0.84:

| spread σ (%/mo) | true effect needed, N=155, t\*=2 | N=67, t\*=2 | N=155, t\*=3 |
|---|---|---|---|
| 0.75 (book-level overlay, VOLEX-like) | 0.17 | 0.26 | 0.23 |
| 3.5 (decile spread; backed out of Julianto-Ekaputra 2020: −1.6%/mo, t −3.57, 60 mo) | 0.80 | 1.22 | 1.08 |

**Noise floor (D-056, enforced at freeze by the code):** a published σ comes from the paper's
universe; ours has ~12–15 names per decile. `cli power` measures σ of the primary spread under random
buckets on our panel (the rule's signal is never called); the power table uses max(literature σ,
noise floor). First measurement (RC-0001, backfill): decile ~6.5%/mo, quintile ~4.6%/mo — so with
~245 months a decile sort needs a true spread of ~1.2%/mo, a quintile sort ~0.85%/mo.

Rule: **plan with the literature effect × 0.5** (decay haircut, R9). If haircut effect < the 80%-power
threshold for the declared N, the rule is **not run** — it is recorded as "underpowered, not tested".
Corollary for forward tests: a 0.8%/mo effect with σ 3.5 reaches expected t ≈ 1.1 after 24 months. **A
24-month forward test cannot confirm significance; it can only confirm implementability and sign.**
Its decision rule should be written that way.

**R6 — Monotonicity is required, not decorative.** Quintile returns (deciles are averaged in pairs:
with 150–300 names, adjacent deciles are too noisy for a min-over-all-differences test) must pass the
MR test in the predicted direction at p < 0.10 (Patton-Timmermann 2010; R package `monotonicity` [V]).
The card declares the **shape**: `full` (graded across every bucket, e.g. value) or `tail` (graded from
the median to the used end, for mechanisms that act in the tail such as lottery demand — requires a
written justification). A pure step confined to the extreme bucket — what a binary chart trigger
produces — fails both and is re-classified as a pattern (verdict FAIL_NOT_MONOTONE). On synthetic panels
(4 seeds) it passed every graded effect and let a pure step through in 1 of 8 seed × shape cases — about
its α, as designed.

**R7 — ≥1 mechanism fingerprint, pre-declared sign.** e.g. lottery overpricing must be stronger in
low-ADV/low-price names and after high-sentiment months. The fingerprint's sign is part of the pass
condition. If headline passes and fingerprint has the wrong sign, verdict = "effect present, mechanism
unconfirmed" — no promotion.

**R8 — Count every trial; no combinations in discovery.** Every variant computed goes in the ledger,
including ones never reported (AHM 2a/2c [V]). Selecting the best *k* of *n* signals is as biased as the
best one of *nᵏ* (Novy-Marx 2016 [V]). Combining signals is allowed only after each component passes
alone. Minimum backtest length: with 5 years of data, >45 independent configurations virtually
guarantees an in-sample Sharpe of 1 with an OOS Sharpe of 0 (Bailey-Borwein-López de Prado-Zhu 2014
[V]). Computed for IDX: the pattern scan's ~12 arms on ~5 years give an expected best annual Sharpe of
**≈0.74 under no skill at all**. PBO/CSCV [V] is the check when a parameter grid is unavoidable.

**R9 — Plan on decay.** McLean-Pontiff: 97 anomalies, returns 26 pp lower out-of-sample and 58 pp lower
post-publication (0.582 → 0.402 → 0.264 %/mo) [V2]. Hou-Xue-Zhang: 65% of 452 anomalies fail |t| ≥ 1.96
once microcaps are controlled; 82% fail at 2.78; 96% of the trading-frictions category fail [V]. Planning
effect = published effect × 0.5; capacity-sensitive (microcap) effects × 0.3.

**R10 — Implementability is part of the estimand.** Next-open entry; 0.60% round trip at the rule's
own turnover; ARA/ARB cells treated as unfillable; **no symmetric (±N) tradeability window** (the VOLEX
lesson: "a result that holds only with a filter the live system cannot apply is not a result");
report ex-2025 and per-year alongside the full sample.

**Survivorship direction.** The corpus holds only names still listed in 2026-09. For **avoid-side**
rules this biases *against* finding the effect (the worst avoid-bucket members delisted and are
missing) — conservative. For **long-side** rules it inflates. State the direction on every card.

---

## 3. The Rule Card (replaces the draft/power/registered chain — D-055)

Template: `RULE_CARD_TEMPLATE.yaml` (same directory). A card lives in
`docs/research_programs/<program>/rulecards/<ID>/` next to its `rule.py`, which defines
`load_panel(ctx)`, `signal(panel)` and optionally `control(panel)`. Everything else — universe, fills,
buckets, benchmark, statistics, checks and the verdict — is the framework's, so a script cannot move its
own goalposts.

```
python -m research.rulecard.cli validate CARD.yaml    # every problem at once; PENDING allowed
python -m research.rulecard.cli dry      CARD.yaml    # structure + no-return checks; no freeze needed
python -m research.rulecard.cli freeze   CARD.yaml --owner "who, when, where recorded"
python -m research.rulecard.cli run      CARD.yaml    # once -> RESULT.json, VERDICT.md, ledger line
```

`FREEZE.json` pins the card, the script and the framework by sha256; any change after the freeze makes
`run` refuse, and so does an existing `RESULT.json`. Every dry and real run executes the seven mandatory
checks (LA-1 look-ahead, ZV-1 zero-volume, ID-1 degenerate predictor, EX-1 zeroed outcome, FILL-1
next-open fill, BM-1 placebo, SPL-1 split band) — each reproduces a defect this repo already shipped, and
`tests/test_rulecard_checks.py` proves each one fails on its defect. Verdicts, in precedence order:
INVALID · FAIL / INCONCLUSIVE_UNDERPOWERED · FAIL_NOT_MONOTONE · EFFECT_PRESENT_MECHANISM_UNCONFIRMED ·
PASS_NOT_DEPLOYABLE · PASS (D-055 §6 maps them to lifecycle states).

---

## 4. Program thesis for a long-only IDX book (proposed, for the Owner)

> **In a short-constrained, retail-heavy market, mispricing concentrates in the overpriced tail.
> The exploitable edge for a long-only book is mostly *avoidance* of predictably overpriced names,
> plus a smaller long-side tilt toward names where investors under-react.**

Testable implications (each becomes a fingerprint, R7):
- **T-a.** For every Tier-R characteristic, the bucket-minus-rest spread is larger in magnitude on the
  overpriced side than on the underpriced side (Stambaugh-Yu-Yuan [V]).
- **T-b.** Overpriced-side spreads are larger after high-sentiment months (IHSG trailing-3-month return
  in its top tercile, or retail net-buy proxy).
- **T-c.** Overpriced-side spreads are larger in low-ADV, low-price names.

In-house facts — **corrected 2026-09-24** by `docs/research_programs/AUDIT_2026-09-24_RESULT_VALIDITY.md`:
- The first draft cited "every significant pattern-scan result is an anti-edge". **That no longer stands
  as evidence.**
  - The scan's endpoint charged the 0.60% round trip to the signal leg only, so a pattern with no
    information scores −0.60%.
  - Its t used entry-date clusters over overlapping holds.
- Re-measured gross with overlap-robust t, only the failed breakdown against the EW liquid book is
  confirmed so far:
  - h20: −0.89%, t −3.6 to −4.4.
  - h5: −0.45%, t −3.7 to −4.5.
- The same pattern against IHSG is **not** confirmed (−0.86%, t −1.7 to −2.0). The other arms are
  unmeasured on that basis until `P-M/validity_audit/validity_audit.py` §F runs.
- VOLEX exclusion survives only as the pooled top-200 construction (ex-ante +0.30%/mo, t 2.6). The
  sector-neutral construction does not survive.
- OJK's IDX transaction study (2013–15, 582 stocks, 285 million transactions) finds that individuals
  trade contrarian (sell winners, buy losers) while institutions trade momentum [V].
- **Conclusion.** The thesis rests on the external literature. The in-house scan is not support for it.

---

## 5. Step 0 — external prior check before touching our data

Global Factor Data (JKP) publishes free (CC BY-NC 4.0) characteristic-managed portfolio returns for
153 characteristics, 13 themes, 93 countries and regions; daily/monthly; capped-VW, VW or EW; country
factors require ≥5 stocks per leg and ≥60 months [V]. **Indonesia's inclusion was not confirmed this
pass** (the country dropdown is dynamic) — first action is to check it.

Discipline point: JKP-Indonesia overlaps our stocks and years, so using it to *choose* rules is a look at
the same sample. Therefore:
- **Choose** rules using the JKP **emerging-markets / Asia-EM ex-Indonesia** series (independent).
- **Read JKP-Indonesia only after** our frozen run, as a third-party replication of the same market.

Characteristics to pull (JKP names from memory [M] — confirm on download): `rmax5_21d` (MAX),
`prc_highprc_252d` (52-week high), `chcsho_12m` (net share issuance), `ret_12_1` (momentum),
`ret_1_0` (short-term reversal), `ivol_capm_21d`, plus the value and profitability themes.

---

## 6. Candidate rules — ranked

Constraints applied: long-only; swing/mid-term holding (weeks–months, per the Owner); 0.60% round trip;
OHLCV ≈2013–2026 (155 months incl. pre-2021 backfill); broker flow only 2025+; **no PIT fundamentals**.
Rank = prior × data readiness × capturability × power.

### C1 — Lottery avoidance (MAX) · Tier R · **rank 1**

- **Rule.** At each month-end formation, MAX5 = mean of the 5 highest daily returns over the prior 21
  sessions. Rank the liquid universe; the top decile is the **avoid bucket**. Price-limit variant: count
  ARA-capped days (a capped day's return understates demand) — J. Financial Markets 2018 shows a
  limit-modified MAX predicts returns and is "not a manifestation of the idiosyncratic volatility
  effect" [V].
- **Mechanism / loser.** Retail lottery preference overprices stocks with extreme recent up-days;
  short-sale constraints stop correction (M5 + M6 barrier).
- **Literature.** Bali-Cakici-Whitelaw 2011 [M]; **IDX-specific: Julianto & Ekaputra (2020), IDX
  2013-07→2018-06, high-minus-low MAX decile −1.6%/mo, t −3.57, FF3-adjusted also −1.6%; high-MAX decile
  raw −0.7%/mo** [V]; the paper notes the IDX effect exceeds the US −0.65%.
- **Estimand.** Primary (replication): high-minus-low MAX decile, monthly, EW, next-open entry,
  predicted negative. Deployment test: avoid-decile minus rest-of-universe, predicted negative. Thesis
  T-a adds: |high − middle| > |low − middle|.
- **Power.** σ ≈ 3.5%/mo (backed out of the IDX paper: 1.6·√60/3.57). Planning effect 1.6 × 0.5 =
  0.8%/mo vs 0.80 needed at N=155, t\*=2 → **admissible, marginally**. On 2021–26 alone (N=67) it is
  underpowered — must use the full 155 months with the halves pre-declared. The deployment test is
  weaker by construction (the paper gives no σ for decile-minus-rest; a high-MAX decile at −0.7%/mo raw
  implies a smaller gap to the rest than to the low decile), so a pass on the primary with a fail on
  deployment is a live outcome and must be written into the kill rule in advance.
- **Fingerprints.** T-b (after high-sentiment months), T-c (low-ADV/low-price), MR monotone across
  deciles.
- **Overlap.** Correlated with Parkinson volatility (VOLEX). Must show incremental effect: primary
  run within volatility terciles (double sort), declared up front. **Family: likely `{V1}`
  (determined by D-053, not opened) — Owner call.**
- **Survivorship:** conservative (avoid side).

### C2 — Share-issuance avoidance (rights issue / private placement) · Tier R · **rank 2**

- **Rule.** Avoid names with a rights issue (HMETD), private placement (PMTHMETD) or warrant-driven
  share creation announced in the prior 12 months; announcement date = formation eligibility date.
- **Mechanism / loser.** Managers issue when overvalued (market timing); buyers of the new supply
  lose. Barrier: short constraints + slow diffusion.
- **Literature.** McLean-Pontiff-Watanabe 2009, 41 non-US countries: issuance predicts returns with
  "greater statistical significance than either size or momentum", robust in small and large firms,
  and — decisive for a long-only book — "driven more by low returns after share creation rather than
  positive returns following share repurchases" [V]. Indonesian event studies found are short-window
  (±5 days, N=42) and not informative about the 12-month drift [V].
- **Data.** `corporate_action_events` holds rightissue / warrant / bonus types 2009–2026 with raw_json
  (class B) — usable, but announcement vs effective date must be verified PIT first.
- **Estimand.** MPW use a continuous change-in-shares-outstanding measure; that needs a shares
  outstanding history we have not confirmed. The binary issuer-vs-rest bucket is an IDX **proxy** — say
  so on the card (a proxy replication carries less of the published prior). **Power:** event density
  unknown — count issuers per month before writing the card; if <10 per month on average, move to an
  event-time estimand with clustering by month.
- **Fingerprint.** Stronger for purposes other than debt restructuring; stronger in low-ADV names.
- **Family:** new (corporate-finance). Owner call.

### C3 — 52-week-high proximity (long side) · Tier R · **rank 3**

- **Rule.** PTH = close / max(high, 252 sessions). Long the top quintile (nearest the high), monthly.
- **Mechanism / loser.** Anchoring: investors under-react to good news near the 52-week high; sellers
  at the anchor lose. Fits the swing/mid-term horizon and uses the long leg.
- **Literature.** George-Hwang 2004 [M]; Liu-Liu-Ma 2011: profitable in 18 of 20 international
  markets, significant in 10, not explained by conventional momentum, no long-run reversal — **but
  "no longer significant in most markets once transaction costs are taken into account"** [V].
- **Concern.** Cost-fragile by the source's own finding; survivorship inflates (long side). In-house
  consistency: resistance breakout at 20d, next-open vs EW book +0.81%, t 3.41 (exploratory, Tier-N
  evidence, does not count toward the prior).
- **Family: likely `{T1}` as its 2nd member** — Owner call. Run only after C1/C2.

### C4 — Index inclusion (ADD-side) event drift · Tier R, forward-only · rank 4

- **Rule.** Buy ADD names at the next open after the official announcement; exit at the effective-date
  close.
- **Literature.** Index-effect literature (Harris-Gurel 1986, Shleifer 1986 [M]); Indonesia: LQ45 and
  MSCI inclusions show significant positive returns (24 LQ45 adds, 17 MSCI adds) [V].
- **In-house.** HYP-PA-0001 ADD-side +1.89%, CI95 [+0.67, +3.11], positive in 11/13 review dates —
  **post-hoc subgroup of a failed registration**, so it cannot be its own confirmation. Only
  forward events can confirm it (new registration, P-A family).
- **Power problem.** ~13 review dates in hand; widen the event set (LQ45, IDX30, IDX80, MSCI, FTSE, JII/ISSI)
  before writing the card.

### C5 — Value / profitability / investment · Tier R, **data-blocked** · rank 5

Highest EM prior in the literature: value "in all emerging markets" (Cakici-Fabozzi-Tan, 18 EMs,
1990–2011 [V]); cash-flow-to-price, gross profitability, composite equity issuance and momentum are
"pervasive" in EW and VW sorts (Hanauer-Lauterbach, 28 EMs, 1995–2016 [V2]). **Blocked by the absence of
PIT fundamentals with filing dates.** Action: a data-acquisition item, not a hypothesis.

### Parked or excluded (with the reason — a rule must be *testable*, not just quantifiable)

| Candidate | Why not now |
|---|---|
| 12-1 cross-sectional momentum | Low prior for Indonesia: momentum profits rise with cultural individualism (Chui-Titman-Wei 2010 [V]) and Indonesia scores among the lowest on Hofstede's index [M]; OJK: retail trades contrarian [V]. EM-wide evidence is regional, not country-level (Cakici et al. [V]). Check JKP EM series first. |
| Low-volatility (new variant) | Already live as VOLEX-001; Hanauer-Lauterbach find low-risk (beta) not significant in EM [V2] while Blitz-Pang-van Vliet find a flat-to-negative risk-return relation [V] — mixed. Let the frozen forward test run; do not add a sibling. |
| 1-month reversal | Contradicted in-house: buying weakness is a t −7 to −12 anti-edge. Any test belongs to `{R1}`. |
| Ramadan / calendar effects | Quantifiable but untestable: Ramadan returns are higher across 14 Muslim countries 1989–2007 [V], yet IDX gives ~13 observations. Fails R5 by construction. |
| ARA/ARB limit continuation | Long leg not capturable (queue at ARA is all buyers), short leg illegal in practice — per `data_inventory_v2` part 3. |
| Broker / foreign flow | Tested seven ways, all failed; the literature gap for Indonesia is documented in the flow review. Re-open only with a new mechanism and ≥2 years of PIT flow. |

---

## 7. Sequence (nothing below starts without the Owner)

1. ~~Adopt R1–R10 and the Rule Card~~ — **done, D-055 (2026-09-24)**.
2. **Step 0:** confirm JKP country coverage; pull the EM ex-Indonesia series for C1–C3 and C5; record
   the prior sign/t on each card.
3. **Cards for C1 and C2.** C1 (`P-M/rulecards/RC-0001-MAX/`) is **closed: not tested, underpowered**
   (D-056) — the noise floor on our ~13-name deciles needs a ~1.2%/mo true spread against a 0.80 plan.
   Before any further card: screen C2/C3 on paper against the noise floor (decile ~6.5, quintile
   ~4.6 %/mo, ~245 months). C2 also needs the issuance event table verified PIT.
4. **One frozen run each** over 155 months: pre-2021 = discovery-as-replication, 2021–26 = confirmation.
   Verdict by the tiered hurdle, MR test and fingerprint — nothing else.
5. **Forward:** implementation and sign check only (R5 corollary); significance was settled in step 4.
6. Only after C1 and C2 have a verdict: C3, then C4 on the next reconstitution calendar.

---

## 8. Sources

Method:
- Arnott, Harvey & Markowitz (2019), "A Backtesting Protocol in the Era of Machine Learning" —
  https://people.duke.edu/~charvey/Research/Published_Papers/SSRN-id3275654.pdf [V]
- Harvey (2017), "Presidential Address: The Scientific Outlook in Financial Economics", JF 72(4) —
  https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2893930 [V]
- Harvey, Liu & Zhu (2016), RFS 29(1) — https://www.nber.org/papers/w20592 [V, prior review]
- Chordia, Goyal & Saretto (2020), "Anomalies and False Rejections", RFS 33(5) —
  https://econpapers.repec.org/article/ouprfinst/v_3a33_3ay_3a2020_3ai_3a5_3ap_3a2134-2179..htm [V]
- Bailey & López de Prado (2014), "The Deflated Sharpe Ratio" — https://www.davidhbailey.com/dhbpapers/deflated-sharpe.pdf [V]
  (standard form: PSR(SR\*) = Φ[(SR̂−SR\*)√(T−1) / √(1−γ₃SR̂+((γ₄−1)/4)SR̂²)];
  DSR = PSR(SR₀), SR₀ = √V[SR̂ₙ]·((1−γ)Φ⁻¹(1−1/N)+γΦ⁻¹(1−1/(Ne))))
- Bailey, Borwein, López de Prado & Zhu, "Pseudo-Mathematics and Financial Charlatanism" —
  https://www.davidhbailey.com/dhbpapers/backtest-pseudo.pdf [V]; "The Probability of Backtest
  Overfitting" — https://escholarship.org/uc/item/4w1110bb [V]
- Novy-Marx (2016), "Backtesting Strategies Based on Multiple Signals" — https://www.nber.org/papers/w21329 [V]
- Hou, Xue & Zhang (2020), "Replicating Anomalies", RFS 33(5) — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3275496 [V]
- Jensen, Kelly & Pedersen (2023), "Is There a Replication Crisis in Finance?", JF —
  https://research-api.cbs.dk/ws/portalfiles/portal/95651880/theis_ingerslev_jensen_et_al_is_there_a_replication_crisis_in_finance_publishersversion.pdf [V];
  data: https://jkpfactors.com/data [V]; https://jkpfactors.s3.amazonaws.com/documents/Documentation.pdf [V]
- McLean & Pontiff (2016), JF — https://rpc.cfainstitute.org/research/cfa-digest/2016/06/does-academic-research-destroy-stock-return-predictability-digest-summary [V2]
- Patton & Timmermann (2010), MR test — https://rdrr.io/cran/monotonicity/man/monoRelation.html [V]
- López de Prado & Zoonekynd, causal factor protocol — https://www.adialab.ae/research-series/a-protocol-for-causal-factor-investing [V]
- Lo, Mamaysky & Wang (2000) — https://www.nber.org/papers/w7613 [V]
- Sullivan, Timmermann & White (1999), JF 54(5) — https://ideas.repec.org/a/bla/jfinan/v54y1999i5p1647-1691.html [V]
- Bajgrowicz & Scaillet (2012), JFE 106(3) — https://econpapers.repec.org/article/eeejfinec/v_3a106_3ay_3a2012_3ai_3a3_3ap_3a473-491.htm [V]
- Hsu & Kuan, Reality Check on technical analysis — https://ideas.repec.org/p/sin/wpaper/04-a003.html [V]

Anomalies / EM / Indonesia:
- Julianto & Ekaputra (2020), "Max-Effect in the Indonesian Market", Capital Markets Review — https://mfa-cmr.com/cmr/article/download/72/69 [V]
- "The MAX effect: Lottery stocks with price limits and limits to arbitrage", J. Financial Markets 41 (2018) — https://ideas.repec.org/a/eee/finmar/v41y2018icp77-91.html [V]
- McLean, Pontiff & Watanabe (2009), JFE 94(1) — https://ideas.repec.org/a/eee/jfinec/v94y2009i1p1-17.html [V]
- Liu, Liu & Ma (2011), 52-week high internationally — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1364566 [V]
- Stambaugh, Yu & Yuan (2012), JFE 104(2) — https://ideas.repec.org/a/eee/jfinec/v104y2012i2p288-302.html [V]
- Blitz, Pang & van Vliet (2013), EMR 16 — https://ideas.repec.org/a/eee/ememar/v16y2013icp31-45.html [V]
- Cakici, Fabozzi & Tan (2013), EMR 16 — https://ideas.repec.org/a/eee/ememar/v16y2013icp46-65.html [V]
- Hanauer & Lauterbach (2019), EMR — https://alphaarchitect.com/the-cross-section-of-emerging-market-stock-returns/ [V2]
- Rouwenhorst (1999), JF 54(4) — https://ideas.repec.org/a/bla/jfinan/v54y1999i4p1439-1464.html [V]
- Chui, Titman & Wei (2010), JF 65(1) — https://econpapers.repec.org/RePEc:bla:jfinan:v:65:y:2010:i:1:p:361-392 [V]
- Yusgiantoro et al. (2018), OJK WP/18/04, IDX investor behaviour — https://www.ojk.go.id/id/data-dan-statistik/research/working-paper/Documents/WP-18-04r.pdf [V]
- LQ45/MSCI inclusion–exclusion, Universitas Indonesia — https://scholar.ui.ac.id/en/publications/the-effect-of-inclusion-and-exclusion-indexes-towards-lq45-and-ms [V]
- Ramadhan, Mardiyati & Dalimunthe (2022), Indonesian rights offerings — https://journal.unj.ac.id/unj/index.php/jdmb/article/download/25763/13120/79696 [V]
- Białkowski, Etebari & Wisniewski (2012), JBF 36(3) — https://ideas.repec.org/a/eee/jbfina/v36y2012i3p835-845.html [V]
- Not fetched this pass [M]: Miller (1977); Bali-Cakici-Whitelaw (2011); George-Hwang (2004);
  Harris-Gurel (1986); Shleifer (1986); Hameed-Kusnadi (2002, fetch blocked 429); Hofstede IDV scores;
  JKP characteristic names.
